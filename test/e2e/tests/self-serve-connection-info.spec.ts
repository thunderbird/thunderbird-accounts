import { test, expect } from '@playwright/test';
import { SelfServePage } from '../pages/self-serve-page';
import { FxAPage } from '../pages/fxa-page';
import { connectionInfo } from '../const/types';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  IMAP_PORT,
  JMAP_PORT,
  SMTP_PORT,
  ACCTS_HOST,
  SECURITY_SSL_TLS,
  APP_PASSWORD,
  YOUR_EMAIL_LBL,
  THUNDERMAIL_USERNAME,
  THUNDERMAIL_EMAIL_ADDRESS,
  ACCTS_TARGET_ENV,
 } from '../const/constants';

let selfServePage: SelfServePage;
let fxaPage: FxAPage;

test.beforeEach(async ({ page }) => {
  selfServePage = new SelfServePage(page);
  fxaPage = new FxAPage(page);
  // we are already signed into accounts via our auth.setup
  await selfServePage.navigateToSelfServeHub();
});

test.describe('self-serve hub connection info', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('connection info displayed correctly', async ({ page }) => {
    // headers and link
    await expect(selfServePage.selfServeConnectionInfoHeader).toBeVisible();
    await expect(selfServePage.welcomeBackHeader).toBeVisible();
    await expect(selfServePage.accountInfoLink).toBeEnabled();

    var expectedInfo: connectionInfo = {
        'hostName': ACCTS_HOST,
        'port': IMAP_PORT,
        'securityType': SECURITY_SSL_TLS,
        'userName': THUNDERMAIL_USERNAME,
        'appPassword': APP_PASSWORD,
      };

    // when running on the stage env a thundermail email is required, but might not exist on the local dev env
    if (ACCTS_TARGET_ENV == 'stage') {
      expect(await selfServePage.yourEmailAddressText.innerText()).toBe(`${YOUR_EMAIL_LBL} ${THUNDERMAIL_EMAIL_ADDRESS}`);
    }

    // check imap details
    await selfServePage.checkIMAPInfo(expectedInfo);

    // check jmap details
    expectedInfo['port'] = JMAP_PORT;
    await selfServePage.checkJMAPInfo(expectedInfo);

    // check smtp details
    expectedInfo['port'] = SMTP_PORT;
    await selfServePage.checkSMTPInfo(expectedInfo);
  });
});
