FROM python:3.12-bookworm

RUN mkdir app
WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.

RUN apt update && apt install -y cron npm

RUN mkdir scripts

COPY README.md .
COPY assets ./assets/
COPY static ./static/
COPY templates ./templates/
COPY manage.py .
COPY MANIFEST.in .
COPY uv.lock .
COPY pyproject.toml .
COPY vite.config.mjs .
COPY package.json .
COPY package-lock.json .
COPY scripts/dev-entry.sh scripts/dev-entry.sh

# Dev only
RUN echo '!! If the next step fails, copy .env.example to .env in the backend folder !!'

COPY .env* .
RUN rm .env.example

# Add this hack to line it up with our dev environment.
# I'll buy whoever fixes this a coffee.
RUN mkdir src
RUN ln -s /app/thunderbird_accounts src/thunderbird_accounts

RUN pip install --upgrade pip
RUN pip install uv
RUN uv sync
RUN npm install && npm cache clean --force

EXPOSE 5000
CMD ["/bin/sh", "./scripts/dev-entry.sh"]
