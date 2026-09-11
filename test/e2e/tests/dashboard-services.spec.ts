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

test.describe('dashboard services', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  skipDashboardTestsOnLocalDev();

  test('service links open the expected authenticated applications', async ({ dashboardPage }) => {
    // The shared fixture signs in through the browser on mobile and reuses desktop
    // auth where supported. Thundermail uses the current page on both form factors,
    // while Appointment and Send open authenticated popups. Named steps identify
    // the exact service if one fails.
    await test.step('open Thundermail', async () => {
      await dashboardPage.verifyThundermailNavigation();
    });

    await dashboardPage.navigateToDashboard();

    await test.step('open authenticated Appointment', async () => {
      await dashboardPage.verifyAppointmentAppLoadsAfterNavigation();
    });

    await test.step('open authenticated Send', async () => {
      await dashboardPage.verifySendAppLoadsAfterNavigation();
    });
  });
});
