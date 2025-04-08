import { test, expect } from '@playwright/test';
import { SelfServePage } from '../pages/self-serve-page';
import { FxAPage } from '../pages/fxa-page';
import { navigateToAccountsSelfServeHubAndSignIn } from '../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  ACCTS_SELF_SERVE_ACCT_INFO_URL,
 } from '../const/constants';

let selfServePage: SelfServePage;
let fxaPage: FxAPage;

test.beforeEach(async ({ page }) => {
  selfServePage = new SelfServePage(page);
  fxaPage = new FxAPage(page);
  await navigateToAccountsSelfServeHubAndSignIn(page);
  await page.goto(ACCTS_SELF_SERVE_ACCT_INFO_URL);
});

test.describe('self-serve hub accounts info', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('accounts info displayed correctly', async ({ page }) => {
    // check headers and links
    await expect(selfServePage.selfServeAccountInfoHeader).toBeVisible();
    await expect(selfServePage.welcomeBackHeader).toBeVisible();
    await expect(selfServePage.accountInfoLink).toBeEnabled();
    await expect(selfServePage.logoutLink).toBeVisible();

    // check for the delete account text and button
    await expect(selfServePage.deleteAccountHeader).toBeVisible();
    await expect(selfServePage.deleteAcctText).toBeVisible();
    await expect(selfServePage.deleteAcctBtn).toBeEnabled();
  });
});
