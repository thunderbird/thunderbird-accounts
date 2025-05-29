#!/bin/sh

#
# This script is for development purposes only!
#

# Build the vite apps
npm run build

# Wait until db is available
echo 'Waiting 1s for DB !'
sleep 1s

# Run migrations
./manage.py migrate

# Retrieve paddle products & prices
./manage.py get_paddle_products
./manage.py get_paddle_prices

# Classic Django devserver
#./manage.py runserver 0.0.0.0:8087

# Uvicorn devserver (preferred)
uv run uvicorn thunderbird_accounts.asgi:application --lifespan off --reload  --host 0.0.0.0 --port 8087 --reload-include *.html
