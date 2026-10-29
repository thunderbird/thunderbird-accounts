import { useAuthFetch } from '@/composables/useFetch';
import { DNS_PROVIDERS } from './dnsProviders';

// The requests are shared with the inline flow in the email settings, so they live in a single place.
// TODO: We should move this over when we remove the custom-domains-revamp feature flag
export {
  addCustomDomain,
  getRemoteDNSRecords,
  verifyDomain,
  removeCustomDomain,
} from '../SettingsView/sections/EmailSettingsSection/CustomDomainsSection/api';

// The outcome of the last verification attempt, which runs in the background
export const getVerificationResult = async (domainName: string) => {
  const { response } = await useAuthFetch(
    `/custom-domains/verification-result?domain-name=${encodeURIComponent(domainName)}`
  );
  return await response.value.json();
};

export type DnsProviderOption = {
  label: string;
  value: string;
};

// The providers we have instructions for, ready for a select input
export const getDnsProviders = (): DnsProviderOption[] =>
  DNS_PROVIDERS.map((provider) => ({ label: provider.label, value: provider.id }));
