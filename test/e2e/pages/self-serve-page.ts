import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_SELF_SERVE_URL } from '../const/constants';

export class SelfServePage {
  readonly page: Page;
  readonly pageHeader: Locator;
  readonly selfServeHeader: Locator;
  readonly logoutLink: Locator;

  constructor(page: Page) {
    this.page = page;
    this.pageHeader = this.page.getByRole('heading', { name: 'Accounts Hub'});
    this.selfServeHeader = this.page.getByRole('heading', { name: 'Self Serve - Connection Information'});
    this.logoutLink = this.page.getByRole('link', { name: 'Logout'});
  }

  async navigateToSelfServeHub() {
    await this.page.goto(ACCTS_SELF_SERVE_URL);
    await this.page.waitForLoadState('domcontentloaded');
  }

  async verifySelfServeHubDisplayed() {
    // verify self-serve hub is displayed
    await this.page.waitForLoadState('domcontentloaded');
    await expect(this.pageHeader).toBeVisible({ timeout: 30_000 }); // generous time
    await expect(this.selfServeHeader).toBeVisible();
    await expect(this.logoutLink).toBeVisible();
  }
}
