import { type Page, type Locator } from '@playwright/test';
import { ACCTS_SIGN_UP_URL, DEFAULT_LOCALE, DEFAULT_TIMEZONE } from '../const/constants';
import { waitForVueApp } from '../utils/utils';

export class TbAcctsSignUpPage {
  readonly page: Page;

  readonly formTitle: Locator;
  readonly noticeBar: Locator | null;
  readonly errorNoticeBar: Locator | null;
  readonly userNameInput: Locator;
  readonly recoveryEmailInput: Locator;
  readonly passwordInput: Locator;
  readonly passwordConfirmInput: Locator;
  readonly fullUsernameInput: Locator;
  readonly localeReadonlyInput: Locator;
  readonly zoneInfoInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.formTitle = this.page.getByTestId('title');
    this.noticeBar = this.page.getByTestId('notice-bar');
    this.errorNoticeBar = null; // This will need to be retrieved on error pages
    this.userNameInput = this.page.getByTestId('username-input');
    this.recoveryEmailInput = this.page.getByTestId('recovery-email-input');
    this.passwordInput = this.page.getByTestId('password-input');
    this.passwordConfirmInput = this.page.getByTestId('password-confirm-input');
    this.fullUsernameInput = this.page.getByTestId('full-username-readonly-input');
    this.localeReadonlyInput = this.page.getByTestId('locale-readonly-input');
    this.zoneInfoInput = this.page.getByTestId('zoneinfo-readonly-input');
    this.submitButton = this.page.getByTestId('submit-button');
  }

  async navigateToPage() {
    await this.page.goto(ACCTS_SIGN_UP_URL);
    await waitForVueApp(this.page);
  }
  
  async fillForm(username: string, recoveryEmail: string, password: string, passwordConfirm: string) {
    await this.userNameInput.fill(username);
    await this.recoveryEmailInput.fill(recoveryEmail);
    await this.passwordInput.fill(password);
    await this.passwordConfirmInput.fill(passwordConfirm);
  }

  async submitForm() {
    await this.submitButton.click();
  }
}
