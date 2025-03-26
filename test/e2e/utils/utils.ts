// utility functions that may be used by any tests
import { expect, type Page } from '@playwright/test';
import { ACCTS_SELF_SERVE_URL, TIMEOUT_2_SECONDS } from '../const/constants';
import { SelfServePage } from '../pages/self-serve-page';
import { FxAPage } from '../pages/fxa-page';

/**
 * Navigate to and sign into the TB Accounts Self-Serve Hub target environment, using the URL and
 * credentials provided in the .env file. Real FxA stage accounts are used when signing into both
 * the local dev stack and stage environments.
 */
export const navigateToAccountsSelfServeHubAndSignIn = async (page: Page) => {
    console.log(`navigating to the tb accounts self-serve hub (${ACCTS_SELF_SERVE_URL}) and signing in`);
    const selfServePage = new SelfServePage(page);
    const fxaPage = new FxAPage(page);
    await selfServePage.navigateToSelfServeHub();
    await fxaPage.signIn();
    await page.waitForTimeout(TIMEOUT_2_SECONDS);
    await expect(selfServePage.pageHeader).toBeVisible({ timeout: 30_000 }); // generous time
    await expect(selfServePage.logoutLink).toBeVisible();
}
