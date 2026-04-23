import { type Page, type Locator, expect } from '@playwright/test';
import { ACCTS_SIGN_UP_URL, DEFAULT_LOCALE, DEFAULT_TIMEZONE } from '../const/constants';
import { waitForVueApp } from '../utils/utils';

export class TbAcctsSignUpPage {
  readonly page: Page;

  readonly stepId: Locator;
  readonly formTitle: Locator;
  readonly formSubtitle: Locator;
  readonly noticeBar: Locator | null;
  readonly errorNoticeBar: Locator | null;
  readonly userNameInput: Locator | null;
  readonly verificationEmailInput: Locator | null;
  readonly passwordInput: Locator | null;
  readonly passwordConfirmInput: Locator | null;
  readonly fullUsernameInput: Locator | null;
  readonly localeReadonlyInput: Locator;
  readonly zoneInfoInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.stepId = this.page.getByTestId('step-id');
    this.formTitle = this.page.getByTestId('title');
    this.formSubtitle = this.page.getByTestId('subtitle');
    this.noticeBar = this.page.getByTestId('notice-bar');
    this.errorNoticeBar = null; // This will need to be retrieved on error pages
    this.userNameInput = this.page.getByTestId('username-input');
    this.verificationEmailInput = this.page.getByTestId('verification-email-input');
    this.passwordInput = this.page.getByTestId('password-input');
    this.passwordConfirmInput = this.page.getByTestId('confirm-password-input');
    this.fullUsernameInput = this.page.getByTestId('full-username-readonly-input');
    this.localeReadonlyInput = this.page.getByTestId('locale-readonly-input');
    this.zoneInfoInput = this.page.getByTestId('zoneinfo-readonly-input');
    this.submitButton = this.page.getByTestId('submit-button');
  }

  async navigateToPage() {
    await this.page.goto(ACCTS_SIGN_UP_URL);
    await waitForVueApp(this.page);
  }
  
  /**
   * Fills the form out with the given values.
   * 
   * The form will only be filled out if the steps values are filled out.
   * Ex/ Username, Password, and PasswordConfirm are not-undefined, but verificationEmail is undefined.
   * The form will advance up until the email verification step and then exit. 
   * 
   * This relies on the locators being lazy loaded.
   */
  async fillForm(username: string, password?: string, passwordConfirm?: string, verificationEmail?: string) {
    await expect(this.stepId).toHaveValue('step-username');
    await this.userNameInput?.fill(username);
    await this.submitForm();

    if (!password || !passwordConfirm) {
      return;
    }
    
    await expect(this.stepId).toHaveValue('step-password');
    await this.passwordInput?.fill(password);
    await this.passwordConfirmInput?.fill(passwordConfirm);
    await this.submitForm();

    if (!verificationEmail) {
      return;
    }

    await expect(this.stepId).toHaveValue('step-verify-email');
    await this.verificationEmailInput?.fill(verificationEmail);
  }

  async submitForm() {
    await this.submitButton.click();
  }
}
