// utility functions that may be used by any tests
import { expect, type Page } from '@playwright/test';
import { ACCTS_SELF_SERVE_CONNECTION_INFO_URL, ACCTS_SELF_SERVE_URL, TIMEOUT_2_SECONDS, TIMEOUT_60_SECONDS } from '../const/constants';
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

    // if we are already signed in, the connection-info will be displayed, then we can just skip FxA
    const visible = await selfServePage.pageHeader.isVisible();
    if (visible && page.url() == ACCTS_SELF_SERVE_CONNECTION_INFO_URL) {
        console.log('we are already signed into accounts self-serve hub');
    } else {
        await fxaPage.signIn();
        await page.waitForTimeout(TIMEOUT_2_SECONDS);
    }

    await expect(selfServePage.pageHeader).toBeVisible({ timeout: TIMEOUT_60_SECONDS }); // generous time
    await expect(selfServePage.logoutLink).toBeVisible();
}
