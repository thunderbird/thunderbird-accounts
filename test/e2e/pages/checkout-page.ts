import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_CHECKOUT_URL } from '../const/constants';

export class CheckoutPage {
  readonly page: Page;
  readonly checkoutHeader: Locator;
  readonly pricingGrid: Locator;

  constructor(page: Page) {
    this.page = page;
    this.checkoutHeader = this.page.getByRole('heading', { name: 'Self Serve - Subscription' });
    this.pricingGrid = this.page.getByTestId('pricing-grid');
  }

  async navigateToCheckoutPage() {
    await this.page.goto(ACCTS_CHECKOUT_URL);
  }
}
