import { test, expect } from '@playwright/test';
import { FxAPage } from '../pages/fxa-page';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  EMAIL_SIGN_UP_EMAIL_ADDRESS,
  ACCTS_FXA_EMAIL,
  EMAIL_SIGN_UP_DOMAIN,
  EMAIL_SIGN_UP_APP_PWORD,
  MOCK_RESPONSE_OK,
 } from '../const/constants';
import { EmailSignUpPage } from '../pages/email-sign-up-page';

let fxaPage: FxAPage;
let emailSignUpPage: EmailSignUpPage;

test.beforeEach(async ({ page }) => {
  fxaPage = new FxAPage(page);
  // we are already signed into accounts via our auth.setup
  emailSignUpPage = new EmailSignUpPage(page);
  await emailSignUpPage.navigateToEmailSignUpPage();
});

test.describe('email sign-up', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('able to sign up for a thundermail email address', async ({ page }) => {
    // capture the POST /sign-up/submit and mock the response so that we don't
    // actually create a new email account
    await page.route('*/**/sign-up/submit', async (route, request) => {
      console.log('captured POST /sign-up/submit and mocking the response');

      // verify the captured request body is as expected
      var capturedBody = await request.postDataJSON();
      expect(capturedBody['email_address']).toBe(EMAIL_SIGN_UP_EMAIL_ADDRESS);
      expect(capturedBody['email_domain']).toBe(EMAIL_SIGN_UP_DOMAIN);
      expect(capturedBody['app_password']).toBe(EMAIL_SIGN_UP_APP_PWORD);

      // now send a fake response to the sign-up request
      await route.fulfill(MOCK_RESPONSE_OK);
    });

    // now fill out the email sign up fields
    await emailSignUpPage.emailAddressInput.fill(EMAIL_SIGN_UP_EMAIL_ADDRESS, { timeout: 5000 });
    await emailSignUpPage.domainSelect.selectOption(EMAIL_SIGN_UP_DOMAIN);

    // the login username/email field should already be filled with your tb accounts login email
    await expect(emailSignUpPage.loginUserNameEmail).not.toBeEditable();
    await expect(emailSignUpPage.loginUserNameEmail).toHaveValue(ACCTS_FXA_EMAIL);

    // fill in app password then click sign up
    await emailSignUpPage.appPassword.fill(EMAIL_SIGN_UP_APP_PWORD, { timeout: 5000 });
    await emailSignUpPage.signUpBtn.click();
  });
});
