import { test, expect } from '@playwright/test';

import { ensureWeAreSignedIn, waitForVueApp } from '../utils/utils';
import {
  ACCTS_HUB_URL,
  ACCTS_OIDC_EMAIL,
  ACCTS_OIDC_PWORD,
  KEYCLOAK_ADMIN_CLIENT_SECRET,
  PLAYWRIGHT_TAG_E2E_SUITE,
  TIMEOUT_30_SECONDS,
} from '../const/constants';
import {
  fetchKeycloakCredentials,
  getRecoveryCodesCredentialMetadata,
  getUserSessionIds,
  MFA_CREDENTIAL_TYPES,
  removeExistingMfaCredentials,
} from '../utils/keycloak-admin';
import { expectImapXoauth2Login, expectSmtpXoauth2Login } from '../utils/mail-protocol';
import {
  acceptLegalPoliciesIfRequired,
  captureRecoveryCodesAndConfirm,
  completeOtpChallenge,
  dismissRecoveryCodesDialog,
  enableMfaFeatureFlag,
  expectRecoveryCodesDialogVisible,
  recoveryCodesDialog,
  setUpAuthenticatorApp,
  signInWithPassword,
  submitRequestedRecoveryCode,
} from '../utils/mfa';
import { getStalwartAccessTokenViaSso } from '../utils/oauth';
import { makeTotpCode } from '../utils/totp';

test.describe('multi-factor authentication', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {

  test.skip((!KEYCLOAK_ADMIN_CLIENT_SECRET) || KEYCLOAK_ADMIN_CLIENT_SECRET === 'undefined', 'KEYCLOAK_ADMIN_CLIENT_SECRET is needed for this test to run.');

  // Manage MFA is gated behind the multi-factor-authentication waffle flag; enable it
  // per-browser so the /manage-mfa route is registered before any test navigates to it.
  test.beforeEach(async ({ page }) => {
    await enableMfaFeatureFlag(page);
  });

  // Always leave the account credential-clean, even if a test fails partway through
  // enrolment; otherwise leftover MFA blocks password-only sign-in in setup.
  test.afterEach(async () => {
    await removeExistingMfaCredentials();
  });

  test('authenticator app setup enables Keycloak login challenge and Stalwart OAuth mail auth', async ({ page }) => {
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

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
    const enrollmentCode = makeTotpCode(manualSecret);
    await page.getByTestId('totp-code-input').fill(enrollmentCode);
    await page.getByRole('button', { name: 'Continue' }).click();
    await dismissRecoveryCodesDialog(page);
    await expect(page.getByRole('button', { name: 'Remove' })).toBeVisible({ timeout: TIMEOUT_30_SECONDS });

    await page.context().clearCookies();
    await page.goto(ACCTS_HUB_URL);
    await page.getByTestId('username-input').fill(ACCTS_OIDC_EMAIL);
    await page.getByTestId('password-input').fill(ACCTS_OIDC_PWORD);
    await page.getByTestId('submit-btn').click();

    await completeOtpChallenge(page, manualSecret, enrollmentCode);
    await waitForVueApp(page);

    const accessToken = await getStalwartAccessTokenViaSso(page);
    await expectImapXoauth2Login(accessToken);
    await expectSmtpXoauth2Login(accessToken);
  });

  test('recovery codes lifecycle: chained setup, confirm-cancel preserves codes, removal', async ({ page }) => {
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

    await page.getByRole('button', { name: 'Set up' }).first().click();
    await page.getByRole('button', { name: 'Enter code manually' }).click();
    const manualSecret = await page.getByTestId('totp-manual-secret').innerText();
    await page.getByRole('button', { name: 'Continue' }).click();
    await page.getByTestId('totp-code-input').fill(makeTotpCode(manualSecret));
    await page.getByRole('button', { name: 'Continue' }).click();

    await expectRecoveryCodesDialogVisible(page);
    await expect(page.getByTestId('recovery-codes-continue')).toBeVisible({ timeout: TIMEOUT_30_SECONDS });

    await dismissRecoveryCodesDialog(page);
    expect(await getRecoveryCodesCredentialMetadata()).toEqual([]);
    const recoveryRow = page.locator('.authentication-method').filter({ hasText: 'Recovery codes' });
    await expect(recoveryRow.getByRole('button', { name: 'Set up' })).toBeVisible();

    await recoveryRow.getByRole('button', { name: 'Set up' }).click();
    const firstSetCodes = await captureRecoveryCodesAndConfirm(page);
    expect(firstSetCodes).toHaveLength(12);
    await expect(recoveryRow.getByRole('button', { name: 'Regenerate' })).toBeVisible({
      timeout: TIMEOUT_30_SECONDS,
    });
    const credentialAfterFirstSetup = await getRecoveryCodesCredentialMetadata();
    expect(credentialAfterFirstSetup).toHaveLength(1);

    await recoveryRow.getByRole('button', { name: 'Regenerate' }).click();
    await expectRecoveryCodesDialogVisible(page);
    await dismissRecoveryCodesDialog(page);
    expect(await getRecoveryCodesCredentialMetadata()).toEqual(credentialAfterFirstSetup);

    await recoveryRow.getByRole('button', { name: 'Regenerate' }).click();
    const replacedCodes = await captureRecoveryCodesAndConfirm(page);
    expect(replacedCodes).toHaveLength(12);
    expect(replacedCodes).not.toEqual(firstSetCodes);
    const credentialAfterReplacement = await getRecoveryCodesCredentialMetadata();
    expect(credentialAfterReplacement).toHaveLength(1);
    expect(credentialAfterReplacement[0].id).not.toBe(credentialAfterFirstSetup[0].id);

    await recoveryRow.getByRole('button', { name: 'Remove' }).click();
    await page.locator('dialog').getByRole('button', { name: 'Remove' }).click();
    await expect(recoveryRow.getByRole('button', { name: 'Set up' })).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    expect(await getRecoveryCodesCredentialMetadata()).toEqual([]);
  });

  test('recovery codes require an authenticator app and are removed along with it', async ({ page }) => {
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

    const recoveryRow = page.locator('.authentication-method').filter({ hasText: 'Recovery codes' });

    await expect(page.getByTestId('mfa-recoveryCodes-setup-button')).toBeDisabled();
    await expect(recoveryRow).toContainText('Set up an authenticator app first');

    await setUpAuthenticatorApp(page);
    const codes = await captureRecoveryCodesAndConfirm(page);
    expect(codes).toHaveLength(12);
    await expect(recoveryRow.getByRole('button', { name: 'Regenerate' })).toBeVisible({
      timeout: TIMEOUT_30_SECONDS,
    });

    await page.getByTestId('mfa-authenticatorApp-remove-button').click();
    await page.locator('dialog').getByRole('button', { name: 'Remove' }).click();
    await expect(page.getByTestId('mfa-authenticatorApp-setup-button')).toBeVisible({
      timeout: TIMEOUT_30_SECONDS,
    });
    await expect(page.getByTestId('mfa-recoveryCodes-setup-button')).toBeDisabled();

    const { credentials } = await fetchKeycloakCredentials();
    expect(credentials.filter((item: { type?: string }) => MFA_CREDENTIAL_TYPES.includes(item.type ?? ''))).toEqual([]);
  });

  test('regenerating recovery codes after a fresh sign-in requires identity verification', async ({ page }) => {
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

    const { manualSecret, enrollmentCode } = await setUpAuthenticatorApp(page);
    const initialCodes = await captureRecoveryCodesAndConfirm(page);
    expect(initialCodes).toHaveLength(12);
    const initialCredential = await getRecoveryCodesCredentialMetadata();
    expect(initialCredential).toHaveLength(1);

    await signInWithPassword(page);
    const signInCode = await completeOtpChallenge(page, manualSecret, enrollmentCode);
    await waitForVueApp(page);

    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await expect(page.getByRole('heading', { name: 'Verify your identity' })).toBeVisible({
      timeout: TIMEOUT_30_SECONDS,
    });

    await page.getByRole('button', { name: 'Verify', exact: true }).click();

    const otpInput = page.getByTestId('otp-input');
    const usernameInput = page.getByTestId('username-input');
    await expect(otpInput.or(usernameInput).first()).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    if (await usernameInput.isVisible()) {
      await usernameInput.fill(ACCTS_OIDC_EMAIL);
      await page.getByTestId('password-input').fill(ACCTS_OIDC_PWORD);
      await page.getByTestId('submit-btn').click();
    }
    await completeOtpChallenge(page, manualSecret, signInCode);
    await waitForVueApp(page);

    const recoveryRow = page.locator('.authentication-method').filter({ hasText: 'Recovery codes' });
    await recoveryRow.getByRole('button', { name: 'Regenerate' }).click();
    const replacedCodes = await captureRecoveryCodesAndConfirm(page);
    expect(replacedCodes).toHaveLength(12);
    expect(replacedCodes).not.toEqual(initialCodes);
    const replacedCredential = await getRecoveryCodesCredentialMetadata();
    expect(replacedCredential).toHaveLength(1);
    expect(replacedCredential[0].id).not.toBe(initialCredential[0].id);

    await removeExistingMfaCredentials();
  });

  test('"sign out from other devices" during setup ends other sessions but keeps the current one', async ({
    page,
    browser,
  }) => {
    // Regression guard for #1005: the old "logout other sessions" call was logout-ALL and
    // evicted the enrolling device too, so the user hit "session expired" moments later.
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

    // Second device: a separate context with its own Keycloak session. The account has no
    // MFA yet, so a password-only sign-in succeeds.
    const otherDevice = await browser.newContext();
    try {
      const idsBeforeOtherDevice = new Set(await getUserSessionIds());
      const otherPage = await otherDevice.newPage();
      await signInWithPassword(otherPage);
      await expect(otherPage.getByRole('banner').locator('.avatar')).toBeVisible({ timeout: TIMEOUT_30_SECONDS });

      const otherDeviceSessionId = (await getUserSessionIds()).find((id) => !idsBeforeOtherDevice.has(id));
      expect(otherDeviceSessionId, 'second device should create a new Keycloak session').toBeTruthy();

      // Enrol the authenticator on the current device with "sign out from other devices" on.
      await setUpAuthenticatorApp(page, { logoutOtherSessions: true });

      // The recovery-codes step immediately follows and calls the provider with the
      // current access token. This is the exact next interaction that failed "session
      // expired" before the fix; it succeeding proves the current device stayed signed in.
      const codes = await captureRecoveryCodesAndConfirm(page);
      expect(codes).toHaveLength(12);

      // ...and the other device's session is terminated.
      await expect
        .poll(async () => await getUserSessionIds(), { timeout: TIMEOUT_30_SECONDS })
        .not.toContain(otherDeviceSessionId);
    } finally {
      await otherDevice.close();
    }
  });

  test('"try another way" lists the authenticator first and signs in via a recovery code', async ({ page }) => {
    await ensureWeAreSignedIn(page);
    await acceptLegalPoliciesIfRequired(page);
    await page.goto(`${ACCTS_HUB_URL}/manage-mfa`);
    await waitForVueApp(page);
    await removeExistingMfaCredentials();
    await page.reload();
    await waitForVueApp(page);

    await setUpAuthenticatorApp(page);
    const codes = await captureRecoveryCodesAndConfirm(page);
    expect(codes).toHaveLength(12);

    await signInWithPassword(page);
    await page.getByTestId('try-another-way-btn').click();

    await expect(page.locator('.select-auth-item__title')).toHaveText(['Authenticator App', 'Recovery Code'], {
      timeout: TIMEOUT_30_SECONDS,
    });

    await page.getByRole('button', { name: /Recovery Code/ }).click();
    await submitRequestedRecoveryCode(page, codes);

    await waitForVueApp(page);
    await expect(page.getByRole('banner').locator('.avatar')).toBeVisible({ timeout: TIMEOUT_30_SECONDS });

    await removeExistingMfaCredentials();
  });
});
