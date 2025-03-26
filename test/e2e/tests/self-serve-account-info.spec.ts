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
  test('displayed correctly with no email set up', async ({ page }) => {
    // headers and link
    await expect(selfServePage.selfServeAccountInfoHeader).toBeVisible();
    await expect(selfServePage.welcomeBackHeader).toBeVisible();
    await expect(selfServePage.accountInfoLink).toBeEnabled();
    await expect(selfServePage.logoutLink).toBeVisible();

    // no email setup text and button
    await expect(selfServePage.emailHeader).toBeVisible();
    await expect(selfServePage.noEmailSetupText).toBeVisible();
    await expect(selfServePage.emailSetupBtn).toBeEnabled();

    // delete account text and button
    await expect(selfServePage.deleteAccountHeader).toBeVisible();
    await expect(selfServePage.deleteAcctText).toBeVisible();
    await expect(selfServePage.deleteAcctBtn).toBeEnabled();
  });
});
