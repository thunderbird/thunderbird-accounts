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
  async signIn(username: string | null = null, password: string | null = null) {
    if (!username) {
      console.log('sign in NO USERNAME!', username);
      expect(ACCTS_OIDC_EMAIL, 'getting ACCTS_OIDC_EMAIL env var').toBeTruthy();
      username = String(ACCTS_OIDC_EMAIL);
    }
    if (!password) {
      console.log('sign in NO PASSWORD!', password);
      expect(ACCTS_OIDC_PWORD, 'getting ACCTS_OIDC_PWORD env var').toBeTruthy();
      password = String(ACCTS_OIDC_PWORD);
    }

    await expect(this.emailInput).toBeVisible({ timeout: TIMEOUT_10_SECONDS });
    await this.emailInput.fill(username);
    await this.passwordInput.fill(password);
    await this.signInButton.click({ force: true });
    await this.page.waitForTimeout(TIMEOUT_10_SECONDS);
  }
}
