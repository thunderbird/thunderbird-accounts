FROM python:3.13-trixie
#
# Dockerfile for Thunderbird Accounts
#

# This a Stable URL for this content that's regularly refreshed with new data.
# If ever it fails, compatible data sources are available in a number of places.
# Check: https://github.com/wp-statistics/DbIP-City-lite/
# Upstream:  https://db-ip.com/db/lite.php
ARG GEOIP_CITY_MMDB_GZ_URL=https://cdn.jsdelivr.net/npm/dbip-city-lite/dbip-city-lite.mmdb.gz

RUN mkdir -p /app/src
WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.
# Determines what BASE_DIR we use
ENV IN_CONTAINER=True

# Upgrade the OS, 
RUN apt update && \
    apt install -y cron npm curl && \
    apt install -y postgresql && \
    apt install -y gettext && \
    apt-get clean && \
    mkdir scripts && \
    pip --no-cache install --upgrade pip uv

RUN mkdir -p /app/data && \
    curl -fsSL "${GEOIP_CITY_MMDB_GZ_URL}" -o /app/data/dbip-city-lite.mmdb.gz && \
    gunzip -f /app/data/dbip-city-lite.mmdb.gz

# Copy in the relevant files
COPY manage.py \
     MANIFEST.in \
     package.json \
     package-lock.json \
     pyproject.toml \
     README.md \
     uv.lock \
     vite.config.mts \
     tsconfig.json \
     env.d.ts \
     .
COPY assets ./assets/
COPY keycloak ./keycloak/
COPY scripts ./scripts/
COPY src/thunderbird_accounts ./src/thunderbird_accounts/
COPY static ./static/
COPY templates ./templates/

# Install our package dependencies, with cli
RUN uv sync --extra cli --extra subscription && \
    npm install && npm cache clean --force && \
    chmod +x scripts/entry.sh

# Build the production app
RUN npm run build

# Collect static content, ignore the vue component directory
RUN ./manage.py collectstatic --noinput -i assets/app/vue

# Clean up after collectstatic is finished
RUN rm -rf ./keycloak/*
RUN rm -rf ./assets/*

EXPOSE 8087
ENTRYPOINT ["./scripts/entry.sh"]
