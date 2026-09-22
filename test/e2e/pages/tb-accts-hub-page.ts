import { type Page, type Locator } from '@playwright/test';

export class TBAcctsHubPage {
  readonly page: Page;
  readonly userAvatar: Locator;
  readonly acceptTOSButton: Locator;

  constructor(page: Page) {
    this.page = page;
    // After sign-in the hub lands on /dashboard. The banner contains the UserAvatar
    // rendered by UserMenu.vue, which always carries class `.avatar`. Scoping to
    // the banner keeps this stable if we later land on a different view.
    this.userAvatar = this.page.getByRole('banner').locator('.avatar');
    this.acceptTOSButton = this.page.getByRole('button', { name: 'Accept policies and continue' });
  }
}
