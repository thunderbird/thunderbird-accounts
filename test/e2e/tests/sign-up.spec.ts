import path from 'path';
import { TB_PRO_WAIT_LIST_URL } from '../const/constants';
import { test, expect } from '@playwright/test';
import { TbAcctsSignUpPage } from '../pages/tb-accts-signup-page';
import { ensureWeAreSignedIn, waitForVueApp, showPageConsoleLog } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  ACCTS_OIDC_EMAIL,
  ACCTS_RECOVERY_EMAIL,
  TIMEOUT_2_SECONDS,
  TIMEOUT_5_SECONDS,
  TIMEOUT_30_SECONDS,
  ACCTS_SIGN_UP_URL,
} from '../const/constants';

let signUpPage: TbAcctsSignUpPage;

test.beforeEach(async ({ page }) => {
  signUpPage = new TbAcctsSignUpPage(page);
  await signUpPage.navigateToPage();
});

test.describe('sign up form', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE, PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY],
}, () => {
  test('form successfully submits but is not on allow list', async ({ page }) => {
    
    // Test that no query params = empty recovery email
    expect(signUpPage.recoveryEmailInput === '');

    // go to the contact / submit an issue form and wait for it to load
    const randomUUID = crypto.randomUUID().replaceAll('-', '');
    await signUpPage.fillForm(randomUUID, 'test@example.com', 'abc123', 'abc123');
    await signUpPage.submitForm();

    // new page!
    await page.waitForLoadState('networkidle');
    expect(page.url() === TB_PRO_WAIT_LIST_URL);
  });

  /* Commented out until we figure out allow list between tests
  test('form successfully submits but is on allow list', async ({ page }) => {
    await showPageConsoleLog(page);
    // go to the contact / submit an issue form and wait for it to load
    const randomUUID = crypto.randomUUID().replaceAll('-', '');
    await signUpPage.fillForm(randomUUID, 'test@example.org', 'abc123', 'abc123');
    await signUpPage.submitForm();

    // new page!
    await waitForVueApp(page);
    expect(page.url() === ACCTS_SUBSCRIBE_URL);
  });
  */

  test('navigating to sign-up with query param pre-fills form', async ({ page }) => {
    const recoveryEmail = 'test@example.com';
    await page.goto(`${ACCTS_SIGN_UP_URL}?email=${recoveryEmail}`);
    await waitForVueApp(page);

    expect(signUpPage.recoveryEmailInput !== '');
    expect(signUpPage.recoveryEmailInput === recoveryEmail);
  });


});
