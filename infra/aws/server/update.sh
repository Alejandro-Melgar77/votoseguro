#!/bin/bash
# Actualiza el servidor a la última versión de la rama JERS.
# Uso (como root en el EC2): bash /opt/votoseguro/app/infra/aws/server/update.sh
set -euo pipefail

APP=/opt/votoseguro/app
ENV_FILE=/opt/votoseguro/.env
WEB_ROOT=/var/www/votoseguro/web
BRANCH=${BRANCH:-JERS}
REGION=${AWS_REGION:-us-east-1}
CERTBOT_IMAGE=certbot/certbot:v3.0.1

TOKEN=$(curl -sX PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
meta() { curl -s -H "X-aws-ec2-metadata-token: $TOKEN" "http://169.254.169.254/latest/$1"; }
PUBLIC_IP=$(meta meta-data/public-ipv4)
DOMAIN=${DOMAIN:-${PUBLIC_IP//./-}.sslip.io}
ACCOUNT=$(meta dynamic/instance-identity/document | sed -n 's/.*"accountId" *: *"\([0-9]*\)".*/\1/p')
BUCKET=${WEB_BUCKET:-votoseguro-web-$ACCOUNT}

echo "== Código: rama $BRANCH"
cd "$APP"
git fetch --quiet origin "$BRANCH"
git reset --quiet --hard "origin/$BRANCH"
git log --oneline -1

if [ ! -f "$ENV_FILE" ]; then
    echo "Falta $ENV_FILE (ver infra/aws/server/README.md)" >&2
    exit 1
fi
if grep -q '^CORS_ORIGINS=' "$ENV_FILE"; then
    sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=https://$DOMAIN|" "$ENV_FILE"
else
    echo "CORS_ORIGINS=https://$DOMAIN" >> "$ENV_FILE"
fi

echo "== Frontend desde s3://$BUCKET"
mkdir -p "$WEB_ROOT"
aws s3 sync "s3://$BUCKET" "$WEB_ROOT" --delete --region "$REGION" --only-show-errors

echo "== Contenedores"
docker volume inspect app_pgdata >/dev/null 2>&1 || docker volume create app_pgdata >/dev/null
docker compose --env-file "$ENV_FILE" -p votoseguro -f "$APP/infra/aws/server/docker-compose.prod.yml" up -d --build --remove-orphans
docker image prune -f >/dev/null

echo "== HTTPS para $DOMAIN"
mkdir -p /var/www/certbot
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    # Configuración temporal solo-HTTP para emitir el primer certificado
    printf '%s\n' \
        'server {' \
        '    listen 80 default_server;' \
        '    server_name _;' \
        '    location /.well-known/acme-challenge/ { root /var/www/certbot; }' \
        '    location / { return 503; }' \
        '}' > /etc/nginx/conf.d/votoseguro.conf
    systemctl reload nginx
    docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/www/certbot:/var/www/certbot \
        "$CERTBOT_IMAGE" certonly --webroot -w /var/www/certbot -d "$DOMAIN" \
        --non-interactive --agree-tos --register-unsafely-without-email
fi
sed "s/__DOMAIN__/$DOMAIN/g" "$APP/infra/aws/server/nginx.conf.template" > /etc/nginx/conf.d/votoseguro.conf
nginx -t
systemctl reload nginx

# Renovación automática del certificado (dos veces al día)
printf '%s\n' \
    '[Unit]' \
    'Description=Renovar certificado Lets Encrypt de VotoSeguro' \
    '[Service]' \
    'Type=oneshot' \
    "ExecStart=/usr/bin/docker run --rm -v /etc/letsencrypt:/etc/letsencrypt -v /var/www/certbot:/var/www/certbot $CERTBOT_IMAGE renew --webroot -w /var/www/certbot --quiet" \
    'ExecStartPost=/usr/bin/systemctl reload nginx' > /etc/systemd/system/votoseguro-certbot.service
printf '%s\n' \
    '[Unit]' \
    'Description=Renovacion periodica del certificado de VotoSeguro' \
    '[Timer]' \
    'OnCalendar=*-*-* 03,15:30:00' \
    'RandomizedDelaySec=1h' \
    'Persistent=true' \
    '[Install]' \
    'WantedBy=timers.target' > /etc/systemd/system/votoseguro-certbot.timer
systemctl daemon-reload
systemctl enable --now votoseguro-certbot.timer >/dev/null

echo "== Esperando API"
for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:8000/api/v1/health >/dev/null; then
        echo "VotoSeguro en línea: https://$DOMAIN"
        exit 0
    fi
    sleep 5
done
echo "La API no respondió a tiempo; revise: docker logs votoseguro-api" >&2
exit 1
