import { type Page, type Locator } from '@playwright/test';
import { ACCTS_SELF_SERVE_URL, ACCTS_FXA_EMAIL } from '../const/constants';

export class SelfServePage {
  readonly page: Page;
  readonly pageHeader: Locator;
  readonly selfServeHeader: Locator;
  readonly welcomeBackHeader: Locator;
  readonly logoutLink: Locator;
  readonly userDisplayName: string;

  constructor(page: Page) {
    this.page = page;
    this.pageHeader = this.page.getByRole('heading', { name: 'Accounts Hub'});
    this.selfServeHeader = this.page.getByRole('heading', { name: 'Self Serve - Connection Information'});
    this.userDisplayName = ACCTS_FXA_EMAIL.split('@')[0];
    this.welcomeBackHeader = this.page.getByText(`Welcome back ${this.userDisplayName}.`, { exact: true });
    this.logoutLink = this.page.getByRole('link', { name: 'Logout'});
  }

  async navigateToSelfServeHub() {
    await this.page.goto(ACCTS_SELF_SERVE_URL);
  }
}
