import { test, expect } from '@playwright/test';
import { SelfServePage } from '../pages/self-serve-page';
import { FxAPage } from '../pages/fxa-page';
import { PLAYWRIGHT_TAG_E2E_SUITE, TIMEOUT_2_SECONDS } from '../const/constants';
import exp from 'constants';

let selfServePage: SelfServePage;
let fxaPage: FxAPage;

test.beforeEach(async ({ page }) => {
  selfServePage = new SelfServePage(page);
  fxaPage = new FxAPage(page);
});

test.describe('tb accounts self-serve hub', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('able to sign-in and sign-out', async ({ page }) => {
    await selfServePage.navigateToSelfServeHub();
    await fxaPage.signIn();
    await expect(selfServePage.pageHeader).toBeVisible({ timeout: 30_000 }); // generous time
    await expect(selfServePage.selfServeHeader).toBeVisible();
    await expect(selfServePage.welcomeBackHeader).toBeVisible();
    await expect(selfServePage.logoutLink).toBeVisible();

    // wait a couple of seconds then sign out
    await page.waitForTimeout(TIMEOUT_2_SECONDS);
    await selfServePage.logoutLink.click();
    await page.waitForTimeout(TIMEOUT_2_SECONDS);
    await expect(selfServePage.selfServeHeader).not.toBeVisible();
    await expect(selfServePage.welcomeBackHeader).not.toBeVisible();
  });
});
