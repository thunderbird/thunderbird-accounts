import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_OIDC_EMAIL, ACCTS_OIDC_PWORD, TIMEOUT_2_SECONDS, TIMEOUT_10_SECONDS, TIMEOUT_30_SECONDS } from '../const/constants';

export class TBAcctsOIDCPage {
  readonly page: Page;
  readonly signInHeaderText: Locator;
  readonly userAvatar: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly signInButton: Locator;
  readonly loginEmailInput: Locator;
  readonly localDevpasswordInput: Locator;
  readonly loginDialogContinueBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.signInHeaderText = this.page.getByText('Sign in to your account');
    this.userAvatar = this.page.getByTestId('avatar-default');
    this.emailInput = this.page.getByTestId('username-input');
    this.passwordInput = this.page.getByTestId('password-input');
    this.signInButton = this.page.getByRole('button', { name: 'Sign in' });
    this.loginEmailInput = this.page.getByLabel('Email');
    this.localDevpasswordInput = this.page.getByLabel('Password');
    this.loginDialogContinueBtn = this.page.getByTitle('Continue');
  }

  /**
   * Sign in to TB Accounts using the provided email and password.
   */
  async signIn() {
    console.log('signing in to TB Accounts');
    expect(ACCTS_OIDC_EMAIL, 'getting ACCTS_OIDC_EMAIL env var').toBeTruthy();
    expect(ACCTS_OIDC_PWORD, 'getting ACCTS_OIDC_PWORD env var').toBeTruthy();
    await expect(this.emailInput).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await this.emailInput.fill(String(ACCTS_OIDC_EMAIL));
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
    await this.passwordInput.fill(String(ACCTS_OIDC_PWORD));
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
    await this.signInButton.click({ force: true });
    await this.page.waitForTimeout(TIMEOUT_10_SECONDS);
  }
}
