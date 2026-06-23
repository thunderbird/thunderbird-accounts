import crypto from 'crypto';
import http from 'http';
import type { AddressInfo } from 'net';
import { expect, type Page } from '@playwright/test';

import {
  KEYCLOAK_REALM_URL,
  STALWART_OAUTH_CLIENT_ID,
  STALWART_OAUTH_CLIENT_SECRET,
  TIMEOUT_30_SECONDS,
} from '../const/constants';

const OAUTH_CALLBACK_TIMEOUT = TIMEOUT_30_SECONDS * 3;

export const getStalwartAccessTokenViaSso = async (page: Page) => {
  if (!STALWART_OAUTH_CLIENT_SECRET || STALWART_OAUTH_CLIENT_SECRET === 'undefined') {
    throw new Error('STALWART_OAUTH_CLIENT_SECRET must be set to run the Stalwart OAuth MFA test.');
  }

  const state = crypto.randomBytes(16).toString('hex');
  let callbackTimer: NodeJS.Timeout;
  const server = http.createServer();
  const callbackPromise = new Promise<{ code: string; state: string }>((resolve, reject) => {
    callbackTimer = setTimeout(() => {
      reject(new Error('Timed out waiting for OAuth callback.'));
    }, OAUTH_CALLBACK_TIMEOUT);

    server.on('request', (request, response) => {
      const callbackUrl = new URL(request.url || '/', 'http://127.0.0.1');
      const code = callbackUrl.searchParams.get('code');
      const returnedState = callbackUrl.searchParams.get('state');

      response.writeHead(code ? 200 : 400, { 'Content-Type': 'text/html' });
      response.end('<html><body>OAuth callback received</body></html>');

      if (!code || !returnedState) {
        reject(new Error(`OAuth callback did not include code and state: ${callbackUrl.search}`));
        return;
      }

      clearTimeout(callbackTimer);
      resolve({ code, state: returnedState });
    });
  });

  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const { port } = server.address() as AddressInfo;
  const redirectUri = `http://127.0.0.1:${port}/callback`;

  // No `prompt=login`: the caller has just signed in with password+OTP, so
  // Stalwart should reuse Keycloak SSO the same way real mail clients do.
  const authUrl = new URL(`${KEYCLOAK_REALM_URL}/protocol/openid-connect/auth`);
  authUrl.search = new URLSearchParams({
    client_id: STALWART_OAUTH_CLIENT_ID,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope: 'openid email',
    state,
  }).toString();

  try {
    await page.goto(authUrl.toString(), { waitUntil: 'domcontentloaded' });

    const callback = await callbackPromise;
    expect(callback.state).toBe(state);

    const tokenResponse = await fetch(`${KEYCLOAK_REALM_URL}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: STALWART_OAUTH_CLIENT_ID,
        client_secret: STALWART_OAUTH_CLIENT_SECRET,
        code: callback.code,
        grant_type: 'authorization_code',
        redirect_uri: redirectUri,
      }),
    });
    const tokenData = await tokenResponse.json();

    if (!tokenResponse.ok || !tokenData.access_token) {
      throw new Error(`Failed to exchange OAuth code: ${JSON.stringify(tokenData)}`);
    }

    return tokenData.access_token as string;
  } finally {
    clearTimeout(callbackTimer!);
    server.close();
  }
};
