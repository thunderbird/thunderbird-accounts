import { test as base } from '@playwright/test';
import { ACCTS_TARGET_ENV } from '../const/constants';
import { DashboardPage } from '../pages/dashboard-page';
import { isMobileProject } from './test-project';
import { ensureWeAreSignedIn, navigateToAccountsHubAndSignIn } from './utils';

type DashboardFixtures = {
  dashboardPage: DashboardPage;
};

export const dashboardTest = base.extend<DashboardFixtures>({
  dashboardPage: async ({ page }, use, testInfo) => {
    if (isMobileProject(testInfo.project.name)) {
      // Mobile projects cannot reuse the desktop setup's storage state, so each
      // isolated dashboard test signs in through the browser before navigating.
      await navigateToAccountsHubAndSignIn(page);
    } else {
      // Desktop projects start with saved auth and refresh it only if it expired.
      await ensureWeAreSignedIn(page);
    }

    const dashboardPage = new DashboardPage(page);
    await dashboardPage.navigateToDashboard();
    await use(dashboardPage);
  },
});

/**
 * The local stack recognizes the test user's active subscription, but it does
 * not currently provide the subscription and quota details rendered here.
 * Stage and production test accounts have all required subscription data.
 */
export const skipDashboardTestsOnLocalDev = () => {
  dashboardTest.skip(
    ACCTS_TARGET_ENV == 'dev',
    'Skipping this test when running on local dev stack until subscription info appears when running on local dev stack',
  );
};
