import { TB_PRO_WAIT_LIST_URL } from '../const/constants';
import { test, expect } from '@playwright/test';
import { TbAcctsSignUpPage } from '../pages/tb-accts-signup-page';
import { waitForVueApp } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  ACCTS_SIGN_UP_URL,
} from '../const/constants';

let signUpPage: TbAcctsSignUpPage;

test.beforeEach(async ({ page }) => {
  // Remove any authentication cookies before passing it to our page
  await page.context().clearCookies();
  // Ensure we're cookieless.
  expect(await page.context().cookies()).toEqual([])

  signUpPage = new TbAcctsSignUpPage(page);
  await signUpPage.navigateToPage();
});

test.describe('sign up form', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE, PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY],
}, () => {
  test('form successfully submits but is not on allow list', async ({ page }) => {
    const testEmail: string = 'test@example.com';

    // Test that no query params = empty recovery email
    await expect(signUpPage.recoveryEmailInput).toBeEmpty();

    // go to the contact / submit an issue form and wait for it to load
    const randomUUID = crypto.randomUUID().replaceAll('-', '');
    await signUpPage.fillForm(randomUUID, testEmail, 'abc123', 'abc123');
    await signUpPage.submitForm();

    // new page!
    await page.waitForLoadState('domcontentloaded');
    expect(page.url()).toEqual(`${TB_PRO_WAIT_LIST_URL}?email=${encodeURIComponent(testEmail)}`);
  });

  test('navigating to sign-up with query param pre-fills form', async ({ page }) => {
    const recoveryEmail = 'test@example.com';
    await page.goto(`${ACCTS_SIGN_UP_URL}?email=${recoveryEmail}`);
    await waitForVueApp(page);

    expect(signUpPage.recoveryEmailInput).toBeTruthy();
    await expect(signUpPage.recoveryEmailInput).toHaveValue(recoveryEmail);
  });
});
