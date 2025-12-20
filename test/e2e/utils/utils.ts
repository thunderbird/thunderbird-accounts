// utility functions that may be used by any tests
import { TBAcctsOIDCPage } from "../pages/tb-accts-oidc-page";
import { TBAcctsHubPage } from "../pages/tb-accts-hub-page";
import { expect, type Page } from '@playwright/test';
import path from 'path';

import {
    ACCTS_TARGET_ENV,
    ACCTS_HUB_URL,
    TIMEOUT_5_SECONDS,
    TIMEOUT_30_SECONDS,
} from "../const/constants";

const authFile = path.join(__dirname, '../test-results/.auth/user.json');
  

/**
 * Navigate to TB Accounts Hub (at the ACCTS_HUB_URL in the test/e2e/.env file). If already signed
 * in then just exit; otherwise if not currently signed in then sign in using the credentials
 * provided in the .env file. When singing in to the local stack we use a local sign in page and
 * aren't redirected to TB Accounts OIDC to sign in.
 */
export const navigateToAccountsHubAndSignIn = async (page: Page) => {
    console.log(`navigating to accounts hub ${ACCTS_TARGET_ENV} (${ACCTS_HUB_URL})`);   
    const tbAcctsSignInPage = new TBAcctsOIDCPage(page);
    const tbAcctsHubPage = new TBAcctsHubPage(page);
    await page.goto(`${ACCTS_HUB_URL}`);
    await page.waitForTimeout(TIMEOUT_5_SECONDS);

    // if we are already signed in then we can skip this
    if (await tbAcctsSignInPage.signInHeaderText.isVisible() && await tbAcctsSignInPage.signInButton.isEnabled()) {
        await tbAcctsSignInPage.signIn();
    }

    // now that we're signed into the accounts hub give it time to load
    await page.waitForTimeout(TIMEOUT_5_SECONDS);
    await expect(tbAcctsHubPage.dashboardTitle).toBeVisible({ timeout: TIMEOUT_30_SECONDS });
    await expect(tbAcctsHubPage.userMenu).toBeVisible();
}

/**
 * Ensure we are already signed into TB Accounts, and if we aren't then sign in. Also set
 * save the storage and auth state. This is meant to be used at the start of each test to ensure
 * we are signed in; the auth.desktop.setup already signs us in before all of the tests begin
 * however if the tests go long the TB Accounts login session can expire.
 */
export const ensureWeAreSignedIn = async (page: Page) => {
    await navigateToAccountsHubAndSignIn(page);
    await page.context().storageState({ path: authFile });
}
