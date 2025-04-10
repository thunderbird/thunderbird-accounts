import { test, expect } from '@playwright/test';
import { SelfServePage } from '../pages/self-serve-page';
import { FxAPage } from '../pages/fxa-page';
import { navigateToAccountsSelfServeHubAndSignIn } from '../utils/utils';
import { connectionInfo } from '../const/types';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  IMAP_SERVER_PORT,
  JMAP_SERVER_PORT,
  SMTP_SERVER_PORT,
  IMAP_SERVER_HOST,
  JMAP_SERVER_HOST,
  SMTP_SERVER_HOST,
  SECURITY_SSL_TLS,
  USERNAME_NONE,
  APP_PASSWORD_NONE,
 } from '../const/constants';

let selfServePage: SelfServePage;
let fxaPage: FxAPage;

test.beforeEach(async ({ page }) => {
  selfServePage = new SelfServePage(page);
  fxaPage = new FxAPage(page);
  await navigateToAccountsSelfServeHubAndSignIn(page);
});

test.describe('self-serve hub connection info', {
  tag: [PLAYWRIGHT_TAG_E2E_SUITE],
}, () => {
  test('displayed correctly with no email set up', async ({ page }) => {
    // headers and link
    await expect(selfServePage.selfServeConnectionInfoHeader).toBeVisible();
    await expect(selfServePage.welcomeBackHeader).toBeVisible();
    await expect(selfServePage.accountInfoLink).toBeEnabled();

    // imap details
    var expectedInfo: connectionInfo = {
      'serverName': IMAP_SERVER_HOST,
      'serverPort': IMAP_SERVER_PORT,
      'securityType': SECURITY_SSL_TLS,
      'userName': USERNAME_NONE,
      'appPassword': APP_PASSWORD_NONE,
    };

    // imap details
    await selfServePage.checkIMAPInfo(expectedInfo);

    // jmap details
    expectedInfo['serverName'] = JMAP_SERVER_HOST;
    expectedInfo['serverPort'] = JMAP_SERVER_PORT;
    await selfServePage.checkJMAPInfo(expectedInfo);

    // smtp details
    expectedInfo['serverName'] = SMTP_SERVER_HOST;
    expectedInfo['serverPort'] = SMTP_SERVER_PORT;
    await selfServePage.checkSMTPInfo(expectedInfo);
  });
});
