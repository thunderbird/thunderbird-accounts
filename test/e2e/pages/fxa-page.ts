import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_FXA_EMAIL, ACCTS_FXA_PWORD } from '../const/constants';

export class FxAPage {
  readonly page: Page;
  readonly emailHeaderText: Locator;
  readonly passwordHeaderText: Locator;
  readonly userAvatar: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly signInButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailHeaderText = this.page.getByRole('heading', { name: 'Enter your email' });
    this.passwordHeaderText = this.page.getByText('Enter your password');
    this.userAvatar = this.page.getByTestId('avatar-default');
    this.emailInput = this.page.getByRole('textbox', { name: 'Enter your email' });
    this.passwordInput = this.page.getByRole('textbox', { name: 'password' });
    this.signInButton = this.page.getByRole('button', { name: 'Sign in' });
  }

  async signIn() {
    // first fxa page is to enter email
    await expect(this.emailHeaderText).toBeVisible({ timeout: 30_000 }); // generous time
    await expect(this.signInButton).toBeVisible();

    // enter email and click sign-in button to continue to password page
    await this.emailInput.fill(ACCTS_FXA_EMAIL);
    await this.signInButton.click();
    await this.page.waitForLoadState('domcontentloaded');

    // now on the second fxa page, enter password and sign-in button
    await expect(this.passwordHeaderText).toBeVisible({ timeout: 30_000 }); // generous time
    await expect(this.userAvatar).toBeVisible({ timeout: 30_000});
    await expect(this.signInButton).toBeVisible();
    await this.passwordInput.fill(ACCTS_FXA_PWORD);
    await this.signInButton.click();
  }
}
