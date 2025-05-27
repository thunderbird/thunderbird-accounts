import { expect, type Page, type Locator } from '@playwright/test';
import { ACCTS_SELF_SERVE_URL, ACCTS_FXA_EMAIL, ACCTS_TARGET_ENV, TIMEOUT_60_SECONDS, TIMEOUT_5_SECONDS } from '../const/constants';
import { connectionInfo } from '../const/types';

export class SelfServePage {
  readonly page: Page;
  readonly pageHeader: Locator;
  readonly selfServeConnectionInfoHeader: Locator;
  readonly selfServeAccountInfoHeader: Locator;
  readonly welcomeBackHeader: Locator;
  readonly logoutLink: Locator;
  readonly userDisplayName: string;
  readonly accountInfoLink: Locator;
  readonly yourEmailAddressText: Locator;
  readonly imapServerName: Locator;
  readonly imapServerPort: Locator;
  readonly imapSecurityType: Locator;
  readonly imapUsername: Locator;
  readonly imapPassword: Locator;
  readonly jmapServerName: Locator;
  readonly jmapServerPort: Locator;
  readonly jmapSecurityType: Locator;
  readonly jmapUsername: Locator;
  readonly jmapPassword: Locator;
  readonly smtpServerName: Locator;
  readonly smtpServerPort: Locator;
  readonly smtpSecurityType: Locator;
  readonly smtpUsername: Locator;
  readonly smtpPassword: Locator;
  readonly emailHeader: Locator;
  readonly noEmailSetupText: Locator;
  readonly emailSetupBtn: Locator;
  readonly deleteAccountHeader: Locator;
  readonly deleteAcctText: Locator;
  readonly deleteAcctBtn: Locator;

  constructor(page: Page) {
    this.page = page;

    // headers and links
    this.pageHeader = this.page.getByRole('heading', { name: 'Accounts Hub'});
    this.selfServeConnectionInfoHeader = this.page.getByRole('heading', { name: 'Self Serve - Connection Information'});
    this.selfServeAccountInfoHeader = this.page.getByRole('heading', { name: 'Self Serve - Account Information'});
    this.userDisplayName = ACCTS_FXA_EMAIL.split('@')[0];
    this.welcomeBackHeader = this.page.getByText(`Welcome back ${this.userDisplayName}.`, { exact: true });
    this.logoutLink = this.page.getByRole('link', { name: 'Logout'});
    this.accountInfoLink = this.page.getByRole('link', { name: 'Account Info'});
    this.yourEmailAddressText = this.page.getByTestId('connection-info-primary-email-address');

    // imap details
    this.imapServerName = this.page.getByTestId('connection-info-imap-server');
    this.imapServerPort = this.page.getByTestId('connection-info-imap-port');
    this.imapSecurityType = this.page.getByTestId('connection-info-imap-security');
    this.imapUsername = this.page.getByTestId('connection-info-imap-username');
    this.imapPassword = this.page.getByTestId('connection-info-imap-password');

    // jmap details
    this.jmapServerName = this.page.getByTestId('connection-info-jmap-server');
    this.jmapServerPort = this.page.getByTestId('connection-info-jmap-port');
    this.jmapSecurityType = this.page.getByTestId('connection-info-jmap-security');
    this.jmapUsername = this.page.getByTestId('connection-info-jmap-username');
    this.jmapPassword = this.page.getByTestId('connection-info-jmap-password');

    // smtp details
    this.smtpServerName = this.page.getByTestId('connection-info-smtp-server');
    this.smtpServerPort = this.page.getByTestId('connection-info-smtp-port');
    this.smtpSecurityType = this.page.getByTestId('connection-info-smtp-security');
    this.smtpUsername = this.page.getByTestId('connection-info-smtp-username');
    this.smtpPassword = this.page.getByTestId('connection-info-smtp-password');
  
    // account info
    this.emailHeader = this.page.getByRole('heading', { name: 'Email' });
    this.noEmailSetupText = this.page.getByTestId('account-info-no-email-setup-text');
    this.emailSetupBtn = this.page.getByRole('button', { name: 'Set Up' });
    this.deleteAccountHeader = this.page.getByRole('heading', { name: 'Delete Account' });
    this.deleteAcctText = this.page.getByTestId('account-info-delete-account-description');
    this.deleteAcctBtn = this.page.getByRole('button', { name: 'Delete Account' });
  }

  async navigateToSelfServeHub() {
    await this.page.waitForTimeout(TIMEOUT_5_SECONDS);
    await this.page.goto(ACCTS_SELF_SERVE_URL, { timeout: TIMEOUT_60_SECONDS });
    await this.page.waitForTimeout(TIMEOUT_5_SECONDS);
  }

  async checkIMAPInfo(expectedInfo: connectionInfo) {
    expect(await this.imapServerName.innerText({ timeout: TIMEOUT_5_SECONDS })).toBe(`Server Name: ${expectedInfo['hostName']}`);
    expect(await this.imapServerPort.innerText()).toBe(`Server Port: ${expectedInfo['port']}`);
    expect(await this.imapSecurityType.innerText()).toBe(`Security: ${expectedInfo['securityType']}`);
    // when running on the stage env a thundermail email is required, but might not exist on the local dev env
    if (ACCTS_TARGET_ENV == 'stage') {
      expect(await this.imapUsername.innerText()).toBe(`Username: ${expectedInfo['userName']}`);
    }
    expect(await this.imapPassword.innerText()).toBe(`Password: ${expectedInfo['appPassword']}`);
  }

  async checkJMAPInfo(expectedInfo: connectionInfo) {
    expect(await this.jmapServerName.innerText({ timeout: TIMEOUT_5_SECONDS })).toBe(`Server Name: ${expectedInfo['hostName']}`);
    expect(await this.jmapServerPort.innerText()).toBe(`Server Port: ${expectedInfo['port']}`);
    expect(await this.jmapSecurityType.innerText()).toBe(`Security: ${expectedInfo['securityType']}`);
    // when running on the stage env a thundermail email is required, but might not exist on the local dev env
    if (ACCTS_TARGET_ENV == 'stage') {
      expect(await this.jmapUsername.innerText()).toBe(`Username: ${expectedInfo['userName']}`);
    }
    expect(await this.jmapPassword.innerText()).toBe(`Password: ${expectedInfo['appPassword']}`);
  }

  async checkSMTPInfo(expectedInfo: connectionInfo) {
    expect(await this.smtpServerName.innerText({ timeout: TIMEOUT_5_SECONDS })).toBe(`Server Name: ${expectedInfo['hostName']}`);
    expect(await this.smtpServerPort.innerText()).toBe(`Server Port: ${expectedInfo['port']}`);
    expect(await this.smtpSecurityType.innerText()).toBe(`Security: ${expectedInfo['securityType']}`);
    // when running on the stage env a thundermail email is required, but might not exist on the local dev env
    if (ACCTS_TARGET_ENV == 'stage') {
      expect(await this.smtpUsername.innerText()).toBe(`Username: ${expectedInfo['userName']}`);
    }
    expect(await this.smtpPassword.innerText()).toBe(`Password: ${expectedInfo['appPassword']}`);
  }
}
