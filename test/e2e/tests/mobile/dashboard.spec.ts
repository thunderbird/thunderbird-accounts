import { test } from '@playwright/test';
import { DashboardPage } from '../../pages/dashboard-page';
import { navigateToAccountsHubAndSignIn } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../../const/constants';

let dashboardPage: DashboardPage;

test.beforeEach(async ({ page }) => {
  dashboardPage = new DashboardPage(page);
  await navigateToAccountsHubAndSignIn(page);
});

/**
 * Prerequisite: This test assumes that the signed-in user already has a TB Pro subscription
 * and therefore the main dashboard is visible (and not redirected to the subscription page).
 * If this test is running in CI on a new local stack (i.e. on PRs) the test user (admin)
 * won't yet have a subscription, therefore skip this test when running in CI on PRs. This
 * test can run in the nighlty tests though because the existing test accounts on stage and
 * prod already have a TB Pro subscription setup. In future we will add a subscribe step so
 * we can run on new local stacks that aren't subscribed yet (issue 771).
 */
test.describe('dashboard controls on mobile browser', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE_MOBILE, PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY],
}, () => {
  test('all visible dashboard controls work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate tb subsrcibe step');

    await dashboardPage.navigateToDashboard();
    await dashboardPage.verifyDashboardSignedIn();
    await dashboardPage.verifyDashboardDisplayed();

    await dashboardPage.verifyPasswordChangeNavigation();
    await dashboardPage.navigateToDashboard();

    await dashboardPage.verifyDeleteAccountNavigationOnly();
    await dashboardPage.navigateToDashboard();

    await dashboardPage.verifyThundermailNavigation();
    await dashboardPage.navigateToDashboard();

    await dashboardPage.verifyServiceAppsLoadAfterNavigation();
    await dashboardPage.verifyManageSubscriptionOpensPortal();
    await dashboardPage.verifyUserMenuControls();
  });
});
