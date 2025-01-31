FROM python:3.12-bookworm

RUN mkdir -p /app/src
WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.

# Upgrade the OS, 
RUN apt update && \
    apt install -y cron npm && \
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

# Dev only
RUN echo '!! If the next step fails, copy .env.example to .env in the backend folder !!'
COPY .env* .
RUN rm .env.example

# Add our source code
ADD src/thunderbird_accounts ./src/thunderbird_accounts

# Install our package dependencies
RUN uv sync && \
    npm install && npm cache clean --force

EXPOSE 5000
CMD ["/bin/sh", "./scripts/dev-entry.sh"]
