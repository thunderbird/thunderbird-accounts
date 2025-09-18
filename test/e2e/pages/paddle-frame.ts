import { type Page, type Frame, type Locator } from '@playwright/test';

export class PaddleFrame {
  readonly page: Page;
  readonly frame: Frame;
  readonly modal: Locator;
  readonly emailField: Locator;
  readonly countryField: Locator;
  readonly postalCodeField: Locator;
  readonly continueButton: Locator;
  readonly consentCheckBox: Locator;
  readonly cardNumberField: Locator;
  readonly cardNameField: Locator;
  readonly cardExpiryField: Locator;
  readonly cardVerificationField: Locator;
  readonly finalCheckoutButton: Locator;
  readonly checkoutErrText: Locator;

  constructor(page: Page) {
    this.page = page;
    this.frame = this.page.frame({ name: 'paddle_frame' })!; // non-null assertion
    this.modal = this.frame.locator('body');
    this.emailField = this.modal.getByTestId('authenticationEmailInput');
    this.countryField = this.modal.getByTestId('countriesSelect');
    this.postalCodeField = this.modal.getByTestId('postcodeInput');
    this.continueButton = this.modal.getByTestId('combinedAuthenticationLocationFormSubmitButton');
    this.consentCheckBox = this.modal.getByTestId('us-compliance-section-overlay').locator('label');
    this.cardNumberField = this.modal.getByTestId('cardNumberInput');
    this.cardNameField = this.modal.getByTestId('cardholderNameInput');
    this.cardExpiryField = this.modal.getByTestId('expiryDateField');
    this.cardVerificationField = this.modal.getByTestId('cardVerificationValueInput');
    this.finalCheckoutButton = this.modal.getByTestId('cardPaymentFormSubmitButton');
    this.checkoutErrText = this.modal.getByText('We are unable to take payment at this time. Please try again, or use a different payment method.');
  }
}
