import { type Page, type Locator } from '@playwright/test';

export class TBAcctsHubPage {
  readonly page: Page;
  readonly userAvatar: Locator;

  constructor(page: Page) {
    this.page = page;
    // After sign-in the hub lands on /mail. The banner contains the UserAvatar
    // rendered by UserMenu.vue, which always carries class `.avatar` in both
    // of its render modes (router-link on /mail, button elsewhere). Scoping to
    // the banner keeps this stable if we later land on a different view.
    this.userAvatar = this.page.getByRole('banner').locator('.avatar');
  }
}
