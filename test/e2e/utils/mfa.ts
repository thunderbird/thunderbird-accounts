import { expect, type Page } from '@playwright/test';

import { ACCTS_HUB_URL, ACCTS_OIDC_EMAIL, ACCTS_OIDC_PWORD, TIMEOUT_30_SECONDS } from '../const/constants';
import { waitForVueApp } from './utils';
import { makeTotpCode, TOTP_PERIOD_SECONDS } from './totp';

export const acceptLegalPoliciesIfRequired = async (page: Page) => {
  const acceptButton = page.getByRole('button', { name: 'Accept policies and continue' });
  if (await acceptButton.isVisible()) {
    await acceptButton.click();
    await waitForVueApp(page);
  }
};

export const recoveryCodesDialog = (page: Page) =>
  page.locator('dialog').filter({
    has: page.getByTestId('recovery-codes-modal'),
  });

export const expectRecoveryCodesDialogVisible = async (page: Page) => {
  await expect(recoveryCodesDialog(page)).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
};

export const dismissRecoveryCodesDialog = async (page: Page) => {
  await recoveryCodesDialog(page).locator('button.close-button').click();
  await expect(recoveryCodesDialog(page)).toBeHidden({ timeout: TIMEOUT_30_SECONDS });
};

// The modal opens on a confirmation step ("this resets your old codes"); continuing
// generates and immediately commits the new codes, then displays them once.
export const continueToRecoveryCodes = async (page: Page) => {
  await expectRecoveryCodesDialogVisible(page);
  await page.getByTestId('recovery-codes-continue').click();
  await expect(page.getByTestId('recovery-codes-list').locator('code')).toHaveCount(12, {
    timeout: TIMEOUT_30_SECONDS,
  });
};

export const captureRecoveryCodesAndConfirm = async (page: Page) => {
  await continueToRecoveryCodes(page);
  const codeElements = await page.getByTestId('recovery-codes-list').locator('code').all();
  const codes = await Promise.all(codeElements.map((element) => element.innerText()));
  // The ack input is `screen-reader-only`; click its label because that toggles the v-model.
  await page.locator('label[for="recovery-codes-ack"]').click();
  await page.getByTestId('recovery-codes-done').click();
  await expect(recoveryCodesDialog(page)).toBeHidden({ timeout: TIMEOUT_30_SECONDS });
  return codes;
};

export const signInWithPassword = async (page: Page) => {
  await page.context().clearCookies();
  await page.goto(ACCTS_HUB_URL);
  await page.getByTestId('username-input').fill(ACCTS_OIDC_EMAIL);
  await page.getByTestId('password-input').fill(ACCTS_OIDC_PWORD);
  await page.getByTestId('submit-btn').click();
};

// Sets up an authenticator app via the management UI and leaves the auto-chained
// recovery-codes modal open on its confirmation step.
export const setUpAuthenticatorApp = async (page: Page) => {
  await page.getByRole('button', { name: 'Set up' }).first().click();
  await page.getByRole('button', { name: 'Enter code manually' }).click();
  const manualSecret = await page.getByTestId('totp-manual-secret').innerText();
  await page.getByRole('button', { name: 'Continue' }).click();
  const enrollmentCode = makeTotpCode(manualSecret);
  await page.getByTestId('totp-code-input').fill(enrollmentCode);
  await page.getByRole('button', { name: 'Continue' }).click();
  return { manualSecret, enrollmentCode };
};

// Keycloak's OTP policy rejects code reuse, so wait for a new TOTP period when needed.
const freshTotpCode = async (page: Page, manualSecret: string, lastUsedCode: string) => {
  let code = makeTotpCode(manualSecret);
  if (code === lastUsedCode) {
    const msUntilNextPeriod = (TOTP_PERIOD_SECONDS - (Math.floor(Date.now() / 1000) % TOTP_PERIOD_SECONDS)) * 1000;
    await page.waitForTimeout(msUntilNextPeriod + 500);
    code = makeTotpCode(manualSecret);
  }
  return code;
};

export const completeOtpChallenge = async (page: Page, manualSecret: string, lastUsedCode: string) => {
  const otpInput = page.getByTestId('otp-input');
  let code = await freshTotpCode(page, manualSecret, lastUsedCode);

  for (let attempt = 0; attempt < 3; attempt++) {
    await expect(otpInput).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await otpInput.fill(code);
    await page.getByTestId('submit-btn').click();
    try {
      await page.waitForURL((url) => !url.pathname.startsWith('/realms/'), { timeout: 10_000 });
      return code;
    } catch {
      code = await freshTotpCode(page, manualSecret, code);
    }
  }
  throw new Error('Keycloak did not accept the OTP challenge after 3 attempts.');
};

// The recovery-code login page prompts for a specific 1-indexed code number.
export const submitRequestedRecoveryCode = async (page: Page, codes: string[]) => {
  const input = page.getByTestId('recovery-code-input');
  await expect(input).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
  const promptText = await page.locator('#kc-recovery-code-login-form').innerText();
  const requestedNumber = Number(promptText.match(/#\s*(\d+)/)?.[1] ?? '1');
  await input.fill(codes[requestedNumber - 1]);
  await page.getByTestId('submit-btn').click();
};
