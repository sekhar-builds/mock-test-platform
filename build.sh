#!/usr/bin/env bash
# Render build step: install, collect static files, migrate and load demo data.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py seed_demo

# Creates the admin account on first deploy when DJANGO_SUPERUSER_USERNAME and
# DJANGO_SUPERUSER_PASSWORD are set; later deploys skip it because it exists.
if [[ -n "$DJANGO_SUPERUSER_USERNAME" ]]; then
  python manage.py createsuperuser --no-input --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" || true
fi
