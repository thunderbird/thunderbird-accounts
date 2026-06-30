import { test, expect } from '@playwright/test';
import { TbAcctsSignUpPage } from '../../pages/tb-accts-signup-page';
import { authFile, isAllowListEnabled, navigateToAccountsHubAndSignIn, waitForVueApp } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  TB_PRO_WAIT_LIST_URL,
  ACCTS_CONTACT_URL,
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
} from '../../const/constants';

let signUpPage: TbAcctsSignUpPage;

// be sure to re-enable these tests once 986 is resolved
//test.skip(true, 'Temporarily disabled due to issue 986');

test.beforeEach(async ({ page }, testInfo) => {
  console.log('inside authenticate setup, about to call navigate and sign in');
  // Perform authentication steps
  await navigateToAccountsHubAndSignIn(page);

  // End of authentication steps, save the auth
  await page.context().storageState({ path: authFile });

  signUpPage = new TbAcctsSignUpPage(page, testInfo.project.name);
  // We need to land on a page that we can stay on to retrieve a csrftoken.
  await page.goto(ACCTS_CONTACT_URL);

  test.skip(!(await isAllowListEnabled(page)), 'Only enabled if backend\'s .env includes USE_ALLOW_LIST=True');
});


test.describe('sign up form on browser', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE, PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY, PLAYWRIGHT_TAG_E2E_SUITE_MOBILE, PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY],
}, () => {
  test('form successfully submits', async ({ page }) => {    
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testEmail: string = `${testUsername}@example.com`;
    const testPassword: string = 'this-is-my-password-and-it-is-long';

    await signUpPage.setupTest(testEmail);
    await waitForVueApp(page);

    await signUpPage.fillForm(testUsername, testPassword, testPassword);
    await signUpPage.submitForm();

    await expect.poll(async () => {
      return await signUpPage.stepId.inputValue();
    }).toBe('step-check-your-mail');
  });

  test('sign-up flow starts on confirm plan step', async ({ page }) => {
    const testEmail: string = `${crypto.randomUUID().replaceAll('-', '')}@example.com`;

    await signUpPage.setupTest(testEmail);
    await waitForVueApp(page);

    await expect(signUpPage.stepId).toHaveValue('step-confirm-plan');
    await expect(signUpPage.formTitle).toHaveText('Confirm plan');
  });

  test('step username fails with bad username', async ({ page }) => {
    // Local part of an email address cannot contain the '@' character.
    const testUsername: string = 'IM@A@BAD@LOCAL@PART@OF@AN@EMAIL';
    const testEmail: string = `${crypto.randomUUID().replaceAll('-', '')}@example.com`;

    await signUpPage.setupTest(testEmail);
    await waitForVueApp(page);

    await signUpPage.confirmPlan();
    await signUpPage.userNameInput?.fill(testUsername);
    await signUpPage.submitForm();

    // Make sure we're still on the username step
    await expect(signUpPage.stepId).toHaveValue('step-username');

    const errorText = page.getByText('This username is not valid. Try another one.');
    await expect(errorText).toBeVisible();
  });

  test('step password fails with password length below minimum', async ({ page }) => {
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testEmail: string = `${testUsername}@example.com`;
    const testPassword: string = 'this-is-my-password-and-it-is-long';
    const testConfirmPassword: string = 'yay';

    await signUpPage.setupTest(testEmail);
    await waitForVueApp(page);

    await signUpPage.fillForm(testUsername, testPassword, testConfirmPassword);
    await signUpPage.submitForm();

    const errorText = page.getByText('12 characters');
    await expect(errorText).toBeVisible();
  });

  test('step password fails with password mismatch', async ({ page }) => {
    const testUsername: string = crypto.randomUUID().replaceAll('-', '');
    const testEmail: string = `${testUsername}@example.com`;
    const testPassword: string = 'this-is-my-password-and-it-is-long';
    const testConfirmPassword: string = 'this-is-my-password-and-it-is-long-tpyo';

    await signUpPage.setupTest(testEmail);
    await waitForVueApp(page);

    await signUpPage.fillForm(testUsername, testPassword, testConfirmPassword);
    await signUpPage.submitForm();

    const errorText = page.getByText('Password and confirm password must match.');
    await expect(errorText).toBeVisible();
  });

  test('sign-up flow punts user to wait list if not on allow list', async ({ page }) => {
    const testEmail: string = `${crypto.randomUUID().replaceAll('-', '')}@example.com`;

    await signUpPage.setupTest(testEmail, false);

    // tb.pro may insert a locale prefix (e.g. /en-US/waitlist/) when redirecting
    await page.waitForLoadState('domcontentloaded');
    const waitListOrigin = new URL(TB_PRO_WAIT_LIST_URL).origin;
    await page.waitForURL(
      url => url.origin === waitListOrigin
        && url.pathname.endsWith('/waitlist/')
        && url.searchParams.get('email') === testEmail,
    );
  });

  test('sign-up flow punts user to wait list if they dont pass an email in', async ({ page }) => {
    await signUpPage.setupTest(null, false);

    // tb.pro may insert a locale prefix (e.g. /en-US/waitlist/) when redirecting
    await page.waitForLoadState('domcontentloaded');
    const waitListOrigin = new URL(TB_PRO_WAIT_LIST_URL).origin;
    await page.waitForURL(
      url => url.origin === waitListOrigin
        && url.pathname.endsWith('/waitlist/')
        && !url.searchParams.get('email'),
    );
  });
});

