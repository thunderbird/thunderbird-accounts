# Thunderbird Accounts

> [!IMPORTANT]
> Thunderbird Accounts is still in active development and is not ready for any active use.

[![Documentation Status](https://readthedocs.com/projects/thunderbird-thunderbird-pro-services/badge/?version=latest)](https://pro-services-docs.thunderbird.net/en/latest/?badge=latest)

This project uses [uv](https://github.com/astral-sh/uv).

Thunderbird Accounts is a Django 5.2 application. Please read up on Django before diving in.

Docker is the recommended way to run the server.

## Before you begin

Make sure you have [uv](https://github.com/astral-sh/uv) up and running, and you adjust your hosts file to include:

```
127.0.0.1 keycloak
127.0.0.1 stalwart
```

## Getting Started

Ensure you have uv setup and the project bootstrapped by running:

```bash
uv sync
uv run bootstrap.py
```

This will create a virtual environment if needed and sync the latest project dependencies to your local environment.

The project comes with some optional dependencies such as cli tools, tools for building the docs, and tools for working
with our Subscription app powered by Paddle.

These can be installed be appending `--extra <optional dependency>` like so:

```bash
uv sync --extra cli --extra docs --extra subscription
```

## Re-bootstrapping the project

If you find your environment in a troubled state (it happens) you can add the option `--from-scratch` to bootstrap like
so:

```bash
uv run bootstrap.py --from-scratch
```

This will overwrite your local `.env` with the contents of `.env.example`, copy over a fresh copy of the stalwart config
from `config.toml.example` to `mail/etc/config.toml` and delete your stalwart's internal db `mail/data`.

Additionally, you'll want to remove the volumes for both postgres and kcpostgres to clear accounts and keycloak's
database.

## OIDC / Authentication

Accounts integrates [mozilla-django-oidc](https://github.com/mozilla/mozilla-django-oidc). Included in this repo is a
basic development config for keycloak, and a keycloak environment defined in docker-compose.yml. There's nothing
stopping you from using a different OIDC provider. Please refer to the package documentation and your local `.env` file
for settings you may need to change.

## Running

Once you have the project bootstrapped you'll want to actually run the project via docker:

```bash
docker compose up --build -V
```

(Note: If you're not attached to the docker group you may need to add sudo before the above command.)

The first boot may take a while as:

* Keycloak imports realm / user information from `keycloak/data/import`
* Accounts runs the required database migrations
* Accounts pulls the latest Paddle product and subscription information (if you have the Paddle setup.)

Please wait until the containers are fully booted before continuing.

## Logging in

A variety of basic development admin accounts are provided to help folks boot the project and start working.

### Accounts / Thunderbird Pro Dashboard

You can access the login / dashboard at [http://localhost:8087/self-serve/](http://localhost:8087/self-serve/). If you
are not logged in you will be taken to a keycloak login screen. You can use the following credentials to proceed:

```
Username: admin@example.org
Password: admin
```

From here you can create an email account.

The default admin user is also setup you use Django's admin panel available
at [http://localhost:8087/admin/](http://localhost:8087/admin/).

### Stalwart

Stalwart is located at [http://localhost:8080/](http://localhost:8080/). Currently, there is
a [bug](https://github.com/stalwartlabs/webadmin/issues/52) preventing instances connected to an external OIDC directory
server from logging into the admin panel.

If you need to access the admin panel you can modify your `mail/etc/config.toml` and edit `[storage].directory` from
`kc` to `internal`, and restart the docker container.

From there you can login with the following credentials:

```
Username: admin
Password: accounts
```

You generally won't need to connect to Stalwart's admin panel unless you need to verify account status or debug api
calls. Make sure to change the `[storage].directory` key back to `kc` and restart the docker container when you're
finished.

### Keycloak

Keycloak is the auth/OIDC provider that is setup by default. Two realms are imported the default `master` realm and the
`tbpro` realm.

If you like to login to Keycloak's admin interface you can access that at [http://keycloak:8999/admin/master/console/](http://keycloak:8999/admin/master/console/)
with the following credentials:

```
Username: admin
Password: admin
```

From there you can switch to the tbpro realm and access settings that will affect Account's and Stalwart's login.

Additionally, you can access a simple user management portal under the tbpro realm available
at [http://keycloak:8999/realms/tbpro/account](http://keycloak:8999/realms/tbpro/account). Since this within the tbpro
realm you can login to any account you created for accounts including admin@example.org.

## Creating additional apps

Apps are feature of django we can use to create re-usable modules with. We mostly just use them to separate out and
organize components.
Apps can depend on and/or require other internal apps, there's no hard rule here.

Ensure to nest all internal apps inside `src/thunderbird_accounts` by appending the destination path after the command:

`mkdir -p src/thunderbird_accounts/<app name> && ./manage.py startapp <app name> src/thunderbird_accounts/<app name>`

Once the app is created go to `src/thunderbird_accounts/<app name>/apps.py` and prepend `thunderbird_accounts.` to
AuthConfig.name so it looks like `thunderbird_accounts.<app name>`.

## Building documentation locally

Ensure you have the requirements in docs installed and run the following command in the project's root folder:

```shell
sphinx-build docs build
```

## Running tests

Make sure that the containers are already running.

To run all tests:

```shell
docker compose exec backend uv run python manage.py test
```

To run tests for a specific module:

```shell
docker compose exec backend uv run manage.py test thunderbird_accounts.client.tests
```

## Running the E2E tests

Please see the [E2E tests README](./test/e2e/README.md).
