import type { DNSRecord, DnsProviderConfig } from './types';

type TokenContext = Record<string, string>;

const stripTrailingDot = (value: string): string => value.replace(/\.$/, '');

// Everything after a run of two or more spaces is a hint for the reader (e.g. "(no trailing dot)")
// and must never end up in the clipboard
const HINT_SEPARATOR = /\s{2,}/;

// The name relative to the domain, with "@" standing for the domain itself
const relativeHost = (recordName: string, domainName: string): string => {
  const name = stripTrailingDot(recordName).toLowerCase();
  const domain = stripTrailingDot(domainName).toLowerCase();

  if (name === '@' || name === domain) {
    return '@';
  }
  return name.endsWith(`.${domain}`) ? name.slice(0, -(domain.length + 1)) : name;
};

// Values for the {tokens} the provider instructions are written with
export const buildTokenContext = (record: DNSRecord, domainName: string): TokenContext => {
  const domain = stripTrailingDot(domainName);
  const host = relativeHost(record.name, domain);
  const priority = record.priority && record.priority !== '-' ? record.priority : '';
  const labels = host.split('.');
  const context: TokenContext = {
    domain,
    host,
    priority,
    fqdn: host === '@' ? `${domain}.` : `${host}.${domain}.`,
    // Blank at the apex, for panels that expect the field to be left empty rather than "@"
    subhost: host === '@' ? '' : host,
    // SRV panels that split "_service._protocol" into separate fields
    service: labels[0],
    protocol: labels[1] ?? '',
    srvhost: labels.slice(2).join('.') || '@',
    srvsubhost: labels.slice(2).join('.'),
    bareservice: labels[0].replace(/^_+/, ''),
    bareprotocol: (labels[1] ?? '').replace(/^_+/, ''),
  };

  if (record.type === 'SRV') {
    const [weight, port, ...target] = record.content.trim().split(/\s+/);
    context.weight = weight;
    context.port = port;
    context.target = stripTrailingDot(target.join(' '));
    context.value = `${weight} ${port} ${context.target}`;
    context.match = `${priority} ${context.value}`;
  } else if (record.type === 'MX' || record.type === 'CNAME') {
    context.target = stripTrailingDot(record.content);
    context.value = context.target;
    context.match = record.type === 'MX' ? `${priority} ${context.target}` : context.target;
  } else {
    context.value = record.content;
    context.match = record.content;
  }

  return context;
};

const interpolate = (template: string, context: TokenContext): string =>
  template.replace(/\{(\w+)\}/g, (_, token: string) => context[token] ?? '');

export type ProviderCell = {
  label: string;
  // What belongs in the provider's field, empty when it should be left blank
  value: string;
  hint: string;
};

export type ProviderRecordGroup = {
  type: string;
  header: string;
  columns: string[];
  rows: ProviderCell[][];
};

// Groups the records by type, in the order they first appear, with each record laid out
// in the fields the provider's panel asks for
export const buildProviderRecordGroups = (
  records: DNSRecord[],
  domainName: string,
  provider: DnsProviderConfig
): ProviderRecordGroup[] => {
  const groups = new Map<string, ProviderRecordGroup>();

  records.forEach((record) => {
    const instructions = provider.records[record.type as keyof DnsProviderConfig['records']];
    if (!instructions) {
      return;
    }

    if (!groups.has(record.type)) {
      groups.set(record.type, {
        type: record.type,
        header: instructions.header,
        columns: instructions.fields.map((field) => field.label),
        rows: [],
      });
    }

    const context = buildTokenContext(record, domainName);
    groups.get(record.type).rows.push(
      instructions.fields.map((field) => {
        const [value, ...hint] = interpolate(field.template, context).split(HINT_SEPARATOR);
        return { label: field.label, value, hint: hint.join(' ') };
      })
    );
  });

  return [...groups.values()];
};
