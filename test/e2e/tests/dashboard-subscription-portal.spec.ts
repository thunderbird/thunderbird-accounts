import {
  dashboardTest as test,
  skipDashboardTestsOnLocalDev,
} from '../utils/dashboard-test';
import {
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
} from '../const/constants';

test.describe('dashboard subscription portal', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  skipDashboardTestsOnLocalDev();

  test('manage subscription opens the Paddle customer portal', async ({ dashboardPage }) => {
    // The project-specific mobile or desktop sign-in route completes in the shared
    // fixture before this separately isolated external Paddle flow begins.
    await dashboardPage.verifyManageSubscriptionOpensPortal();
  });
});
