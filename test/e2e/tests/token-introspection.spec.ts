import { expect, test } from '@playwright/test';

import {
  KEYCLOAK_ADMIN_BASE_URL,
  KEYCLOAK_ADMIN_CLIENT_ID,
  KEYCLOAK_ADMIN_CLIENT_SECRET,
  PLAYWRIGHT_TAG_E2E_SUITE,
} from '../const/constants';

test.describe('token introspection compatibility', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test.skip(
    !KEYCLOAK_ADMIN_CLIENT_SECRET || KEYCLOAK_ADMIN_CLIENT_SECRET === 'undefined',
    'Keycloak admin client credentials are required for the introspection compatibility test.',
  );

  test('allows a client to introspect a token without its audience', async () => {
    const masterRealmUrl = `${KEYCLOAK_ADMIN_BASE_URL}/realms/master`;
    const tokenResponse = await fetch(`${masterRealmUrl}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: KEYCLOAK_ADMIN_CLIENT_ID,
        client_secret: KEYCLOAK_ADMIN_CLIENT_SECRET,
        grant_type: 'client_credentials',
      }),
    });
    const tokenData = await tokenResponse.json();

    expect(tokenResponse.ok, JSON.stringify(tokenData)).toBe(true);
    expect(tokenData.access_token).toBeTruthy();

    const tokenPayload = JSON.parse(
      Buffer.from(String(tokenData.access_token).split('.')[1], 'base64url').toString('utf8'),
    );
    const audiences = Array.isArray(tokenPayload.aud)
      ? tokenPayload.aud
      : tokenPayload.aud
        ? [tokenPayload.aud]
        : [];
    expect(audiences).not.toContain(KEYCLOAK_ADMIN_CLIENT_ID);

    const introspectionResponse = await fetch(
      `${masterRealmUrl}/protocol/openid-connect/token/introspect`,
      {
        method: 'POST',
        headers: {
          Authorization: `Basic ${Buffer.from(
            `${KEYCLOAK_ADMIN_CLIENT_ID}:${KEYCLOAK_ADMIN_CLIENT_SECRET}`,
          ).toString('base64')}`,
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          token: tokenData.access_token,
          token_type_hint: 'access_token',
        }),
      },
    );
    const introspectionData = await introspectionResponse.json();

    expect(introspectionResponse.ok, JSON.stringify(introspectionData)).toBe(true);
    expect(introspectionData.active).toBe(true);
  });
});
