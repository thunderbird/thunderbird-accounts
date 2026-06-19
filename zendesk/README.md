# Thundermail Zendesk Sidebar

This folder contains the private Zendesk app manifest for the Thundermail customer sidebar.
Zendesk renders a minimal iframe to collect ticket requester context with ZAF. The app then calls
the Django sidebar content endpoint through `client.request(..., secure: true)` using Zendesk's
per-agent OAuth token for Keycloak.

Access is controlled by Django permissions. The Keycloak token subject must match a local
Thundermail staff account's `oidc_id`, and that user must have the relevant view permissions for
authentication, mail, and subscription records. The iframe does not rely on Django session cookies.

## Routes

- `POST /zendesk/sidebar/`
  Production ZAF shell entrypoint. Zendesk POSTs a signed ZAF JWT here. Django validates the token
  with `ZENDESK_APP_PUBLIC_KEY` and `ZENDESK_APP_AUDIENCE`, then renders the shell.
  - See [instructions for getting the Zendesk public key for the app](https://developer.zendesk.com/documentation/apps/build-an-app/building-a-server-side-app/part-5-secure-the-app/#getting-your-zendesk-apps-public-key-and-installation-id)
  

- `GET /zendesk/sidebar/content/?email=user@example.com&via=api`
  Django-rendered customer sidebar content. In a top-level local preview this can use a normal
  Django session.

- `POST /zendesk/sidebar/content/`
  Production content route. The shell calls this through ZAF `client.request` with
  `Authorization: Bearer {{setting.token}}`; Zendesk substitutes the Keycloak OAuth
  access token server-side.

## Keycloak Setup

Create a staging OIDC client for Zendesk. Suggested client id:

```text
zendesk-sidebar-stage
```

Use these settings:

- Enable standard authorization-code flow.
- Enable client authentication and save the generated client secret for the Zendesk app package.
- Set the valid redirect URI to:

```text
https://zis.zendesk.com/api/services/zis/connections/oauth/callback
```

- Use scopes `openid email profile`.
- Add an audience mapper so access tokens include `zendesk-sidebar-stage` in `aud`.
- Make sure the token includes `azp=zendesk-sidebar-stage`.

Configure the Django staging environment with:

```text
ZENDESK_SUBDOMAIN=<zendesk-subdomain>
ZENDESK_APP_AUDIENCE=https://<zendesk-subdomain>.zendesk.com/api/v2/apps/installations/<installation-id>.json
# With physical newlines converted to \n so it fits on a single line.
ZENDESK_APP_PUBLIC_KEY=<installed-app-public-key-pem>
ZENDESK_OAUTH_CLIENT_ID=zendesk-sidebar-stage
ZENDESK_OAUTH_AUDIENCE=zendesk-sidebar-stage
ZENDESK_OAUTH_ISSUER=https://auth-stage.tb.pro/realms/tbpro
ZENDESK_OAUTH_JWKS_ENDPOINT=https://auth-stage.tb.pro/realms/tbpro/protocol/openid-connect/certs
```

For production, use the production Keycloak base URL and a separate production client.

## Local Preview

Run the Django stack, sign in locally as a staff user with the required view permissions, then open:

```text
http://localhost:8000/zendesk/sidebar/content/?email=user@example.com&via=api
```

Use `via=api` to show the requester as verified. Any other channel, for example `via=web`, shows
`Not verified`.

The content route is meant for fast UI and data checks and does not test Zendesk signed request
validation.

## Testing With Zendesk On Stage

Use a real Zendesk private app install pointed at the stage Django environment.

Before packaging, replace the `KEYCLOAK_CLIENT_ID` and `KEYCLOAK_CLIENT_SECRET` placeholders in
`manifest.json` with the staging Keycloak client id and secret. Do not commit the real secret.

1. Package the app from this directory. The zip root must contain `manifest.json`, `assets/`, and
   `translations/`.

   ```bash
   cd zendesk
   zip -r zendesk-sidebar.zip manifest.json assets translations README.md
   ```

2. In Zendesk Admin Center, upload `zendesk-sidebar.zip` as a private Support app.

3. Set the app setting `sidebar_url` to the stage iframe URL:

   ```text
   https://accounts.stage-thundermail.com/zendesk/sidebar/
   ```


4. Set the app setting `api_host` to the stage Accounts host:

   ```text
   accounts.stage-thundermail.com
   ```

5. Complete the app's OAuth prompt as a Zendesk agent with a matching Thundermail staff account.

6. Open a Zendesk Support ticket and reload the ticket sidebar.

7. The sidebar should load customer data using the ticket requester email for lookup.

## Testing with Zendesk locally.

Zendesk staging can also be connected with a copy this repo running on your laptop using Tailscale funnel. First, make sure the app is running as normal with `sudo docker compose up -V`

Start a tailscale funnel for port 8087, which will forward a public, HTTPS-enabled domain name to your laptop and then forward traffic 8087. Example:

```
❯ tailscale funnel 8087
Available on the internet:

https://your-host.goldside-cuddlefish.ts.net/
|-- proxy http://127.0.0.1:8087

Press Ctrl+C to exit.
```
From there, the instructions are the same as using Zendesk staging above, with the two following URL differences, based on the hostname that Tailscale provides you:

* `sidebar_url`: `https://change-me.random-words.ts.net/zendesk/sidebar/`
* `api_host`: `change-me.random-words.ts.net`


## Per-Agent OAuth Check

Before relying on per-agent authorization in production, verify how Zendesk scopes the OAuth setting
in practice:

1. Install the private app and complete the OAuth prompt as agent A.
2. Open the sidebar as agent B, using a different Keycloak account with a different `sub`.
3. Temporarily inspect decoded access token claims on the Django content route. Do not log the raw
   access token.
4. Confirm the decoded `sub` and `email` match the active Zendesk agent, not the installing agent.

## Automated Tests

The test suite covers the local content route, the ZAF shell template, OAuth bearer access, signed
request validation parameters, and customer lookup behavior.

```bash
docker compose exec accounts uv run python manage.py test thunderbird_accounts.core.tests
```
