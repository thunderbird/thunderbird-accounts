# Thunderbird Accounts

> [!IMPORTANT]  
> Thunderbird Accounts is still in active development and is not ready for any active use.


[![Documentation Status](https://readthedocs.com/projects/thunderbird-thunderbird-pro-services/badge/?version=latest)](https://pro-services-docs.thunderbird.net/en/latest/?badge=latest)

This project uses [uv](https://github.com/astral-sh/uv).

Thunderbird Accounts is a Django 5.1 application. Please read up on Django before diving in.

## Setup / Running

### Installing

Ensure that uv is installed, and then run:
```shell
uv sync
```

### Creating a local SuperUser

Run the following and follow the terminal prompts:

```shell
./manage.py createsuperuser
```

### Running in docker (recommended)

```shell
docker-compose up --build -V
```

A server will be available at [http://localhost:8087/](http://localhost:8087/)

### Running local dev server

```shell
./manage.py runserver 0.0.0.0:8087
```

## Exposed dev ports

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

## Creating additional apps

Apps are feature of django we can use to create re-usable modules with. We mostly just use them to separate out and organize components. 
Apps can depend on and/or require other internal apps, there's no hard rule here. 

Ensure to nest all internal apps inside `src/thunderbird_accounts` by appending the destination path after the command:

`mkdir -p src/thunderbird_accounts/<app name> && ./manage.py startapp <app name> src/thunderbird_accounts/<app name>`

Once the app is created go to `src/thunderbird_accounts/<app name>/apps.py` and prepend `thunderbird_accounts.` to AuthConfig.name so it looks like `thunderbird_accounts.<app name>`.