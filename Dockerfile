FROM python:3.13-bookworm
#
# Development docker file
#

RUN mkdir -p /app/src
WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.
# Determines what BASE_DIR we use
ENV IN_CONTAINER=True

# Upgrade the OS, 
RUN apt update && \
    apt install -y cron npm && \
    apt install -y postgresql && \
    apt-get clean && \
    mkdir scripts && \
    pip --no-cache install --upgrade pip uv

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
COPY scripts ./scripts/
COPY src/thunderbird_accounts ./src/thunderbird_accounts/
COPY static ./static/
COPY templates ./templates/

# Install our package dependencies, with cli
RUN uv sync --extra cli --extra subscription && \
    npm install && npm cache clean --force && \
    chmod +x scripts/entry.sh

EXPOSE 8087
ENTRYPOINT ["./scripts/entry.sh"]
