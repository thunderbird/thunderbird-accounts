import path from 'path';
import { test, expect } from '@playwright/test';
import { ContactPage } from '../pages/contact-page';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  ACCTS_OIDC_EMAIL,
} from '../const/constants';

let contactPage: ContactPage;

// Mock values for the contact form fields
const MOCK_PRODUCT_VALUE = 'appointment';
const MOCK_TYPE_VALUE = 'technical';

test.beforeEach(async ({ page }) => {
  contactPage = new ContactPage(page);

  // Mock the /contact/fields endpoint to return predictable values
  await page.route('*/**/contact/fields', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        ticket_fields: {
          'Product': {
            id: 123456,
            title: 'Product',
            custom_field_options: [
              { id: 1, name: 'Thunderbird Appointment', value: MOCK_PRODUCT_VALUE },
            ]
          },
          'Type of request': {
            id: 789012,
            title: 'Type of request',
            custom_field_options: [
              { id: 3, name: 'Technical Support', value: MOCK_TYPE_VALUE },
            ]
          }
        }
      })
    });
  });

  // we are already signed into accounts via our auth.setup
  await contactPage.navigateToContactPage();

  // Wait for the form to be ready
  await contactPage.waitForFormFieldsToLoad();
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
    await expect(contactPage.emailInput).toHaveValue(ACCTS_OIDC_EMAIL);
  });

  test('contact form displayed correctly without logging in', async ({ page }) => {
    // clear authentication state for this test
    await page.context().clearCookies();

    await contactPage.navigateToContactPage();
    await contactPage.waitForFormFieldsToLoad();

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

    // check that email is not pre-filled with user's email
    expect(contactPage.emailInput).toBeEmpty;
  });

  test('able to submit contact form successfully', async ({ page }) => {
    // capture the POST /contact/submit and mock the response
    await page.route('*/**/contact/submit', async (route, request) => {
      const postData = request.postData();
      expect(postData).not.toBeNull();

      const contentType = request.headers()['content-type'];
      expect(contentType).toContain('multipart/form-data');

      // Verify that the FormData contains the expected fields
      expect(postData).toContain('email');
      expect(postData).toContain('subject');
      expect(postData).toContain('product');
      expect(postData).toContain('type');
      expect(postData).toContain('description');

      // send a fake response to the contact submit request
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    // fill out the contact form
    await contactPage.fillContactForm(
      ACCTS_OIDC_EMAIL,
      'Test Subject',
      MOCK_PRODUCT_VALUE,
      MOCK_TYPE_VALUE,
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
        body: JSON.stringify({ 
          success: false,
          error: 'Failed to submit contact form. Please try again.'
        }),
      });
    });

    // fill out the contact form
    await contactPage.fillContactForm(
      ACCTS_OIDC_EMAIL,
      'Test Subject',
      MOCK_PRODUCT_VALUE,
      MOCK_TYPE_VALUE,
      'Test description for contact form'
    );

    // submit the form
    await contactPage.submitForm();

    // check for error message
    await expect(contactPage.errorMessage).toBeVisible();
  });

  test('able to submit contact form with attachments', async ({ page }) => {
    // capture the POST /contact/submit and mock the response
    await page.route('*/**/contact/submit', async (route, request) => {
      const postData = request.postData();
      expect(postData).not.toBeNull();

      const contentType = request.headers()['content-type'];
      expect(contentType).toContain('multipart/form-data');

      // Verify that the FormData contains the expected fields and file
      // For multipart/form-data, we need to check the raw post data
      expect(postData).toContain('email');
      expect(postData).toContain('subject');
      expect(postData).toContain('product');
      expect(postData).toContain('type');
      expect(postData).toContain('description');
      expect(postData).toContain('attachments');
      expect(postData).toContain('test-attachment.txt');

      // send a fake response to the contact submit request
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true }),
      });
    });

    // fill out the contact form
    await contactPage.fillContactForm(
      ACCTS_OIDC_EMAIL,
      'Test Subject with Attachment',
      MOCK_PRODUCT_VALUE,
      MOCK_TYPE_VALUE,
      'Test description with file attachment'
    );

    // upload a test file
    const testFilePath = path.join(__dirname, '../test-files/test-attachment.txt');
    await contactPage.uploadFile(testFilePath);

    // submit the form
    await contactPage.submitForm();

    // check for success message
    await expect(contactPage.successMessage).toBeVisible();
  });

  test('file upload UI works correctly', async ({ page }) => {
    // Upload a test file
    const testFilePath = path.join(__dirname, '../test-files/test-attachment.txt');
    await contactPage.uploadFile(testFilePath);

    // Check that the file appears in the attachment list
    await expect(page.getByText('test-attachment.txt')).toBeVisible();
    await expect(page.getByText('1 file(s) selected. Drag & drop more files here, or click to upload')).toBeVisible();

    // Check that the remove button is present
    const removeButton = page.locator('.remove-attachment-btn').first();
    await expect(removeButton).toBeVisible();

    // Remove the attachment
    await removeButton.click();

    // Check that the file is removed from the list
    await expect(page.getByText('test-attachment.txt')).not.toBeVisible();
    await expect(page.getByText('Drag & drop files here, or click to upload')).toBeVisible();
  });
}); 