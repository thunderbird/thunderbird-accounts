import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_OIDC_EMAIL, ACCTS_OIDC_PWORD, TIMEOUT_1_SECOND, TIMEOUT_30_SECONDS } from '../const/constants';

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
      // BrowserStack Android devices can leave the enabled sign-in button behind an input wrapper
      // after the virtual keyboard scrolls the form. They can also report the button as ready before
      // Keycloak's controlled input state has settled, causing an immediate click to submit neither
      // credential. This short, Android-only pause and force-click are proven workarounds for those
      // device-specific races; the authentication-state poll handles the result after submission.
      await this.page.waitForTimeout(TIMEOUT_1_SECOND);
      await this.signInButton.click({ force: true });
    } else {
      // Desktop and iOS use Playwright's normal actionability checks so an overlay or unstable
      // button produces a useful failure instead of an artificial click.
      await this.signInButton.click({ timeout: TIMEOUT_30_SECONDS });
    }
  }
}
