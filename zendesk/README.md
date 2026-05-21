# Thunderbird Pro Zendesk Sidebar

This folder contains the private Zendesk app manifest for the Thunderbird Pro customer sidebar.
Zendesk renders a minimal iframe to pass on requester email and source, the rest is managed in a
Django page. Production sidebar access uses the signed Zendesk request token and a stored mapping
between the Zendesk agent and a Thunderbird Pro staff account.

Access is controlled by Django permissions. Each Zendesk agent must connect their Zendesk identity
to a Thunderbird Pro staff account that has the relevant view permissions for authentication, mail,
and subscription records. This avoids relying on Django session cookies inside the Zendesk iframe.

## Routes

- `POST /zendesk/sidebar/`
  Production ZAF shell entrypoint. Zendesk POSTs a signed request token here. The shell reads the
  ticket requester email/channel and submits the nested content iframe with the signed Zendesk
  token in the POST body.

- `GET /zendesk/sidebar/content/?email=user@example.com&via=api`
  Django-rendered customer sidebar content. In a top-level local preview this can use a normal
  Django session.

- `POST /zendesk/sidebar/content/`
  Production iframe content route. The shell submits requester email, channel, and the signed
  Zendesk token in the request body. The token is not placed in the URL.

- `POST /zendesk/sidebar/connect/`
  Top-level account-linking route. The agent signs in with Thunderbird Pro, Django validates the
  signed Zendesk token from the request body, checks the staff permissions, and stores the
  Zendesk-agent connection. If login is required, the token is kept in the Django session during
  the login redirect rather than in the URL.

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

4. Configure stage with the Zendesk signing settings:

   ```text
   ZENDESK_SUBDOMAIN=<your-zendesk-subdomain>
   ZENDESK_APP_ID=<installed-private-app-id>
   ZENDESK_USER_EMAIL=<zendesk-admin-email>
   ZENDESK_API_TOKEN=<zendesk-api-token>
   ```

5. Open a Zendesk Support ticket. If your Zendesk agent is not connected yet, the sidebar shows a
   `Connect Thunderbird Pro` button.

6. Open the connect button in a top-level tab, sign in with a Thunderbird Pro staff account that has
   the required permissions, then return to Zendesk and reload the ticket sidebar.

7. The sidebar should load customer data using the ticket requester email for lookup.

## Automated Tests

The test suite covers the local content route, the ZAF shell template, and the customer
lookup behavior. It intentionally does not exercise Zendesk signed request validation.

```bash
docker compose exec accounts uv run python manage.py test thunderbird_accounts.core.tests
```
