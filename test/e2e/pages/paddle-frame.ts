import { type Page, type Frame, type Locator } from '@playwright/test';

export class PaddleFrame {
  readonly page: Page;
  readonly frame: Frame;
  readonly modal: Locator;
  readonly emailField: Locator;
  readonly postalCodeField: Locator;
  readonly continueButton: Locator;
  readonly cardNumberField: Locator;
  readonly cardNameField: Locator;
  readonly cardExpiryField: Locator;
  readonly cardVerificationField: Locator;
  readonly finalCheckoutButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.frame = this.page.frame({ name: 'paddle_frame' })!; // non-null assertion
    this.modal = this.frame.locator('body');
    this.emailField = this.modal.getByTestId('authenticationEmailInput');
    this.postalCodeField = this.modal.getByTestId('postcodeInput');
    this.continueButton = this.modal.getByTestId('combinedAuthenticationLocationFormSubmitButton');
    this.cardNumberField = this.modal.getByTestId('cardNumberInput');
    this.cardNameField = this.modal.getByTestId('cardholderNameInput');
    this.cardExpiryField = this.modal.getByTestId('expiryDateField');
    this.cardVerificationField = this.modal.getByTestId('cardVerificationValueInput');
    this.finalCheckoutButton = this.modal.getByTestId('cardPaymentFormSubmitButton');
  }
}
