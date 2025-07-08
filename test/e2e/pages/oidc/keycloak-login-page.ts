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
    this.emailHeaderText = this.page.getByRole('heading', { name: ' Sign in to your account' });
    this.emailInput = this.page.getByRole('textbox', { name: 'Username or email' });
    this.passwordInput = this.page.getByRole('textbox', { name: 'Password' });
    this.signInButton = this.page.getByRole('button', { name: 'Sign In' });
  }

  async signIn() {
    // Just one page here:
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
    await expect(this.emailHeaderText).toBeVisible({ timeout: TIMEOUT_60_SECONDS }); // generous time
    await expect(this.signInButton).toBeVisible();

    await this.emailInput.fill(ACCTS_OIDC_EMAIL);
    await this.passwordInput.fill(ACCTS_OIDC_PWORD);
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
    await this.signInButton.click();
  }
}
