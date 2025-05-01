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
     vite.config.mjs \
     .
COPY assets ./assets/
COPY scripts/dev-entry.sh scripts/dev-entry.sh
COPY static ./static/
COPY templates ./templates/

# Required for local dev work (and running tests locally)
RUN ln -s /app/thunderbird_accounts src/thunderbird_accounts

# Add our source code
ADD src/thunderbird_accounts ./src/thunderbird_accounts

# Install our package dependencies, with cli
RUN uv sync --extra cli && \
    npm install && npm cache clean --force

EXPOSE 8087
CMD ["/bin/sh", "./scripts/dev-entry.sh"]
