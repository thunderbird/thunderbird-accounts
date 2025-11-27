import path from 'path';
import { test, expect } from '@playwright/test';
import { ContactPage } from '../pages/contact-page';
import { ensureWeAreSignedIn } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  ACCTS_OIDC_EMAIL,
  ACCTS_RECOVERY_EMAIL,
  TIMEOUT_2_SECONDS,
  TIMEOUT_5_SECONDS,
  TIMEOUT_30_SECONDS,
} from '../const/constants';

let contactPage: ContactPage;

const MOCK_PRODUCT_VALUE = 'pro_service_thundermail';
const MOCK_TYPE_VALUE = 'pro_technical';
const TEST_NAME = 'Automated E2E Test';
const TEST_SUBJECT = 'Test Subject';
const TEST_DESC = 'Issue created by automated E2E test'

const verifyFormPostData = async (postData: string | null) => {
  // verify the data captured in the submit form post is as expected
  expect(postData).toContain('email');
  expect(postData).toContain(ACCTS_OIDC_EMAIL);
  expect(postData).toContain('name');
  expect(postData).toContain(TEST_NAME);
  expect(postData).toContain('subject');
  expect(postData).toContain(TEST_SUBJECT);
  expect(postData).toContain('Product');
  expect(postData).toContain(MOCK_PRODUCT_VALUE);
  expect(postData).toContain('type');
  expect(postData).toContain(MOCK_TYPE_VALUE);
  expect(postData).toContain('description');
  expect(postData).toContain(TEST_DESC);
};


test.beforeEach(async ({ page }) => {
  contactPage = new ContactPage(page);

  // mock the /contact/fields endpoint to return predictable values for the form
  await page.route('*/**/contact/fields', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        ticket_fields: [
          {
              "id": 1001,
              "title": "Subject",
              "description": "",
              "required": true,
              "type": "subject"
          },
          {
              "id": 2001,
              "title": "Description",
              "description": "Please shared detailed information about your issue or request.",
              "required": true,
              "type": "description"
          },
          {
              "id": 3001,
              "title": "Product",
              "description": "Which service do you need help with?",
              "required": true,
              "type": "tagger",
              "custom_field_options": [
                  {
                      "id": 4001,
                      "name": "Account Hub",
                      "value": "pro_service_account_hub"
                  },
                  {
                      "id": 5001,
                      "name": "Appointment",
                      "value": "pro_service_appointment"
                  },
                  {
                      "id": 6001,
                      "name": "Send",
                      "value": "pro_service_send"
                  },
                  {
                      "id": 7001,
                      "name": "Thundermail",
                      "value": MOCK_PRODUCT_VALUE
                  }
              ]
          },
          {
              "id": 8001,
              "title": "Type of request",
              "description": "Let us know what we can help you with today.",
              "required": true,
              "type": "tagger",
              "custom_field_options": [
                  {
                      "id": 9001,
                      "name": "Accounts & Login \t",
                      "value": "pro_accounts"
                  },
                  {
                      "id": 10001,
                      "name": "Provide Feedback or Request Features",
                      "value": "pro_feedback"
                  },
                  {
                      "id": 11001,
                      "name": "Payments & Billing \t",
                      "value": "pro_bililng"
                  },
                  {
                      "id": 12001,
                      "name": "Technical",
                      "value": MOCK_TYPE_VALUE
                  },
                  {
                      "id": 13001,
                      "name": " Something else",
                      "value": "pro_not_listed"
                  }
              ]
          }
        ]
      })
    });
  });

  // we should be signed into TB Accounts already via our auth setup but check in case session expired
  await ensureWeAreSignedIn(page);
});

test.describe('contact support form', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE, PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY],
}, () => {
  test('contact form displayed correctly when signed in', async ({ page }) => {
    // go to the contact / submit an issue form and wait for it to load
    await contactPage.navigateToContactPage();

    // we are already signed into TB Accounts; ensure the form shows as expected when signed in
    await contactPage.verifyFormDisplayed();

    // since we're signed in, email field should be pre-filled with the user's recovery email
    await expect(contactPage.emailInput).toHaveValue(ACCTS_RECOVERY_EMAIL);
  });
  
  test('contact form displayed correctly when not signed in', async ({ page }) => {
    // clear authentication state for this test
    await page.context().clearCookies();
    await page.reload();
    await page.waitForTimeout(TIMEOUT_5_SECONDS);
    await contactPage.navigateToContactPage();

    // check that the contact form is visible
    await contactPage.verifyFormDisplayed();

    // not signed in, so check that email is not pre-filled
    await expect(contactPage.emailInput).toBeEmpty();
    await expect(contactPage.nameInput).toBeEmpty();
  });

  test('able to submit contact form successfully', async ({ page }) => {
    // go to the contact / submit an issue form and wait for it to load
    await contactPage.navigateToContactPage();

    // capture the POST /contact/submit and mock the response
    await page.route('*/**/contact/submit', async (route, request) => {
      const postData = request.postData();
      expect(postData).not.toBeNull();

      const contentType = request.headers()['content-type'];
      expect(contentType).toContain('multipart/form-data');

      // verify that the posted FormData contains the expected fields
      await verifyFormPostData(postData);

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
      TEST_NAME,
      TEST_SUBJECT,
      MOCK_PRODUCT_VALUE,
      MOCK_TYPE_VALUE,
      TEST_DESC,
    );

    // submit the form, scroll back to top to capture message after submit (for screenshot if test fails)
    await contactPage.submitForm();

    // check for success message
    await expect(contactPage.successMessage).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
  });

  test('form validation prevents submission', async ({ page }) => {
    // go to the contact / submit an issue form and wait for it to load
    await contactPage.navigateToContactPage();
    await contactPage.submitForm();
    await expect(contactPage.successMessage).not.toBeVisible();
  });

  test('error handling works correctly', async ({ page }) => {
    // go to the contact / submit an issue form and wait for it to load
    await contactPage.navigateToContactPage();
    // capture the POST /contact/submit and mock an error response
    await page.route('*/**/contact/submit', async (route, _request) => {
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
      TEST_NAME,
      TEST_SUBJECT,
      MOCK_PRODUCT_VALUE,
      MOCK_TYPE_VALUE,
      TEST_DESC,
    );

    // submit the form
    await contactPage.submitForm();

    // check for error message
    await expect(contactPage.errorMessage).toBeVisible();
  });

  test('able to submit contact form with attachments', async ({ page }) => {
    // go to the contact / submit an issue form and wait for it to load
    await contactPage.navigateToContactPage();
    // capture the POST /contact/submit and mock the response
    await page.route('*/**/contact/submit', async (route, request) => {
      const postData = request.postData();
      expect(postData).not.toBeNull();

      const contentType = request.headers()['content-type'];
      expect(contentType).toContain('multipart/form-data');

      // verify that the posted FormData contains the expected fields
      await verifyFormPostData(postData);
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
      TEST_NAME,
      `${TEST_SUBJECT} with File Attachment`,
      MOCK_PRODUCT_VALUE,
      MOCK_TYPE_VALUE,
      `${TEST_DESC} with File Attachment`,
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
    // go to the contact / submit an issue form and wait for it to load
    await contactPage.navigateToContactPage();
    // Upload a test file
    const testFilePath = path.join(__dirname, '../test-files/test-attachment.txt');
    await contactPage.uploadFile(testFilePath);

    // Check that the file appears in the attachment list
    await expect(page.getByText('test-attachment.txt')).toBeVisible();
    await expect(page.getByText('1 file(s) selected. Drag & drop more files here, or click to upload')).toBeVisible();

    // Check that the remove button is present
    const removeButton = page.locator('.remove-attachment-btn').first();
    await expect(removeButton).toBeVisible({ timeout: TIMEOUT_30_SECONDS });

    // Remove the attachment
    await removeButton.click();
    await page.waitForTimeout(TIMEOUT_2_SECONDS);

    // Check that the file is removed from the list
    await expect(page.getByText('test-attachment.txt')).not.toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await expect(page.getByText('Drag & drop files here, or click to upload')).toBeVisible();
  });
});
