#!/usr/bin/env bash
set -euo pipefail
exec 9>/var/lock/votoseguro-deploy.lock
flock -w 900 9
ROOT=/opt/votoseguro
SOURCE="$ROOT/source"
REGION=us-east-1
EXPECTED_SHA="${1:-}"
mkdir -p "$ROOT" "$ROOT/private" "$ROOT/data" "$ROOT/web"
chmod 700 "$ROOT/private"
if [ ! -d "$SOURCE/.git" ]; then
  git clone --branch JERS --single-branch https://github.com/Alejandro-Melgar77/votoseguro.git "$SOURCE"
fi
cd "$SOURCE"
git fetch origin JERS
SHA=$(git rev-parse origin/JERS)
if [ -n "$EXPECTED_SHA" ] && [ "$EXPECTED_SHA" != "$SHA" ]; then
  echo 'Se omite una revisión antigua: JERS ya tiene un commit posterior.'
  exit 0
fi
git checkout --detach "$SHA"
export RELEASE_TAG="$SHA"

# Secret values are downloaded directly from SSM into a root-only environment file.
aws ssm get-parameter --region "$REGION" --name /votoseguro/JERS/runtime --with-decryption --query Parameter.Value --output text > "$ROOT/private/runtime.env"
chmod 600 "$ROOT/private/runtime.env"

CERTS="$ROOT/private/certs"
mkdir -p "$CERTS"
chmod 755 "$ROOT/private" "$CERTS"
if [ ! -f "$CERTS/ca.crt" ]; then
  openssl req -x509 -nodes -newkey rsa:2048 -days 730 -keyout "$CERTS/ca.key" -out "$CERTS/ca.crt" -subj /CN=VotoSeguro-Internal-CA >/dev/null 2>&1
  openssl req -nodes -newkey rsa:2048 -keyout "$CERTS/server.key" -out "$CERTS/server.csr" -subj /CN=postgres >/dev/null 2>&1
  printf 'subjectAltName=DNS:postgres\nextendedKeyUsage=serverAuth\n' > "$CERTS/server.ext"
  openssl x509 -req -in "$CERTS/server.csr" -CA "$CERTS/ca.crt" -CAkey "$CERTS/ca.key" -CAcreateserial -out "$CERTS/server.crt" -days 730 -extfile "$CERTS/server.ext" >/dev/null 2>&1
  chown 70:70 "$CERTS/server.key"
  chmod 600 "$CERTS/ca.key" "$CERTS/server.key"
  chmod 644 "$CERTS/ca.crt" "$CERTS/server.crt"
fi

PUBLIC_HOST=$(aws ssm get-parameter --region "$REGION" --name /votoseguro/JERS/public-host --query Parameter.Value --output text)
cat > "$ROOT/private/Caddyfile" <<CADDY
$PUBLIC_HOST {
  encode zstd gzip
  header X-Content-Type-Options nosniff
  header Referrer-Policy strict-origin-when-cross-origin
  header Permissions-Policy "camera=(self), microphone=(self), on-device-speech-recognition=(self)"
  handle /api/* {
    reverse_proxy api:8000
    header Cache-Control no-store
  }
  handle {
    root * /srv
    try_files {path} /index.html
    file_server
  }
}
CADDY
chmod 600 "$ROOT/private/Caddyfile"

docker build -t "votoseguro-api:$SHA" apps/api
COMPOSE=(docker compose --project-name votoseguro -f infra/aws-free/compose.yml)
"${COMPOSE[@]}" up -d --wait postgres
"${COMPOSE[@]}" run --rm --no-deps api alembic upgrade head

# Install only the packages needed to build the web application.
CI=true pnpm install --frozen-lockfile --filter @votoseguro/web...
VITE_API_BASE_URL=/api/v1 pnpm --filter @votoseguro/web build
cp -a apps/web/dist/. "$ROOT/web/"
"${COMPOSE[@]}" up -d --remove-orphans api scheduler web
for attempt in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T api curl --fail --silent http://localhost:8000/api/v1/health >/dev/null; then
    printf '%s\n' "$SHA" > "$ROOT/deployed-sha"
    printf 'RELEASE_TAG=%s\n' "$SHA" > "$ROOT/private/release.env"
    echo "Versión JERS publicada: $SHA"
    exit 0
  fi
  sleep 3
done
echo 'La API no confirmó su salud.' >&2
exit 1
