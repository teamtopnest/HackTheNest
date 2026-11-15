#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this installer as root." >&2
    exit 1
fi

cd /opt/hackthenest/app
command -v nginx >/dev/null
command -v certbot >/dev/null
test -f app/dist/index.html
test -f app/src/lib/communication-menu.json

if ! id hackthenest >/dev/null 2>&1; then
    adduser --system --group --home /opt/hackthenest hackthenest
fi

install -d -m 750 -o root -g hackthenest /etc/hackthenest
if [ ! -f /etc/hackthenest/backend.env ]; then
    install -m 640 -o root -g hackthenest backend/deploy/backend.env.example /etc/hackthenest/backend.env
fi
chown root:hackthenest /etc/hackthenest/backend.env
chmod 640 /etc/hackthenest/backend.env
chmod 755 /opt/hackthenest

if [ ! -x /opt/hackthenest/venv/bin/python ]; then
    python3 -m venv /opt/hackthenest/venv
fi
/opt/hackthenest/venv/bin/python -m pip install -r backend/requirements-cloud.txt

install -m 644 backend/deploy/neuronvision.service /etc/systemd/system/neuronvision.service
install -m 644 backend/deploy/neuronvision.nginx /etc/nginx/sites-available/neuronvision
ln -sfn /etc/nginx/sites-available/neuronvision /etc/nginx/sites-enabled/neuronvision
nginx -t
systemctl daemon-reload
systemctl enable --now nginx
systemctl reload nginx

if grep -qE 'REPLACE_|CLUSTER_HOST' /etc/hackthenest/backend.env; then
    echo "Frontend installed. Backend not started: replace placeholders in /etc/hackthenest/backend.env."
else
    systemctl enable neuronvision
    systemctl restart neuronvision
    for attempt in $(seq 1 30); do
        if curl -fsS http://127.0.0.1:8000/health >/dev/null; then
            echo "Backend health verified."
            exit 0
        fi
        sleep 1
    done
    echo "Backend did not become ready. Check: journalctl -u neuronvision -n 40 --no-pager" >&2
    exit 1
fi
