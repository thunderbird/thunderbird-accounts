import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_OIDC_EMAIL, ACCTS_OIDC_PWORD, TIMEOUT_2_SECONDS, TIMEOUT_60_SECONDS } from '../../const/constants';

export class OIDCKeycloakPage {
  readonly page: Page;
  readonly emailHeaderText: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly signInButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailHeaderText = this.page.getByTestId('header-text');
    this.emailInput = this.page.getByTestId('username-input');
    this.passwordInput = this.page.getByTestId('password-input');
    this.signInButton = this.page.getByTestId('submit-btn');
  }

  async signIn() {
    // Just one page here:
    await expect(this.emailHeaderText).toBeVisible();
    await expect(this.signInButton).toBeVisible();

    await this.emailInput.fill(ACCTS_OIDC_EMAIL);
    await this.passwordInput.fill(ACCTS_OIDC_PWORD);
    await this.signInButton.click();
    console.debug('[oidc] signIn completed');
  }
}
