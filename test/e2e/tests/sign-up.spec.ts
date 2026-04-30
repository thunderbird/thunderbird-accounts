import { TB_PRO_WAIT_LIST_URL } from '../const/constants';
import { test, expect } from '@playwright/test';
import { TbAcctsSignUpPage } from '../pages/tb-accts-signup-page';
import { isAllowListEnabled, waitForVueApp } from '../utils/utils';

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
    test.skip(!(await isAllowListEnabled(page)), 'Only enabled if backend\'s .env includes USE_ALLOW_LIST=True');
    
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testEmail: string = `${testUsername}@example.com`;
    const testPassword: string = 'this-is-my-password-and-it-is-long';

    await signUpPage.fillForm(testUsername, testPassword, testPassword, testEmail);
    await signUpPage.submitForm();

    // new page!
    await page.waitForLoadState('domcontentloaded');
    await page.waitForURL(`${TB_PRO_WAIT_LIST_URL}?email=${encodeURIComponent(testEmail)}`);
  });

  test('navigating to sign-up with query param pre-fills form', async ({ page }) => {
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testPassword: string = 'this-is-my-password-and-it-is-long';

    const verificationEmail = 'test@example.com';
    await page.goto(`${ACCTS_SIGN_UP_URL}?email=${verificationEmail}`);
    await waitForVueApp(page);


    await signUpPage.fillForm(testUsername, testPassword, testPassword);
    await signUpPage.submitForm();

    expect(signUpPage.verificationEmailInput).toBeTruthy();
    await expect(signUpPage.verificationEmailInput).toHaveValue(verificationEmail);
  });

  test('step username fails with bad username', async ({ page }) => {
    // Local part of an email address cannot contain the '@' character.
    const testUsername: string = 'IM@A@BAD@LOCAL@PART@OF@AN@EMAIL';

    await signUpPage.userNameInput?.fill(testUsername);
    await signUpPage.submitForm();

    // Make sure we're still on the first step
    await expect(signUpPage.stepId).toHaveValue('step-username');

    const errorText = page.getByText('This username is not valid. Try another one.');
    await expect(errorText).toBeVisible();
  });

  test('step password fails with password length below minimum', async ({ page }) => {
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testPassword: string = 'this-is-my-password-and-it-is-long';
    const testConfirmPassword: string = 'yay';

    await signUpPage.fillForm(testUsername, testPassword, testConfirmPassword);
    await signUpPage.submitForm();

    const errorText = page.getByText('12 characters');
    await expect(errorText).toBeVisible();
  });

  test('step password fails with password mismatch', async ({ page }) => {
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testPassword: string = 'this-is-my-password-and-it-is-long';
    const testConfirmPassword: string = 'this-is-my-password-and-it-is-long-tpyo';

    await signUpPage.fillForm(testUsername, testPassword, testConfirmPassword);
    await signUpPage.submitForm();

    const errorText = page.getByText('Password and confirm password must match.');
    await expect(errorText).toBeVisible();
  });
});
