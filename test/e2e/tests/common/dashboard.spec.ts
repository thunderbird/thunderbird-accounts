import { test } from '@playwright/test';
import { DashboardPage } from '../../pages/dashboard-page';
import { isMobileAndroidProject, navigateToAccountsHubAndSignIn } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../../const/constants';

let dashboardPage: DashboardPage;

test.beforeEach(async ({ page }, testInfo) => {
  const isMobileAndroid = isMobileAndroidProject(testInfo.project.name);
  dashboardPage = new DashboardPage(page, isMobileAndroid);
  await navigateToAccountsHubAndSignIn(page, {
    isMobileAndroid,
  });
});

/**
 * Prerequisite: This test assumes that the signed-in user already has a TB Pro subscription
 * and therefore the main dashboard is visible (and not redirected to the subscription page).
 * On a new local dev stack (including PR CI), the test user does not yet have a subscription,
 * so this scenario is skipped. The existing stage and prod nightly accounts are subscribed.
 * Issue 771 tracks adding a subscribe step so this can run on new local stacks too.
 */
test.describe('dashboard controls on browser', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  test('all visible dashboard controls work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate tb subscribe step');

    await dashboardPage.navigateToDashboard();
    await dashboardPage.verifyDashboardSignedIn();
    await dashboardPage.verifyDashboardDisplayed();
    await dashboardPage.verifyGetStartedComponents();

    await dashboardPage.verifyPasswordChangeNavigation();
    await dashboardPage.navigateToDashboard();

    await dashboardPage.verifyDeleteAccountNavigationOnly();
    await dashboardPage.navigateToDashboard();

    await dashboardPage.verifyServiceAppsLoadAfterNavigation();
    await dashboardPage.verifyManageSubscriptionOpensPortal();
    await dashboardPage.verifyUserMenuControls();
  });
});
