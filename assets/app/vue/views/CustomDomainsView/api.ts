import { DNS_PROVIDERS } from './dnsProviders.generated';

// The requests are shared with the inline flow in the email settings, so they live in a single place.
// TODO: We should move this over when we remove the custom-domains-revamp feature flag
export {
  addCustomDomain,
  getRemoteDNSRecords,
  verifyDomain,
  removeCustomDomain,
} from '../SettingsView/sections/EmailSettingsSection/CustomDomainsSection/api';

export type DnsProviderOption = {
  label: string;
  value: string;
};

// The providers we have instructions for, ready for a select input
export const getDnsProviders = (): DnsProviderOption[] =>
  DNS_PROVIDERS.map((provider) => ({ label: provider.label, value: provider.id }));
