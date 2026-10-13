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

// TODO: Replace with the real list of DNS providers
export const getDnsProviders = (): DnsProviderOption[] => [
  { label: 'Provider One', value: 'provider-one' },
  { label: 'Provider Two', value: 'provider-two' },
  { label: 'Other', value: 'other' },
];
