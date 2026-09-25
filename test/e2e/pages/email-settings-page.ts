import { expect, type Locator, type Page } from '@playwright/test';
import {
  ACCTS_HOST,
  ACCTS_HUB_URL,
  DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS,
  DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES,
  IMAP_PORT,
  IMAP_TLS,
  JMAP_PORT,
  JMAP_TLS,
  PRIMARY_THUNDERMAIL_EMAIL,
  SMTP_PORT,
  SMTP_TLS,
  TIMEOUT_1_SECOND,
  TIMEOUT_2_SECONDS,
  TIMEOUT_5_SECONDS,
} from '../const/constants';
import { waitForVueApp } from '../utils/utils';

const hasTls = (tls: string) => Boolean(tls && tls !== 'None' && tls !== 'undefined');
const formatPort = (port: number, tls: string) => `${port}${hasTls(tls) ? ' (SSL/TLS)' : ''}`;
const TEST_EMAIL_ALIAS_LOCAL_PART_PREFIX = 'testalias';

export class EmailSettingsPage {
  readonly page: Page;
  readonly emailSettingsSection: Locator;
  readonly customDomainsSection: Locator;
  readonly serverSettingsAccordion: Locator;
  readonly emailAliasesSection: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailSettingsSection = this.page.locator('section#email-settings');
    this.customDomainsSection = this.emailSettingsSection.locator('.custom-domains-details-summary');
    this.serverSettingsAccordion = this.emailSettingsSection.locator('.accordion').filter({ hasText: 'Server settings' });
    this.emailAliasesSection = this.emailSettingsSection.locator('.email-aliases-content');
  }

  async navigateToEmailSettings() {
    await this.page.goto(`${ACCTS_HUB_URL}/settings`);
    await this.waitForPageToSettle();
    await expect.poll(async () => new URL(this.page.url()).pathname).toBe('/settings');
  }

  async verifyEmailSettingsComponents() {
    await this.emailSettingsSection.scrollIntoViewIfNeeded();
    await expect(this.emailSettingsSection.getByRole('heading', { name: 'Email settings' })).toBeVisible();

    await this.verifyEmailAliasFormOpensAndCancels();
    await this.verifyCanAddAndDeleteEmailAlias();
    await this.verifyServerSettings();
  }

  async verifyCustomDomainsComponents() {
    const customDomainsHeader = this.customDomainsSection.getByRole('button', { name: 'Custom domains' });
    await customDomainsHeader.scrollIntoViewIfNeeded();
    await expect(customDomainsHeader).toBeVisible();
    await customDomainsHeader.click();

    await expect(this.customDomainsSection).toContainText('Use your own domain to create personalized email addresses.');
    await expect(this.customDomainsSection.locator('.domains-added')).toContainText(
      new RegExp(`of\\s+${this.escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_CUSTOM_DOMAINS)}\\s+custom domains used`),
    );

    await this.verifyCustomDomainActionMenuIfPresent();
    await this.verifyAddDomainFormCanOpen();
  }

  private async verifyEmailAliasFormOpensAndCancels() {
    const emailAliasesHeader = this.emailSettingsSection.getByRole('button', { name: 'Email aliases' });
    await emailAliasesHeader.scrollIntoViewIfNeeded();
    await expect(emailAliasesHeader).toBeVisible();
    await emailAliasesHeader.click();

    await this.emailAliasesSection.scrollIntoViewIfNeeded();
    await expect(this.emailAliasesSection).toContainText(PRIMARY_THUNDERMAIL_EMAIL);
    await expect(this.emailAliasesSection.locator('.email-aliases-count-text').filter({ hasText: 'aliases used' })).toContainText(
      new RegExp(`of\\s+${this.escapeRegExp(DASHBOARD_CURRENT_SUBSCRIPTION_EMAIL_ADDRESSES)}\\s+aliases used`),
    );
    const primaryAliasRow = this.emailAliasesSection.locator('.alias-item').filter({ hasText: PRIMARY_THUNDERMAIL_EMAIL });
    await expect(primaryAliasRow).toBeVisible();
    await expect(primaryAliasRow).toContainText('Primary');
    await expect(primaryAliasRow).toContainText('Subscription');

    const addAliasButton = this.emailAliasesSection.getByRole('button', { name: 'Create email alias' });
    if (await addAliasButton.isVisible()) {
      await addAliasButton.click();
      await expect(this.emailAliasesSection.locator('input[name="email-alias"]')).toBeVisible();
      const domainSelect = this.emailAliasesSection.locator('select[name="domain"]');
      await expect(domainSelect).toBeVisible();
      expect(ACCTS_HOST).toContain(await domainSelect.inputValue());
      await expect(this.emailAliasesSection.getByRole('button', { name: 'Submit' })).toBeVisible();
      await this.emailAliasesSection.getByRole('button', { name: 'Cancel' }).click();
      await expect(this.emailAliasesSection.locator('input[name="email-alias"]')).not.toBeVisible();
    }
  }

  private async verifyCanAddAndDeleteEmailAlias() {
    const aliasUsageText = await this.emailAliasesSection.locator('.email-aliases-count-text').filter({ hasText: 'aliases used' }).first().innerText();
    const aliasUsageMatch = aliasUsageText.match(/(\d+)\s+of\s+(\d+)\s+aliases used/i);
    if (!aliasUsageMatch) {
      throw new Error(`Could not determine alias usage from text: "${aliasUsageText}"`);
    }

    const aliasesUsed = Number(aliasUsageMatch[1]);
    const aliasLimit = Number(aliasUsageMatch[2]);
    if (aliasesUsed >= aliasLimit) {
      console.log('Skipping add/delete alias test because the maximum number of aliases are already in use.');
      return;
    }

    const addAliasButton = this.emailAliasesSection.getByRole('button', { name: 'Create email alias' });
    await expect(addAliasButton).toBeVisible();
    await addAliasButton.click();

    let aliasInput = this.emailAliasesSection.locator('input[name="email-alias"]');
    let domainSelect = this.emailAliasesSection.locator('select[name="domain"]');
    await expect(aliasInput).toBeVisible();
    await expect(domainSelect).toBeVisible();

    const selectedDomain = await domainSelect.inputValue();
    expect(ACCTS_HOST).toContain(selectedDomain);

    const testAliasLocalPart = `${TEST_EMAIL_ALIAS_LOCAL_PART_PREFIX}${Date.now()}`;
    const testAliasEmail = `${testAliasLocalPart}@${selectedDomain}`;
    const existingTestAliasRow = this.getEmailAliasRow(testAliasEmail);
    if (await existingTestAliasRow.count() > 0 && await existingTestAliasRow.isVisible()) {
      await this.emailAliasesSection.getByRole('button', { name: 'Cancel' }).click();
      await this.deleteEmailAlias(testAliasEmail);
      await this.page.waitForTimeout(TIMEOUT_1_SECOND);

      await addAliasButton.click();
      aliasInput = this.emailAliasesSection.locator('input[name="email-alias"]');
      domainSelect = this.emailAliasesSection.locator('select[name="domain"]');
      await expect(aliasInput).toBeVisible();
      await expect(domainSelect).toBeVisible();
      expect(await domainSelect.inputValue()).toBe(selectedDomain);
    }

    await aliasInput.fill(testAliasLocalPart);
    await this.emailAliasesSection.getByRole('button', { name: 'Submit' }).click();
    await this.page.waitForTimeout(TIMEOUT_1_SECOND);

    const testAliasRow = this.getEmailAliasRow(testAliasEmail);
    await expect(testAliasRow).toBeVisible();
    await expect(testAliasRow).not.toContainText('Primary');
    await expect(testAliasRow).not.toContainText('Subscription');

    await this.deleteEmailAlias(testAliasEmail);
    await this.page.waitForTimeout(TIMEOUT_1_SECOND);
    await expect(testAliasRow).not.toBeVisible();
  }

  private getEmailAliasRow(emailAlias: string) {
    return this.emailAliasesSection.locator('.alias-item').filter({ hasText: emailAlias });
  }

  private async deleteEmailAlias(emailAlias: string) {
    const aliasRow = this.getEmailAliasRow(emailAlias);
    await expect(aliasRow).toBeVisible();
    await aliasRow.locator('.kebab-menu-button').click();
    await aliasRow.getByRole('button', { name: 'Delete' }).click();
  }

  private async verifyServerSettings() {
    await this.serverSettingsAccordion.scrollIntoViewIfNeeded();
    await this.serverSettingsAccordion.getByRole('button', { name: 'Server settings' }).click();
    await expect(this.serverSettingsAccordion).toContainText('Incoming server');
    await expect(this.serverSettingsAccordion).toContainText('Outgoing server');
    await this.verifyServerSettingsValues(this.serverSettingsAccordion);
  }

  private async verifyServerSettingsValues(container: Locator) {
    const incomingServerCard = container.locator('.server-settings-card').filter({ hasText: 'Incoming server' });
    const outgoingServerCard = container.locator('.server-settings-card').filter({ hasText: 'Outgoing server' });

    await incomingServerCard.getByRole('button', { name: 'IMAP' }).click();
    await this.verifyServerCardValues(incomingServerCard, ACCTS_HOST, formatPort(IMAP_PORT, IMAP_TLS));

    await incomingServerCard.getByRole('button', { name: 'JMAP' }).click();
    await this.verifyServerCardValues(incomingServerCard, ACCTS_HOST, formatPort(JMAP_PORT, JMAP_TLS));

    await outgoingServerCard.getByRole('button', { name: 'SMTP' }).click();
    await this.verifyServerCardValues(outgoingServerCard, ACCTS_HOST, formatPort(SMTP_PORT, SMTP_TLS));
  }

  private async verifyServerCardValues(serverCard: Locator, expectedServer: string, expectedPort: string) {
    const serverValue = serverCard
      .locator('.server-detail-item')
      .filter({ hasText: 'SERVER:' })
      .locator('.server-detail-item-value span');
    const portValue = serverCard
      .locator('.server-detail-item')
      .filter({ hasText: 'PORT:' })
      .locator('.server-detail-item-value span');

    await expect(serverValue).toHaveText(expectedServer);
    await expect(portValue).toContainText(expectedPort);
  }

  private async verifyCustomDomainActionMenuIfPresent() {
    const actionButtons = this.customDomainsSection.locator('.custom-domain-item .kebab-menu-button');
    if (await actionButtons.count() === 0) {
      return;
    }

    const firstDomain = this.customDomainsSection.locator('.custom-domain-item').first();
    await expect(firstDomain).toContainText(/verified|Pending|Failed/);
    await actionButtons.first().click();
    await expect(this.customDomainsSection.getByRole('button', { name: 'View DNS records' })).toBeVisible();
    await expect(this.customDomainsSection.getByRole('button', { name: /Verify|Re-verify/ })).toBeVisible();
    await expect(this.customDomainsSection.getByRole('button', { name: 'Delete' })).toBeVisible();
    await this.customDomainsSection.locator('.custom-domains-header-row').click();
  }

  private async verifyAddDomainFormCanOpen() {
    const addDomainButton = this.customDomainsSection.getByRole('button', { name: 'Add domain' });
    if (await addDomainButton.count() === 0 || !(await addDomainButton.isVisible())) {
      return;
    }

    await addDomainButton.click();
    await expect(this.customDomainsSection.locator('input[name="custom-domain"]')).toBeVisible();
    await expect(this.customDomainsSection.getByRole('button', { name: 'Continue' })).toBeVisible();
  }

  private async waitForPageToSettle() {
    await waitForVueApp(this.page);
    await this.page.waitForLoadState('networkidle', { timeout: TIMEOUT_5_SECONDS }).catch(() => {});
    await this.page.waitForTimeout(TIMEOUT_2_SECONDS);
  }

  private escapeRegExp(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }
}
