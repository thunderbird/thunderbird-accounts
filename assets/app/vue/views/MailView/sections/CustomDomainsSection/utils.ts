export const generateDNSRecords = async (domainName: string) => {
  const dnsHostname = window._page?.dnsHostname;

  return [
    {
      type: 'MX',
      name: '@',
      content: dnsHostname,
      priority: '10',
    },
    {
      type: 'CNAME',
      name: `mail.${domainName}`,
      content: dnsHostname,
      priority: '-',
    },
    {
      type: 'CNAME',
      name: `autoconfig.${domainName}.`,
      content: dnsHostname,
      priority: '-',
    },
    {
      type: 'CNAME',
      name: `autodiscover.${domainName}.`,
      content: dnsHostname,
      priority: '-',
    },
    {
      type: 'CNAME',
      name: `mta-sts.${domainName}.`,
      content: dnsHostname,
      priority: '-',
    },
    {
      type: 'SRV',
      name: `_jmap._tcp.${domainName}.`,
      content: `0 1 443 ${dnsHostname}`,
      priority: '-',
    },
    {
      type: 'SRV',
      name: `_caldavs._tcp.${domainName}.`,
      content: `0 1 443 ${dnsHostname}`,
      priority: '-',
    },
    {
      type: 'SRV',
      name: `_carddavs._tcp.${domainName}.`,
      content: `0 1 443 ${dnsHostname}`,
      priority: '-',
    },
    {
      type: 'SRV',
      name: `_imap._tcp.${domainName}.`,
      content: `0 1 443 ${dnsHostname}`,
      priority: '-',
    },
    {
      type: 'SRV',
      name: `_imaps._tcp.${domainName}.`,
      content: `0 1 993 ${dnsHostname}`,
      priority: '-',
    },
    {
      type: 'SRV',
      name: `_submission._tcp.${domainName}.`,
      content: `0 1 587 ${dnsHostname}`,
      priority: '-',
    },
    {
      type: 'TXT',
      name: domainName,
      content: 'v=spf1 ra=postmaster -all',
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
