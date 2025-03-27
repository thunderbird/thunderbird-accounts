import { type Page, type Locator } from '@playwright/test';
import { ACCTS_SELF_SERVE_URL, ACCTS_FXA_EMAIL } from '../const/constants';

export class SelfServePage {
  readonly page: Page;
  readonly pageHeader: Locator;
  readonly selfServeHeader: Locator;
  readonly welcomeBackHeader: Locator;
  readonly logoutLink: Locator;
  readonly userDisplayName: string;
  readonly accountInfoLink: Locator;
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

  constructor(page: Page) {
    this.page = page;

    // headers and links
    this.pageHeader = this.page.getByRole('heading', { name: 'Accounts Hub'});
    this.selfServeHeader = this.page.getByRole('heading', { name: 'Self Serve - Connection Information'});
    this.userDisplayName = ACCTS_FXA_EMAIL.split('@')[0];
    this.welcomeBackHeader = this.page.getByText(`Welcome back ${this.userDisplayName}.`, { exact: true });
    this.logoutLink = this.page.getByRole('link', { name: 'Logout'});
    this.accountInfoLink = this.page.getByRole('link', { name: 'Account Info'});

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
  }

  async navigateToSelfServeHub() {
    await this.page.goto(ACCTS_SELF_SERVE_URL);
  }
}
