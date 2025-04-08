# Thunderbird Accounts

> [!IMPORTANT]
> Thunderbird Accounts is still in active development and is not ready for any active use.


[![Documentation Status](https://readthedocs.com/projects/thunderbird-thunderbird-pro-services/badge/?version=latest)](https://pro-services-docs.thunderbird.net/en/latest/?badge=latest)

This project uses [uv](https://github.com/astral-sh/uv).

Thunderbird Accounts is a Django 5.1 application. Please read up on Django before diving in.

Docker is the recommended way to run the server, though you have the option to run it locally.


## Shared setup

Whether you're running the server via Docker or locally, you'll need to set up your `.env` file and copy the example Stalwart config.

### Create the .env file

Start from the `.env.example` file to create your dev and test `.env` files:

```shell
cp .env.example .env
```

#### Get the `FXA_CLIENT_ID` and `FXA_SECRET`

These can be found in the Services 1password vault in the item named "FXA stage application keys for TB Accounts".

### Use the example config for Stalwart

Note: Do not use this for production environments.

Copy config.toml.example to `mail/etc/config.toml` before first run.

```shell
mkdir -p mail/etc && cp config.toml.example mail/etc/config.toml
```

The default admin password should be `accounts`.


## Running the server in Docker (recommended)


### Start the Docker containers

```shell
docker-compose up --build -V
```

A server will be available at [http://localhost:8087/](http://localhost:8087/)

### Generate `SECRET` keys


Generate a random secret with this command:

```shell
docker compose exec backend uv run manage.py generate_key
```

Use this value for the following variables in your `.env` file:

- `FXA_ENCRYPT_SECRET`
- `SECRET_KEY`
- `LOGIN_CODE_SECRET`

It's fine to use the same key for all three; this is only for development.

After making this change, restart your docker containers.


### Create a superuser

Run the this command and follow the terminal prompts:

```shell
docker compose exec backend uv run manage.py createsuperuser --email <fxa_email_address>
```

When asked, enter your FXA email address.

### Make an existing user a superuser

If you have already attempted to login to the admin via FXA and gotten a `401 Unauthorized`, run this command:

```shell
docker compose exec backend uv run manage.py make_superuser <fxa_email_address>
```

### Exposed dev ports

For development the following ports are exposed:

| Service          | Port for host computer | Port in docker network |
|------------------|------------------------|------------------------|
| Webserver        | 8087                   | 8087                   |
| Postgres         | 5433                   | 5432                   |
| Redis            | 6380                   | 6379                   |
| Redis (Insights) | 8071                   | 8001                   |
| Mailpit (Web UI) | 8026                   | 8025                   |
| Mailpit (SMTP)   | 1026                   | 1024                   |

(Note: You're the host computer. So connect to postgres via port 5433!)


## Running the server locally

### Installation

Ensure that uv is installed, and then run:
```shell
uv sync --extra cli --extra docs
```

The default admin password should be `accounts`.

### Create a superuser

Run the following and follow the terminal prompts:

```shell
./manage.py createsuperuser --email <fxa_email_address>
```

When asked, enter your FXA email address.

### Generate `SECRET` keys


Generate a random secret with this command:

```shell
./manage.py generate_key
```

Use this value for the following variables in your `.env` file:

- `FXA_ENCRYPT_SECRET`
- `SECRET_KEY`
- `LOGIN_CODE_SECRET`

It's fine to use the same key for all three; this is only for development.

### Start the local dev server

```shell
./manage.py runserver 0.0.0.0:8087
```


### Make an existing user a superuser

If you have already attempted to login to the admin via FXA and gotten a `401 Unauthorized`, run this command:

```shell
./manage.py make_superuser <fxa_email_address>
```



## Creating additional apps

Apps are feature of django we can use to create re-usable modules with. We mostly just use them to separate out and organize components.
Apps can depend on and/or require other internal apps, there's no hard rule here.

Ensure to nest all internal apps inside `src/thunderbird_accounts` by appending the destination path after the command:

`mkdir -p src/thunderbird_accounts/<app name> && ./manage.py startapp <app name> src/thunderbird_accounts/<app name>`

Once the app is created go to `src/thunderbird_accounts/<app name>/apps.py` and prepend `thunderbird_accounts.` to AuthConfig.name so it looks like `thunderbird_accounts.<app name>`.

## Building documentation locally

Ensure you have the requirements in docs installed and run the following command in the project's root folder:

```shell
sphinx-build docs build
```

## Running tests in docker

Make sure that the containers are already running.

To run all tests:
```shell
docker compose exec backend uv run python manage.py test
```

To run tests for a specific module:
```shell
docker compose exec backend uv run manage.py test thunderbird_accounts.client.tests
```
