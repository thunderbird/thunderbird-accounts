import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_OIDC_EMAIL, ACCTS_OIDC_PWORD, TIMEOUT_30_SECONDS } from '../const/constants';

export class TBAcctsOIDCPage {
  readonly page: Page;
  readonly isMobileAndroid: boolean;
  readonly signInHeaderText: Locator;
  readonly userAvatar: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly signInButton: Locator;
  readonly loginEmailInput: Locator;
  readonly localDevpasswordInput: Locator;
  readonly loginDialogContinueBtn: Locator;

  constructor(page: Page, isMobileAndroid: boolean = false) {
    this.page = page;
    this.isMobileAndroid = isMobileAndroid;
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
      expect(ACCTS_OIDC_EMAIL, 'getting ACCTS_OIDC_EMAIL env var').toBeTruthy();
      username = String(ACCTS_OIDC_EMAIL);
    }
    if (!password) {
      expect(ACCTS_OIDC_PWORD, 'getting ACCTS_OIDC_PWORD env var').toBeTruthy();
      password = String(ACCTS_OIDC_PWORD);
    }

    await expect(this.emailInput).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.emailInput).toBeEditable({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.passwordInput).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.passwordInput).toBeEditable({ timeout: TIMEOUT_30_SECONDS });

    await this.emailInput.fill(username);
    await this.passwordInput.fill(password);

    await expect(this.signInButton).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await expect(this.signInButton).toBeEnabled({ timeout: TIMEOUT_30_SECONDS });

    if (this.isMobileAndroid) {
      // On real BrowserStack Android devices, the sign-in heading or input
      // wrappers can intercept the enabled button's pointer coordinates after
      // the virtual keyboard scrolls the form. Force only this proven case.
      await this.signInButton.click({ force: true });
    } else {
      await this.signInButton.click({ timeout: TIMEOUT_30_SECONDS });
    }
  }
}
