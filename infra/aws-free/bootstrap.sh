#!/usr/bin/env bash
set -euo pipefail
dnf install -y docker git nodejs22 nodejs22-npm openssl
systemctl enable --now docker
if ! command -v node >/dev/null; then ln -s /usr/bin/node-22 /usr/local/bin/node; fi
if ! command -v npm >/dev/null; then ln -s /usr/bin/npm-22 /usr/local/bin/npm; fi
npm install --global pnpm@11.25.0
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL https://github.com/docker/compose/releases/download/v2.35.1/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
fi
mkdir -p /opt/votoseguro
if [ ! -d /opt/votoseguro/source/.git ]; then
  git clone --branch JERS --single-branch https://github.com/Alejandro-Melgar77/votoseguro.git /opt/votoseguro/source
fi
bash /opt/votoseguro/source/infra/aws-free/deploy.sh
