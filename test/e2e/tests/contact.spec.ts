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
      // verify the captured request body is as expected
      const capturedBody = await request.postDataJSON();
      expect(capturedBody['email']).toBe(ACCTS_FXA_EMAIL);
      expect(capturedBody['subject']).toBe('Test Subject');
      expect(capturedBody['product']).toBe('thunderbird_assist');
      expect(capturedBody['type']).toBe('technical');
      expect(capturedBody['description']).toBe('Test description for contact form');

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

  test('able to upload file attachment', async ({ page }) => {
    // capture the POST /contact/attach_file and mock the response
    await page.route('*/**/contact/attach_file', async (route, request) => {
      // send a fake response to the file upload request
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          upload_token: 'fake-upload-token-123',
          filename: 'test-attachment.txt'
        }),
      });
    });

    // create a temporary test file
    const testFilePath = './test-files/test-attachment.txt';

    // upload the file
    await contactPage.uploadFile(testFilePath);

    // check that the file appears in the attachment list
    await expect(page.getByText('test-attachment.txt')).toBeVisible();
  });

  test('form validation works correctly', async ({ page }) => {
    // try to submit empty form
    await contactPage.submitForm();

    // check that form validation prevents submission
    // The form should not submit and no success message should appear
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