import { type Page, type Locator, expect } from '@playwright/test';
import { ACCTS_HUB_URL, ACCTS_SIGN_UP_URL } from '../const/constants';

export class TbAcctsSignUpPage {
  readonly page: Page;
  readonly testPlatform: string;
  readonly stepId: Locator;
  readonly formTitle: Locator;
  readonly formSubtitle: Locator;
  readonly noticeBar: Locator | null;
  readonly errorNoticeBar: Locator | null;
  readonly userNameInput: Locator | null;
  readonly passwordInput: Locator | null;
  readonly passwordConfirmInput: Locator | null;
  readonly fullUsernameInput: Locator | null;
  readonly localeReadonlyInput: Locator;
  readonly zoneInfoInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page, testPlatform: string = 'desktop') {
    this.page = page;
    this.testPlatform = testPlatform;
    this.stepId = this.page.getByTestId('step-id');
    this.formTitle = this.page.getByTestId('title');
    this.formSubtitle = this.page.getByTestId('subtitle');
    this.noticeBar = this.page.getByTestId('notice-bar');
    this.errorNoticeBar = null; // This will need to be retrieved on error pages
    this.userNameInput = this.page.getByTestId('username-input');
    this.passwordInput = this.page.getByTestId('password-input');
    this.passwordConfirmInput = this.page.getByTestId('confirm-password-input');
    this.fullUsernameInput = this.page.getByTestId('full-username-readonly-input');
    this.localeReadonlyInput = this.page.getByTestId('locale-readonly-input');
    this.zoneInfoInput = this.page.getByTestId('zoneinfo-readonly-input');
    this.submitButton = this.page.getByTestId('submit-button');
  }

  /**
   * Clear cookies, this is generally used to remove any authenticated status.
   */
  async clearCookies() {
    await this.page.context().clearCookies();
    // Ensure we're cookieless.
    expect(await this.page.context().cookies()).toEqual([])
  }

  /**
   * Create an allow list entry with the provided email.
   * This will create a temporary test entry, the entry and user will be cleaned up by the server after a period of time.
   * 
   * Note: You must be on a page that has a csrfToken available for this to work.
   */
  async _createAllowListEntry(email: string) {
    try {
      const csrfToken = await this.page.evaluate('window?._page?.csrfToken') as string;

      const response = await this.page.request.fetch(`${ACCTS_HUB_URL}/api/v1/testing/allow-list/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken,
          'Origin': ACCTS_HUB_URL,
          'Referer': this.page.url(),
        },
        data: JSON.stringify({
          email
        })
      });
      return await response.json();
    } catch(ex) {
      // Force a fail here
      expect(true, `There was an error creating the allow list entry: ${ex}.`).toBeFalsy();
    }
  }

  /**
   * Create an allow list entry with the given email or skip it if addEmailToAllowList is false.
   * After clear the cookies (auth) and navigate to the signUp page.
   */
  async setupTest(email: string | null, addEmailToAllowList: boolean = true) {
    if (addEmailToAllowList && email) {
      const response = await this._createAllowListEntry(email);
      await expect(response['success'], `Error creating allow list entry: ${JSON.stringify(response)}`).toBeTruthy();
    }
    await this.clearCookies();
    await this.navigateToPage(email || '');
  }

  /**
   * Navigate to the sign up flow
   * 
   * This requires an email address on the allow list. Make sure to create that ahead of time!
   */
  async navigateToPage(email: string|null) {
    const url = email ? `${ACCTS_SIGN_UP_URL}?email=${encodeURIComponent(email)}` : ACCTS_SIGN_UP_URL;
    await this.page.goto(url);
  }
  
  /**
   * Advances from the confirm plan step to the username step.
   */
  async confirmPlan() {
    await expect.poll(async () => {
      return await this.stepId.inputValue();
    }).toBe('step-confirm-plan');

    await this.submitForm();

    await expect.poll(async () => {
      return await this.stepId.inputValue();
    }).toBe('step-username');
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
  async fillForm(username: string, password?: string, passwordConfirm?: string) {
    await this.confirmPlan();

    await this.userNameInput?.fill(username);
    await this.submitForm();

    if (!password || !passwordConfirm) {
      return;
    }
    
    // we expect to be on the next step; need time for the next page/step to load (will timeout if fails)
    await expect.poll(async () => {
      return await this.stepId.inputValue();
    }).toBe('step-password');

    await this.passwordInput?.fill(password);
    await this.passwordConfirmInput?.fill(passwordConfirm);
  }

  async submitForm() { 
    // when clicking on android it won't click it unless we force it; but force doesn't work on ios
    if (this.testPlatform.includes('android')) { 
      await this.submitButton.click({ force: true, clickCount: 1 });
    } else {
      await this.submitButton.click();
    }
  }
}
