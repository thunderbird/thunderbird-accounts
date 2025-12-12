import { type Page, type Locator, expect } from '@playwright/test';
import { ACCTS_CONTACT_URL, TIMEOUT_2_SECONDS } from '../const/constants';

export class ContactPage {
  readonly page: Page;
  readonly contactHeader: Locator;
  readonly requiredFieldsText: Locator;
  readonly emailInput: Locator;
  readonly nameInput: Locator;
  readonly subjectInput: Locator;
  readonly productSelect: Locator;
  readonly typeSelect: Locator;
  readonly descriptionInput: Locator;
  readonly fileDropzone: Locator;
  readonly fileInput: Locator;
  readonly submitButton: Locator;
  readonly successMessage: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    this.page = page;
    this.contactHeader = this.page.getByRole('heading', { name: 'Submit a request' });
    this.requiredFieldsText = this.page.getByText('Fields marked with an asterisk (*) are required.');
    this.emailInput = this.page.getByTestId('contact-email-input');
    this.nameInput = this.page.getByTestId('contact-name-input');
    this.subjectInput = this.page.getByTestId('contact-Subject-input');
    this.productSelect = this.page.getByTestId('contact-Product-input');
    this.typeSelect = this.page.getByTestId('contact-Type of request-input');
    this.descriptionInput = this.page.getByTestId('contact-Description-input');
    this.fileDropzone = this.page.getByRole('button', { name: 'Upload files' });
    this.fileInput = this.page.locator('input[type="file"]');
    this.submitButton = this.page.getByTestId('contact-submit-btn');
    this.successMessage = this.page.getByText('Your support request has been submitted successfully');
    this.errorMessage = this.page.getByText('Failed to submit contact form. Please try again.');
  }

  async navigateToContactPage() {
    await this.page.goto(ACCTS_CONTACT_URL);
    await this.waitForFormFieldsToLoad();
  }

  async waitForFormFieldsToLoad() {
    // Wait for the select elements to be visible and ready
    await this.productSelect.waitFor({ state: 'visible' });
    await this.typeSelect.waitFor({ state: 'visible' });

    // Give a moment for any async operations to complete
    await this.page.waitForTimeout(500);
  }

  async verifyFormDisplayed() {
    // ensure the form shows as expected
    await expect(this.contactHeader).toBeVisible();
    await expect(this.requiredFieldsText).toBeVisible();
    await expect(this.emailInput).toBeVisible();
    await expect(this.subjectInput).toBeVisible();
    await expect(this.productSelect).toBeVisible();
    await expect(this.typeSelect).toBeVisible();
    await this.typeSelect.scrollIntoViewIfNeeded();
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS)
    await expect(this.descriptionInput).toBeVisible();
    await expect(this.fileDropzone).toBeVisible();
    await expect(this.submitButton).toBeVisible();
  }

  async fillContactForm(email: string, name: string, subject: string, product: string, type: string, description: string) {
    await this.emailInput.fill(email);
    await this.nameInput.fill(name);
    await this.subjectInput.fill(subject);
    await this.productSelect.selectOption(product);
    await this.typeSelect.selectOption(type);
    await this.descriptionInput.fill(description);
  }

  async uploadFile(filePath: string) {
    try {
      await this.fileInput.scrollIntoViewIfNeeded();
      await this.fileInput.setInputFiles(filePath);
      await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
    } catch (error) {
      console.error(`Failed to upload file ${filePath}:`, error);
      throw error;
    }
  }

  async submitForm() {
    await this.submitButton.scrollIntoViewIfNeeded();
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS)
    await this.submitButton.click();
    // scroll back to top to capture any messages after the submit (ie. browserstack video)
    await this.contactHeader.scrollIntoViewIfNeeded();
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS)
  }
}
