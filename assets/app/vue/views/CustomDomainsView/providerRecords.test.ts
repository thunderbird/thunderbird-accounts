import { describe, expect, it } from 'vitest';
import { buildProviderRecordGroups, buildTokenContext } from './providerRecords';
import { DNS_PROVIDERS, GENERIC_DNS_PROVIDER_ID } from './dnsProviders';
import type { DNSRecord } from './types';

const DOMAIN = 'example.com';

const records: DNSRecord[] = [
  { type: 'MX', name: '@', content: 'mail.thundermail.com.', priority: '10' },
  { type: 'SRV', name: '_imaps._tcp.example.com.', content: '1 993 mail.thundermail.com', priority: '0' },
  { type: 'TXT', name: 'example.com.', content: 'v=spf1 include:spf.thundermail.com -all', priority: '-' },
  { type: 'CNAME', name: 'tm1._domainkey.example.com.', content: 'tm1.example.com.dkim.thunderhosted.com.', priority: '-' },
];

const provider = (id: string) => DNS_PROVIDERS.find((candidate) => candidate.id === id);

describe('buildTokenContext', () => {
  it('derives the relative host and SRV parts from the record name', () => {
    const context = buildTokenContext(records[1], DOMAIN);

    expect(context).toMatchObject({
      host: '_imaps._tcp',
      service: '_imaps',
      protocol: '_tcp',
      srvhost: '@',
      weight: '1',
      port: '993',
      target: 'mail.thundermail.com',
      match: '0 1 993 mail.thundermail.com',
    });
  });

  it('uses @ for the domain itself and drops trailing dots from targets', () => {
    expect(buildTokenContext(records[2], DOMAIN)).toMatchObject({ host: '@', subhost: '' });
    expect(buildTokenContext(records[0], DOMAIN)).toMatchObject({ target: 'mail.thundermail.com', match: '10 mail.thundermail.com' });
  });
});

describe('buildProviderRecordGroups', () => {
  it('lays records out in the fields of the chosen provider', () => {
    const groups = buildProviderRecordGroups(records, DOMAIN, provider('namecheap'));

    expect(groups.map((group) => group.type)).toEqual(['MX', 'SRV', 'TXT', 'CNAME']);
    expect(groups[0].columns).toEqual(['Host', 'Mail Server', 'Priority']);
    expect(groups[0].rows[0].map((cell) => cell.value)).toEqual(['@', 'mail.thundermail.com', '10']);
  });

  it('keeps hints out of the value to copy', () => {
    const [cname] = buildProviderRecordGroups([records[3]], DOMAIN, provider('namecheap'));
    const target = cname.rows[0][1];

    expect(target.value).toBe('tm1.example.com.dkim.thunderhosted.com');
    expect(target.hint).toBe('(no trailing dot)');
  });

  it('leaves the host blank at the apex for providers that expect it', () => {
    const [mx] = buildProviderRecordGroups([records[0]], DOMAIN, provider('cosmotown'));
    const host = mx.rows[0].find((cell) => cell.label === 'Host');

    expect(host.value).toBe('');
  });

  it('moves columns with the same value in every row out of the table', () => {
    const srv = (name: string, port: string): DNSRecord => ({
      type: 'SRV',
      name: `${name}._tcp.example.com.`,
      content: `0 ${port} mail.thundermail.com`,
      priority: '0',
    });
    const [group] = buildProviderRecordGroups([srv('_imap', '143'), srv('_imaps', '993')], DOMAIN, provider('godaddy'));

    expect(group.columns).not.toContain('Priority');
    expect(group.columns).not.toContain('Weight');
    expect(group.columns).toContain('Port');
    expect(group.columns).toContain('Name');
    expect(group.sharedFields).toEqual([
      { label: 'Priority', value: '0' },
      { label: 'Weight', value: '0' },
    ]);
    expect(group.rows.every((row) => row.length === group.columns.length)).toBe(true);
  });

  it('keeps every column when there is a single row', () => {
    const [mx] = buildProviderRecordGroups([records[0]], DOMAIN, provider('godaddy'));

    expect(mx.sharedFields).toEqual([]);
    expect(mx.columns).toHaveLength(4);
  });

  it('supports the generic provider', () => {
    const groups = buildProviderRecordGroups(records, DOMAIN, provider(GENERIC_DNS_PROVIDER_ID));

    expect(groups[1].rows[0].map((cell) => cell.value)).toEqual(['SRV', '_imaps._tcp.example.com.', '0 1 993 mail.thundermail.com', '0']);
  });
});
