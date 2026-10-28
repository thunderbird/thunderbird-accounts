import type { DnsProviderConfig } from './types';

export const GENERIC_DNS_PROVIDER_ID = 'generic';

export const DNS_PROVIDERS: DnsProviderConfig[] = [
  {
    id: "bunny",
    label: "Bunny",
    records: {
      MX: {
        fields: [
          { label: "Hostname", template: "{subhost}" },
          { label: "Type", template: "MX" },
          { label: "Value", template: "{match}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Hostname", template: "{host}" },
          { label: "Type", template: "SRV" },
          { label: "Value", template: "{match}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Hostname", template: "{subhost}" },
          { label: "Type", template: "TXT" },
          { label: "Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Hostname", template: "{host}" },
          { label: "Type", template: "CNAME" },
          { label: "Value", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "cloudflare",
    label: "Cloudflare",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Name", template: "{host}" },
          { label: "Mail server", template: "{target}" },
          { label: "Priority", template: "{priority}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Name", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
          { label: "Target", template: "{target}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Name", template: "{host}" },
          { label: "Content", template: "\"{value}\"" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Name", template: "{host}" },
          { label: "Target", template: "{target}" },
          { label: "Proxy status", template: "DNS only" },
        ],
      },
    },
  },
  {
    id: "cosmotown",
    label: "Cosmotown",
    records: {
      MX: {
        fields: [
          { label: "Priority", template: "{priority}" },
          { label: "Host", template: "{subhost}" },
          { label: "Points to", template: "{target}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
          { label: "Target", template: "{target}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Host", template: "{subhost}" },
          { label: "TXT Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Host", template: "{subhost}" },
          { label: "Points to", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "digitalocean",
    label: "DigitalOcean",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Hostname", template: "{host}" },
          { label: "Mail provider's mail server", template: "{target}" },
          { label: "Priority", template: "{priority}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Hostname", template: "{host}" },
          { label: "Will direct to", template: "{target}." },
          { label: "Port", template: "{port}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Hostname", template: "{host}" },
          { label: "TXT Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Hostname", template: "{host}" },
          { label: "Is an alias of", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "godaddy",
    label: "GoDaddy",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Name", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Value", template: "{target}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Service", template: "{service}" },
          { label: "Protocol", template: "{protocol}" },
          { label: "Name", template: "{srvhost}" },
          { label: "Value", template: "{target}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Name", template: "{host}" },
          { label: "Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Name", template: "{host}" },
          { label: "Value", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "hover",
    label: "Hover",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Hostname", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Mail Server", template: "{target}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Service", template: "{service}" },
          { label: "Protocol", template: "{protocol}" },
          { label: "Subdomain", template: "{srvsubhost}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
          { label: "Server", template: "{target}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Hostname", template: "{host}" },
          { label: "Content", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Hostname", template: "{host}" },
          { label: "Target Name", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "ionos",
    label: "IONOS",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Host name", template: "{host}" },
          { label: "Points to", template: "{target}" },
          { label: "Priority", template: "{priority}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Service", template: "{service}" },
          { label: "Protocol", template: "TCP" },
          { label: "Host name", template: "{srvhost}" },
          { label: "Points to", template: "{target}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Host name", template: "{host}" },
          { label: "Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Hostname", template: "{host}" },
          { label: "Point to", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "metanet-plesk",
    label: "METANET (Plesk)",
    records: {
      MX: {
        fields: [
          { label: "Eintragstyp (Type)", template: "MX" },
          { label: "Domainname (Host)", template: "{subhost}" },
          { label: "Priorität (Priority)", template: "{priority}" },
          { label: "Mail-Exchange-Server (Target)", template: "{target}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Eintragstyp (Type)", template: "SRV" },
          { label: "Service-Name (Service)", template: "{bareservice}" },
          { label: "Protokoll (Protocol)", template: "{bareprotocol}" },
          { label: "Domainname (Host)", template: "{srvsubhost}" },
          { label: "Priorität (Priority)", template: "{priority}" },
          { label: "Relative Gewichtung (Weight)", template: "niedrig (0)" },
          { label: "Zielhost (Target host)", template: "{target}" },
          { label: "Zielport (Target port)", template: "{port}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Eintragstyp (Type)", template: "TXT" },
          { label: "Domainname (Host)", template: "{subhost}" },
          { label: "TXT-Eintrag (TXT value)", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Eintragstyp (Type)", template: "CNAME" },
          { label: "Domainname (Host)", template: "{subhost}" },
          { label: "Kanonischer Name (Target)", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "namecheap",
    label: "Namecheap",
    records: {
      MX: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Mail Server", template: "{target}" },
          { label: "Priority", template: "{priority}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Service", template: "{service}" },
          { label: "Protocol", template: "{protocol}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
          { label: "Target", template: "{target}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Target", template: "{value}   (no trailing dot)" },
        ],
      },
    },
  },
  {
    id: "ovh",
    label: "OVH",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Sub-domain", template: "{subhost}" },
          { label: "Priority", template: "{priority}" },
          { label: "Target", template: "{target}." },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Sub-domain", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
          { label: "Target", template: "{target}." },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Sub-domain", template: "{subhost}" },
          { label: "Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Sub-domain", template: "{host}" },
          { label: "Target", template: "{target}." },
        ],
      },
    },
  },
  {
    id: "porkbun",
    label: "Porkbun",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Host", template: "{subhost}" },
          { label: "Priority", template: "{priority}" },
          { label: "Answer", template: "{target}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Host", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Answer", template: "{value}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Host", template: "{subhost}" },
          { label: "Answer", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Host", template: "{subhost}" },
          { label: "Target", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "spaceship",
    label: "Spaceship",
    records: {
      MX: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Type", template: "MX" },
          { label: "Value", template: "{target}" },
          { label: "Priority", template: "{priority}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Type", template: "SRV" },
          { label: "Priority", template: "{priority}" },
          { label: "Weight", template: "{weight}" },
          { label: "Port", template: "{port}" },
          { label: "Target", template: "{target}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Type", template: "TXT" },
          { label: "Value", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Host", template: "{host}" },
          { label: "Type", template: "CNAME" },
          { label: "Value", template: "{target}" },
        ],
      },
    },
  },
  {
    id: "squarespace",
    label: "Squarespace",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Name", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Data", template: "{target}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Name", template: "{host}" },
          { label: "Priority", template: "{priority}" },
          { label: "Data", template: "{value}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Name", template: "{host}" },
          { label: "Data", template: "{value}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Name", template: "{host}" },
          { label: "Data", template: "{value}" },
        ],
      },
    },
  },
  {
    id: "generic",
    label: "Other",
    records: {
      MX: {
        fields: [
          { label: "Type", template: "MX" },
          { label: "Name", template: "{fqdn}" },
          { label: "Value", template: "{match}" },
          { label: "Priority", template: "{priority}" },
        ],
      },
      SRV: {
        fields: [
          { label: "Type", template: "SRV" },
          { label: "Name", template: "{fqdn}" },
          { label: "Value", template: "{match}" },
          { label: "Priority", template: "{priority}" },
        ],
      },
      TXT: {
        fields: [
          { label: "Type", template: "TXT" },
          { label: "Name", template: "{fqdn}" },
          { label: "Value", template: "{match}" },
        ],
      },
      CNAME: {
        fields: [
          { label: "Type", template: "CNAME" },
          { label: "Name", template: "{fqdn}" },
          { label: "Value", template: "{match}" },
        ],
      },
    },
  },
];
