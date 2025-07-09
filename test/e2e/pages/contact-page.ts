import { type Page, type Locator } from '@playwright/test';
import { ACCTS_CONTACT_URL } from '../const/constants';

export class ContactPage {
  readonly page: Page;
  readonly contactHeader: Locator;
  readonly requiredFieldsText: Locator;
  readonly emailInput: Locator;
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
    this.subjectInput = this.page.getByTestId('contact-subject-input');
    this.productSelect = this.page.getByTestId('contact-product-input');
    this.typeSelect = this.page.getByTestId('contact-type-input');
    this.descriptionInput = this.page.getByTestId('contact-description-input');
    this.fileDropzone = this.page.getByRole('button', { name: 'Upload files' });
    this.fileInput = this.page.locator('input[type="file"]');
    this.submitButton = this.page.getByTestId('contact-submit-btn');
    this.successMessage = this.page.getByText('Your support request has been submitted successfully');
    this.errorMessage = this.page.getByText('Failed to submit contact form');
  }

  async navigateToContactPage() {
    await this.page.goto(ACCTS_CONTACT_URL);
  }

  async waitForFormFieldsToLoad() {
    // Wait for the select elements to be visible and ready
    await this.productSelect.waitFor({ state: 'visible' });
    await this.typeSelect.waitFor({ state: 'visible' });

    // Give a moment for any async operations to complete
    await this.page.waitForTimeout(500);
  }

  async fillContactForm(email: string, subject: string, product: string, type: string, description: string) {
    await this.emailInput.fill(email);
    await this.subjectInput.fill(subject);
    await this.productSelect.selectOption(product);
    await this.typeSelect.selectOption(type);
    await this.descriptionInput.fill(description);
  }

  async uploadFile(filePath: string) {
    try {
      await this.fileInput.setInputFiles(filePath);
    } catch (error) {
      console.error(`Failed to upload file ${filePath}:`, error);
      throw error;
    }
  }

  async submitForm() {
    await this.submitButton.click();
  }
} 