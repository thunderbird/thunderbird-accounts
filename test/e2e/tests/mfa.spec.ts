import crypto from 'crypto';
import http from 'http';
import net from 'net';
import tls from 'tls';
import type { AddressInfo } from 'net';
import { test, expect, type Page } from '@playwright/test';

import { ensureWeAreSignedIn, waitForVueApp } from '../utils/utils';
import {
  ACCTS_HOST,
  ACCTS_HUB_URL,
  ACCTS_OIDC_EMAIL,
  ACCTS_OIDC_PWORD,
  IMAP_PORT,
  KEYCLOAK_ADMIN_BASE_URL,
  KEYCLOAK_ADMIN_CLIENT_ID,
  KEYCLOAK_ADMIN_CLIENT_SECRET,
  KEYCLOAK_REALM_URL,
  PLAYWRIGHT_TAG_E2E_SUITE,
  PRIMARY_THUNDERMAIL_EMAIL,
  SMTP_PORT,
  SMTP_TLS,
  STALWART_OAUTH_CLIENT_ID,
  STALWART_OAUTH_CLIENT_SECRET,
  TIMEOUT_30_SECONDS,
} from '../const/constants';

const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
const TOTP_PERIOD_SECONDS = 30;
const OAUTH_CALLBACK_TIMEOUT = TIMEOUT_30_SECONDS * 3;

const decodeBase32 = (input: string) => {
  const normalized = input.replace(/\s/g, '').replace(/=+$/, '').toUpperCase();
  const bytes: number[] = [];
  let bits = 0;
  let value = 0;

  for (const character of normalized) {
    const index = BASE32_ALPHABET.indexOf(character);
    if (index === -1) {
      throw new Error(`Invalid base32 character: ${character}`);
    }

    value = (value << 5) | index;
    bits += 5;

    if (bits >= 8) {
      bytes.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }

  return Buffer.from(bytes);
};

const makeTotpCode = (manualSecret: string) => {
  const counter = Math.floor(Date.now() / 1000 / TOTP_PERIOD_SECONDS);
  const counterBuffer = Buffer.alloc(8);
  counterBuffer.writeBigUInt64BE(BigInt(counter));
  const digest = crypto.createHmac('sha1', decodeBase32(manualSecret)).update(counterBuffer).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const truncatedHash = digest.readUInt32BE(offset) & 0x7fffffff;
  return String(truncatedHash % 1_000_000).padStart(6, '0');
};

const getKeycloakAdminToken = async () => {
  if (!KEYCLOAK_ADMIN_CLIENT_SECRET || KEYCLOAK_ADMIN_CLIENT_SECRET === 'undefined') {
    throw new Error('KEYCLOAK_ADMIN_CLIENT_SECRET must be set to clean up MFA credentials.');
  }

  const response = await fetch(`${KEYCLOAK_ADMIN_BASE_URL}/realms/master/protocol/openid-connect/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: KEYCLOAK_ADMIN_CLIENT_ID,
      client_secret: KEYCLOAK_ADMIN_CLIENT_SECRET,
      grant_type: 'client_credentials',
    }),
  });
  const data = await response.json();

  if (!response.ok || !data.access_token) {
    throw new Error(`Could not get Keycloak admin token: ${JSON.stringify(data)}`);
  }

  return data.access_token as string;
};

const MFA_CREDENTIAL_TYPES = ['otp', 'recovery-authn-codes'];

const fetchKeycloakCredentials = async () => {
  const adminToken = await getKeycloakAdminToken();
  const headers = { Authorization: `Bearer ${adminToken}`, Accept: 'application/json' };
  const usersResponse = await fetch(
    `${KEYCLOAK_ADMIN_BASE_URL}/admin/realms/tbpro/users?${new URLSearchParams({ username: ACCTS_OIDC_EMAIL, exact: 'true' })}`,
    { headers },
  );
  const users = await usersResponse.json();

  if (!usersResponse.ok || users.length !== 1) {
    throw new Error(`Could not load Keycloak user for cleanup: ${JSON.stringify(users)}`);
  }

  const credentialsResponse = await fetch(
    `${KEYCLOAK_ADMIN_BASE_URL}/admin/realms/tbpro/users/${users[0].id}/credentials`,
    { headers },
  );
  const credentials = await credentialsResponse.json();

  if (!credentialsResponse.ok) {
    throw new Error(`Could not load Keycloak credentials: ${JSON.stringify(credentials)}`);
  }

  return { userId: users[0].id as string, credentials, headers };
};

const removeExistingMfaCredentials = async () => {
  const { userId, credentials, headers } = await fetchKeycloakCredentials();

  for (const credential of credentials.filter((item: { type?: string }) => MFA_CREDENTIAL_TYPES.includes(item.type ?? ''))) {
    const deleteResponse = await fetch(
      `${KEYCLOAK_ADMIN_BASE_URL}/admin/realms/tbpro/users/${userId}/credentials/${credential.id}`,
      { method: 'DELETE', headers },
    );
    if (!deleteResponse.ok) {
      throw new Error(`Could not delete Keycloak credential for cleanup: ${await deleteResponse.text()}`);
    }
  }
};

const getRecoveryCodesCredentialMetadata = async () => {
  const { credentials } = await fetchKeycloakCredentials();
  return credentials
    .filter((item: { type?: string }) => item.type === 'recovery-authn-codes')
    .map((item: { id: string; createdDate?: number }) => ({ id: item.id, createdDate: item.createdDate }));
};

const acceptLegalPoliciesIfRequired = async (page: Page) => {
  const acceptButton = page.getByRole('button', { name: 'Accept policies and continue' });
  if (await acceptButton.isVisible()) {
    await acceptButton.click();
    await waitForVueApp(page);
  }
};

const recoveryCodesDialog = (page: Page) => page.locator('dialog').filter({
  has: page.getByTestId('recovery-codes-list'),
});

const expectRecoveryCodesDialogVisible = async (page: Page) => {
  await expect(recoveryCodesDialog(page)).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
};

const dismissRecoveryCodesDialog = async (page: Page) => {
  await recoveryCodesDialog(page).locator('button.close-button').click();
  await expect(recoveryCodesDialog(page)).toBeHidden({ timeout: TIMEOUT_30_SECONDS });
};

const captureRecoveryCodesAndConfirm = async (page: Page) => {
  await expectRecoveryCodesDialogVisible(page);
  const codeElements = await page.getByTestId('recovery-codes-list').locator('code').all();
  const codes = await Promise.all(codeElements.map((element) => element.innerText()));
  // The ack input is `screen-reader-only`; the visual+clickable element is its
  // <label for="recovery-codes-ack"> sibling, which is what toggles the v-model.
  await page.locator('label[for="recovery-codes-ack"]').click();
  await page.getByTestId('recovery-codes-done').click();
  await expect(recoveryCodesDialog(page)).toBeHidden({ timeout: TIMEOUT_30_SECONDS });
  return codes;
};

const readUntil = async (socket: net.Socket, isComplete: (buffer: string) => boolean) => new Promise<string>((resolve, reject) => {
  let buffer = '';
  const timeout = setTimeout(() => {
    cleanup();
    reject(new Error(`Timed out waiting for mail server response. Last response: ${buffer}`));
  }, TIMEOUT_30_SECONDS);
  const cleanup = () => {
    clearTimeout(timeout);
    socket.off('data', onData);
    socket.off('error', onError);
  };
  const onData = (data: Buffer) => {
    buffer += data.toString('utf8');
    if (isComplete(buffer)) {
      cleanup();
      resolve(buffer);
    }
  };
  const onError = (error: Error) => {
    cleanup();
    reject(error);
  };

  socket.on('data', onData);
  socket.on('error', onError);
});

const isTlsEnabled = (value: string) => !['false', 'none', 'undefined', ''].includes(value.toLowerCase());

const connectToMailServer = async (port: number, useTls = false) => new Promise<net.Socket>((resolve, reject) => {
  const socket = useTls
    ? tls.connect({ host: ACCTS_HOST, port, rejectUnauthorized: false }, () => resolve(socket))
    : net.createConnection({ host: ACCTS_HOST, port }, () => resolve(socket));
  socket.setTimeout(TIMEOUT_30_SECONDS);
  socket.once('error', reject);
  socket.once('timeout', () => {
    socket.destroy();
    reject(new Error(`Timed out connecting to ${ACCTS_HOST}:${port}`));
  });
});

const writeAndRead = async (
  socket: net.Socket,
  command: string,
  isComplete: (buffer: string) => boolean,
) => {
  socket.write(command);
  return readUntil(socket, isComplete);
};

const makeXoauth2Payload = (accessToken: string) => Buffer.from(
  `user=${PRIMARY_THUNDERMAIL_EMAIL}\x01auth=Bearer ${accessToken}\x01\x01`,
).toString('base64');

const expectImapXoauth2Login = async (accessToken: string) => {
  const socket = await connectToMailServer(IMAP_PORT);
  const authPayload = makeXoauth2Payload(accessToken);

  try {
    await readUntil(socket, (response) => response.includes('* OK'));
    const authResponse = await writeAndRead(
      socket,
      `a1 AUTHENTICATE XOAUTH2 ${authPayload}\r\n`,
      (response) => /a1 (OK|NO|BAD)/i.test(response),
    );
    expect(authResponse).toMatch(/a1 OK/i);
    await writeAndRead(socket, 'a2 LOGOUT\r\n', (response) => /a2 OK/i.test(response));
  } finally {
    socket.destroy();
  }
};

const expectSmtpXoauth2Login = async (accessToken: string) => {
  const socket = await connectToMailServer(SMTP_PORT, isTlsEnabled(SMTP_TLS));
  const authPayload = makeXoauth2Payload(accessToken);

  try {
    await readUntil(socket, (response) => /^220/m.test(response));
    await writeAndRead(socket, 'EHLO tb-accounts-e2e.example.org\r\n', (response) => /\r?\n250[ -]/.test(response));
    const authResponse = await writeAndRead(
      socket,
      `AUTH XOAUTH2 ${authPayload}\r\n`,
      (response) => /^(235|334|535|454)/m.test(response),
    );
    expect(authResponse).toMatch(/^235/m);
    await writeAndRead(socket, 'QUIT\r\n', (response) => /^221/m.test(response));
  } finally {
    socket.destroy();
  }
};

const getStalwartAccessTokenViaSso = async (page: Page) => {
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

  // No `prompt=login` — the caller has just signed in with password+OTP, so
  // we deliberately let Keycloak's existing SSO session satisfy the auth request.
  // That's also closer to how Stalwart Web/IMAP/SMTP clients use this OAuth flow
  // (they expect SSO, not a fresh re-auth) and avoids a Firefox/localhost cookie
  // edge case where `prompt=login` + a stale session breaks `KC_RESTART`.
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

test.describe('multi-factor authentication', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('authenticator app setup enables Keycloak login challenge and Stalwart OAuth mail auth', async ({ page }) => {
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

    // Authenticator app row (first); the recovery codes row also surfaces a "Set up" button.
    await page.getByRole('button', { name: 'Set up' }).first().click();
    await expect(page.getByRole('img', { name: 'QR code for authenticator app setup' })).toBeVisible({
      timeout: TIMEOUT_30_SECONDS,
    });
    await expect(page.getByRole('img', { name: 'QR code for authenticator app setup' })).toHaveAttribute(
      'src',
      /data:image\/svg\+xml/,
    );

    await page.getByRole('button', { name: 'Enter code manually' }).click();
    const manualSecret = await page.getByTestId('totp-manual-secret').innerText();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByTestId('totp-code-input').fill(makeTotpCode(manualSecret));
    await page.getByRole('button', { name: 'Continue' }).click();
    // The recovery-codes modal auto-opens after a successful TOTP confirm.
    // This test isn't about recovery codes, so dismiss it to land on the management page.
    await dismissRecoveryCodesDialog(page);
    await expect(page.getByRole('button', { name: 'Remove' })).toBeVisible({ timeout: TIMEOUT_30_SECONDS });

    await page.context().clearCookies();
    await page.goto(ACCTS_HUB_URL);
    await page.getByTestId('username-input').fill(ACCTS_OIDC_EMAIL);
    await page.getByTestId('password-input').fill(ACCTS_OIDC_PWORD);
    await page.getByTestId('submit-btn').click();

    await expect(page.getByTestId('otp-input')).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await page.getByTestId('otp-input').fill(makeTotpCode(manualSecret));
    await page.getByTestId('submit-btn').click();
    await waitForVueApp(page);

    // The accounts login above established a Keycloak SSO session at acr=2.
    // Stalwart's OAuth flow should reuse that session and immediately return a code.
    const accessToken = await getStalwartAccessTokenViaSso(page);
    await expectImapXoauth2Login(accessToken);
    await expectSmtpXoauth2Login(accessToken);
  });

  test('recovery codes lifecycle: chained setup, edit-dismiss preserves codes, removal', async ({ page }) => {
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

    // Set up TOTP — recovery codes modal auto-opens after a successful confirm.
    await page.getByRole('button', { name: 'Set up' }).first().click();
    await page.getByRole('button', { name: 'Enter code manually' }).click();
    const manualSecret = await page.getByTestId('totp-manual-secret').innerText();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByTestId('totp-code-input').fill(makeTotpCode(manualSecret));
    await page.getByRole('button', { name: 'Continue' }).click();

    // Verify the modal opens automatically and shows 12 codes.
    await expectRecoveryCodesDialogVisible(page);
    await expect(page.getByTestId('recovery-codes-list').locator('code')).toHaveCount(12);
    // Done is disabled until the user acknowledges saving the codes.
    await expect(page.getByTestId('recovery-codes-done')).toBeDisabled();

    // Dismissing the modal must NOT write a credential to Keycloak — old codes
    // (or in this case, the absence of any) must remain authoritative.
    await dismissRecoveryCodesDialog(page);
    expect(await getRecoveryCodesCredentialMetadata()).toEqual([]);
    const recoveryRow = page.locator('.authentication-method').filter({ hasText: 'Recovery codes' });
    await expect(recoveryRow.getByRole('button', { name: 'Set up' })).toBeVisible();

    // Trigger setup again from the Recovery codes row and capture the codes this time.
    await recoveryRow.getByRole('button', { name: 'Set up' }).click();
    const firstSetCodes = await captureRecoveryCodesAndConfirm(page);
    expect(firstSetCodes).toHaveLength(12);
    await expect(recoveryRow.getByRole('button', { name: 'Edit' })).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    const credentialAfterFirstSetup = await getRecoveryCodesCredentialMetadata();
    expect(credentialAfterFirstSetup).toHaveLength(1);

    // Edit + dismiss: server has cached new codes but must not have replaced the
    // committed credential. The Keycloak credential id/createdDate should be unchanged.
    await recoveryRow.getByRole('button', { name: 'Edit' }).click();
    await expectRecoveryCodesDialogVisible(page);
    const previewedCodeElements = await page.getByTestId('recovery-codes-list').locator('code').all();
    const previewedCodes = await Promise.all(previewedCodeElements.map((element) => element.innerText()));
    expect(previewedCodes).toHaveLength(12);
    expect(previewedCodes).not.toEqual(firstSetCodes);
    await dismissRecoveryCodesDialog(page);
    expect(await getRecoveryCodesCredentialMetadata()).toEqual(credentialAfterFirstSetup);

    // Edit + confirm: this time the credential should be replaced.
    await recoveryRow.getByRole('button', { name: 'Edit' }).click();
    const replacedCodes = await captureRecoveryCodesAndConfirm(page);
    expect(replacedCodes).toHaveLength(12);
    expect(replacedCodes).not.toEqual(firstSetCodes);
    const credentialAfterReplacement = await getRecoveryCodesCredentialMetadata();
    expect(credentialAfterReplacement).toHaveLength(1);
    expect(credentialAfterReplacement[0].id).not.toBe(credentialAfterFirstSetup[0].id);

    // Remove: the credential should be deleted from Keycloak.
    await recoveryRow.getByRole('button', { name: 'Remove' }).click();
    await page.locator('dialog').getByRole('button', { name: 'Remove' }).click();
    await expect(recoveryRow.getByRole('button', { name: 'Set up' })).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    expect(await getRecoveryCodesCredentialMetadata()).toEqual([]);
  });
});
