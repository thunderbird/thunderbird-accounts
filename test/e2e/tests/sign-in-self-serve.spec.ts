import { test, expect } from '@playwright/test';
import { SelfServePage } from '../pages/self-serve-page';
import { FxAPage } from '../pages/fxa-page';
import { PLAYWRIGHT_TAG_E2E_SUITE } from '../const/constants';

let selfServePage: SelfServePage;
let fxaPage: FxAPage;

test.beforeEach(async ({ page }) => {
  selfServePage = new SelfServePage(page);
  fxaPage = new FxAPage(page);
});

test.describe('sign-in to tb accounts self-serve hub', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('able to sign-in', async ({ page }) => {
    await selfServePage.navigateToSelfServeHub();
    await fxaPage.signIn();
    await selfServePage.verifySelfServeHubDisplayed();
  });
});
