import type { DNSRecord } from "./types";

export const extractDKIMRecords = (dnsRecords: DNSRecord[], domainName: string) => {
  return dnsRecords.filter((record) => record.type === 'TXT' && record.name.includes(`_domainkey.${domainName}.`));
};

export const generateDNSRecords = (domainName: string) => {
  // Currently, we don't have a separate host for JMAP, IMAP or SMTP
  // in the future, if we do, we'll need to pass this as a separate variable
  const dnsHostname = window._page?.connectionInfo?.SMTP?.HOST;
  const dnsTopHost = dnsHostname?.split(".").slice(1).join(".");

  return [
    {
      type: 'MX',
      name: '@',
      content: dnsHostname,
      priority: '10',
    },
    {
      type: 'SRV',
      name: `_jmap._tcp.${domainName}.`,
      content: `1 443 ${dnsHostname}`,
      priority: '0',
    },
    {
      type: 'SRV',
      name: `_caldavs._tcp.${domainName}.`,
      content: `1 443 ${dnsHostname}`,
      priority: '0',
    },
    {
      type: 'SRV',
      name: `_carddavs._tcp.${domainName}.`,
      content: `1 443 ${dnsHostname}`,
      priority: '0',
    },
    {
      type: 'SRV',
      name: `_imaps._tcp.${domainName}.`,
      content: `1 993 ${dnsHostname}`,
      priority: '0',
    },
    {
      type: 'SRV',
      name: `_submission._tcp.${domainName}.`,
      content: `1 587 ${dnsHostname}`,
      priority: '0',
    },
    {
      type: 'TXT',
      name: domainName,
      content: `v=spf1 include:spf.${dnsTopHost} -all`,
      priority: '-',
    },
    {
      type: 'TXT',
      name: `_mta-sts.${domainName}.`,
      content: 'v=STSv1; id=18139500144460329770',
      priority: '-',
    },
    {
      type: 'TXT',
      name: `_smtp._tls.${domainName}.`,
      content: `v=TLSRPTv1; rua=mailto:postmaster@${domainName}`,
      priority: '-',
    },
    {
      type: 'TXT',
      name: `_dmarc.${domainName}.`,
      content: 'v=DMARC1; p=none;',
      priority: '-',
    },
  ];
};

/**
 * Deduplicates critical errors by consolidating ehloError and readGreetingError
 * since they represent the same issue (inability to verify domain records connect to Thundermail)
 */
export const deduplicateCriticalErrors = (errors: string[]): string[] => {
  const errorSet = new Set(errors);

  // If both ehloError and readGreetingError exist, keep only readGreetingError
  if (errorSet.has('ehloError') && errorSet.has('readGreetingError')) {
    errorSet.delete('ehloError');
  }

  // If only ehloError exists, replace it with readGreetingError
  else if (errorSet.has('ehloError')) {
    errorSet.delete('ehloError');
    errorSet.add('readGreetingError');
  }

  return Array.from(errorSet);
};
