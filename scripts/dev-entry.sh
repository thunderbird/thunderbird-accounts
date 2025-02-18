#!/bin/sh

# Build the vite apps
npm run build

# Collect static content, ignore the vue component directory
./manage.py collectstatic --noinput -i assets/app/vue

echo 'Waiting 1s for DB !'

# Wait until db is available
sleep 1s

# Run migrations
./manage.py migrate

# Classic Django devserver
#./manage.py runserver 0.0.0.0:8087

# Uvicorn devserver (preferred)
uv run uvicorn thunderbird_accounts.asgi:application --reload  --host 0.0.0.0 --port 8087 --reload-include *.html
