import { test, expect } from '@playwright/test';
import { SelfServePage } from '../pages/self-serve-page';
import { OIDCKeycloakPage } from '../pages/oidc/keycloak-login-page';
import { connectionInfo } from '../const/types';

import {
  PLAYWRIGHT_TAG_E2E_SUITE,
  IMAP_PORT,
  JMAP_PORT,
  SMTP_PORT,
  ACCTS_HOST,
  IMAP_TLS,
  JMAP_TLS,
  SMTP_TLS,
  APP_PASSWORD,
  YOUR_EMAIL_LBL,
  THUNDERMAIL_USERNAME,
  THUNDERMAIL_EMAIL_ADDRESS,
  ACCTS_TARGET_ENV,
 } from '../const/constants';

let selfServePage: SelfServePage;
let keycloakPage: OIDCKeycloakPage;

test.beforeEach(async ({ page }) => {
  selfServePage = new SelfServePage(page);
  keycloakPage = new OIDCKeycloakPage(page);
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
        'securityType': IMAP_TLS,
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
    expectedInfo['securityType'] = JMAP_TLS;
    await selfServePage.checkJMAPInfo(expectedInfo);

    // check smtp details
    expectedInfo['port'] = SMTP_PORT;
    expectedInfo['securityType'] = SMTP_TLS;
    await selfServePage.checkSMTPInfo(expectedInfo);
  });
});
