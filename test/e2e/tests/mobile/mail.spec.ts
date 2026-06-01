import { test } from '@playwright/test';
import { MailPage } from '../../pages/mail-page';
import { navigateToAccountsHubAndSignIn } from '../../utils/utils';

import {
  PLAYWRIGHT_TAG_E2E_SUITE_MOBILE,
  PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY,
  ACCTS_TARGET_ENV,
} from '../../const/constants';

let mailPage: MailPage;

test.beforeEach(async ({ page }) => {
  mailPage = new MailPage(page);
  await navigateToAccountsHubAndSignIn(page);
});

test.describe('mail page components on mobile browser', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE_MOBILE, PLAYWRIGHT_TAG_E2E_PROD_MOBILE_NIGHTLY],
}, () => {
  test('all visible mail page components work as expected', async () => {
    test.skip(ACCTS_TARGET_ENV == 'dev', 'Skipping this test when running on local dev stack until we automate subsrcibe step');

    await mailPage.navigateToMail();
    await mailPage.verifyWelcomeDashboardDisplayed();
    await mailPage.verifyGetStartedComponents();
    await mailPage.verifyEmailSettingsComponents();
    await mailPage.verifyCustomDomainsComponents();
  });
});
