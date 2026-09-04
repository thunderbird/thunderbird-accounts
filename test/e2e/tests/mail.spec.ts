import { test } from '@playwright/test';
import { MailPage } from '../pages/mail-page';
import { ensureWeAreSignedIn, navigateToAccountsHubAndSignIn } from '../utils/utils';
import { isMobileAndroidProject, isMobileProject } from '../utils/test-project';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../const/constants';

let mailPage: MailPage;

test.beforeEach(async ({ page }, testInfo) => {
  mailPage = new MailPage(page);
  if (isMobileProject(testInfo.project.name)) {
    // BrowserStack mobile projects cannot reuse the desktop setup's storage state.
    await navigateToAccountsHubAndSignIn(page, {
      isMobileAndroid: isMobileAndroidProject(testInfo.project.name),
    });
  } else {
    // Desktop projects load saved auth, but refresh it if the session has expired.
    await ensureWeAreSignedIn(page);
  }
});

test.describe('mail page components on browser', {
  tag: [
    PLAYWRIGHT_TAG_E2E_SUITE,
    PLAYWRIGHT_TAG_E2E_PROD_DESKTOP_NIGHTLY,
    PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
    PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ],
}, () => {
  test('all visible mail page components work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate subscribe step');
    await mailPage.navigateToMail();
    await mailPage.verifyWelcomeDashboardDisplayed();
    await mailPage.verifyGetStartedComponents();
    await mailPage.verifyEmailSettingsComponents();
    await mailPage.verifyCustomDomainsComponents();
  });
});
