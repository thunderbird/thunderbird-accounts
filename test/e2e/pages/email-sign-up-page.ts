import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_EMAIL_SIGN_UP_URL } from '../const/constants';

export class EmailSignUpPage {
  readonly page: Page;
  readonly emailAddressInput: Locator;
  readonly domainSelect: Locator;
  readonly loginUserNameEmail: Locator;
  readonly appPassword: Locator;
  readonly signUpBtn: Locator;
  readonly cancelBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailAddressInput = this.page.getByTestId('sign-up-email-address-input');
    this.domainSelect = this.page.getByTestId('sign-up-domain-input');
    this.loginUserNameEmail = this.page.getByTestId('sign-up-login-username-input');
    this.appPassword = this.page.getByTestId('sign-up-app-password-input');
    this.signUpBtn = this.page.getByRole('button', { 'name': 'Sign Up' });
    this.cancelBtn = this.page.getByRole('button', { 'name': 'Cancel' });
  }

  async navigateToEmailSignUpPage() {
    await this.page.goto(ACCTS_EMAIL_SIGN_UP_URL);
  }
}
