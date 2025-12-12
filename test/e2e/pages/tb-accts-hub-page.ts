import { type Page, type Locator } from '@playwright/test';

export class TBAcctsHubPage {
  readonly page: Page;
  readonly dashboardTitle: Locator;
  readonly userMenu: Locator;

  constructor(page: Page) {
    this.page = page;
    this.dashboardTitle = this.page.getByRole('banner').getByRole('link', { name: 'Dashboard' });
    this.userMenu = this.page.locator('.user-menu');
  }
}
