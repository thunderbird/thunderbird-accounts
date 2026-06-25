import { test, expect } from '@playwright/test';
import { TbAcctsSignUpPage } from '../../pages/tb-accts-signup-page';
import { isAllowListEnabled, waitForVueApp } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  TB_PRO_WAIT_LIST_URL,
  ACCTS_SIGN_UP_URL,
} from '../../const/constants';

let signUpPage: TbAcctsSignUpPage;

// be sure to re-enable these tests once 986 is resolved
test.skip(true, 'Temporarily disabled due to issue 986');

test.beforeEach(async ({ page }, testInfo) => {
  // Remove any authentication cookies before passing it to our page
  await page.context().clearCookies();
  // Ensure we're cookieless.
  expect(await page.context().cookies()).toEqual([])

  signUpPage = new TbAcctsSignUpPage(page, testInfo.project.name);
  await signUpPage.navigateToPage();
});

test.describe('sign up form on mobile browser', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE_MOBILE, PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY],
}, () => {
  test('form successfully submits but is not on allow list', async ({ page }) => {
    test.skip(!(await isAllowListEnabled(page)), 'Only enabled if backend\'s .env includes USE_ALLOW_LIST=True');
    
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testEmail: string = `${testUsername}@example.com`;
    const testPassword: string = 'this-is-my-password-and-it-is-long';

    await signUpPage.fillForm(testUsername, testPassword, testPassword, testEmail);
    await signUpPage.submitForm();

    // tb.pro may insert a locale prefix (e.g. /en-US/waitlist/) when redirecting
    await page.waitForLoadState('domcontentloaded');
    const waitListOrigin = new URL(TB_PRO_WAIT_LIST_URL).origin;
    await page.waitForURL(
      url => url.origin === waitListOrigin
        && url.pathname.endsWith('/waitlist/')
        && url.searchParams.get('email') === testEmail,
    );
  });

  test('sign-up flow starts on confirm plan step', async () => {
    await expect.poll(async () => {
      return await signUpPage.stepId.inputValue();
    }).toBe('step-confirm-plan');

    await expect.poll(async () => {
      return await signUpPage.formTitle.textContent();
    }).toBe('Confirm plan');
  });

  test('navigating to sign-up with query param pre-fills form', async ({ page }) => {
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testPassword: string = 'this-is-my-password-and-it-is-long';

    const verificationEmail = 'test@example.com';
    await page.goto(`${ACCTS_SIGN_UP_URL}?email=${verificationEmail}`);
    await waitForVueApp(page);

    await signUpPage.fillForm(testUsername, testPassword, testPassword);
    expect(signUpPage.verificationEmailInput).toBeTruthy();
    
    // locator.toHaveValue is not supported in iOS BrowserStack so must get value then verify it
    await expect.poll(async () => {
      return await signUpPage.verificationEmailInput?.inputValue();
    }).toBe(verificationEmail);
  });

  test('step username fails with bad username', async ({ page }) => {
    // Local part of an email address cannot contain the '@' character.
    const testUsername: string = 'IM@A@BAD@LOCAL@PART@OF@AN@EMAIL';

    await signUpPage.confirmPlan();
    await signUpPage.userNameInput?.fill(testUsername);
    await signUpPage.submitForm();

    // Make sure we're still on the username step
    // locator.toHaveValue is not supported in iOS BrowserStack so must get value then verify it
    await expect.poll(async () => {
      return await signUpPage.stepId.inputValue();
    }).toBe('step-username');

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
