# Jarvis single-VPS runbook

## Start
```bash
cd /root/jarvis-backup
source venv/bin/activate
cp -n .env.example .env   # then fill secrets
python main.py
```

## Systemd
```bash
sudo cp deploy/jarvis.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jarvis
```

## Health
- HTTP: `GET /health`
- Watchdog: `python watchdog.py` (TCP port check + soft restart; never touches git)

## Tests
```bash
python tests/smoke_tests.py
# or
pytest tests/smoke_tests.py -q
```

## Active roles
ceo, sysadmin, researcher, deep_researcher, business_manager, secretary
