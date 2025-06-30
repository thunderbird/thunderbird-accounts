import { test, expect } from '@playwright/test';
import { ContactPage } from '../pages/contact-page';
import { FxAPage } from '../pages/fxa-page';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  ACCTS_FXA_EMAIL,
} from '../const/constants';

let contactPage: ContactPage;
let fxaPage: FxAPage;

test.beforeEach(async ({ page }) => {
  contactPage = new ContactPage(page);
  fxaPage = new FxAPage(page);
  // we are already signed into accounts via our auth.setup
  await contactPage.navigateToContactPage();
});

test.describe('contact support form', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('contact form displayed correctly', async ({ page }) => {
    // check that the contact form is visible
    await expect(contactPage.contactHeader).toBeVisible();
    await expect(contactPage.requiredFieldsText).toBeVisible();
    await expect(contactPage.emailInput).toBeVisible();
    await expect(contactPage.subjectInput).toBeVisible();
    await expect(contactPage.productSelect).toBeVisible();
    await expect(contactPage.typeSelect).toBeVisible();
    await expect(contactPage.descriptionInput).toBeVisible();
    await expect(contactPage.fileDropzone).toBeVisible();
    await expect(contactPage.submitButton).toBeVisible();

    // check that email is pre-filled with user's email
    await expect(contactPage.emailInput).toHaveValue(ACCTS_FXA_EMAIL);
  });

  test('able to submit contact form successfully', async ({ page }) => {
    // capture the POST /contact/submit and mock the response
    await page.route('*/**/contact/submit', async (route, request) => {
      const postData = request.postData();
      expect(postData).not.toBeNull();

      const contentType = request.headers()['content-type'];
      expect(contentType).toContain('multipart/form-data');

      // send a fake response to the contact submit request
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    // fill out the contact form
    await contactPage.fillContactForm(
      ACCTS_FXA_EMAIL,
      'Test Subject',
      'thunderbird_assist',
      'technical',
      'Test description for contact form'
    );

    // submit the form
    await contactPage.submitForm();

    // check for success message
    await expect(contactPage.successMessage).toBeVisible();
  });

  test('form validation prevents submission', async ({ page }) => {
    await contactPage.submitForm();
    await expect(contactPage.successMessage).not.toBeVisible();
  });

  test('error handling works correctly', async ({ page }) => {
    // capture the POST /contact/submit and mock an error response
    await page.route('*/**/contact/submit', async (route, request) => {
      // send an error response
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ success: false }),
      });
    });

    // fill out the contact form
    await contactPage.fillContactForm(
      ACCTS_FXA_EMAIL,
      'Test Subject',
      'thunderbird_assist',
      'technical',
      'Test description for contact form'
    );

    // submit the form
    await contactPage.submitForm();

    // check for error message
    await expect(contactPage.errorMessage).toBeVisible();
  });
}); 