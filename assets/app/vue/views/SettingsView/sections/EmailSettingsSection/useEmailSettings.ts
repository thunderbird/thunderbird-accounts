import { ref } from 'vue';
import type { Ref } from 'vue';
import { listCustomDomains } from './CustomDomainsSection/api';
import type { CustomDomain } from './CustomDomainsSection/types';

let emailAddresses: Ref<string[]> | null = null;
let customDomains: Ref<CustomDomain[]> | null = null;
let customDomainsExpandRequested = false;

const endsWithDomain = (email: string, domainName: string) =>
  email.toLowerCase().endsWith(`@${domainName.toLowerCase()}`);

export const useEmailSettings = () => {
  if (!emailAddresses || !customDomains) {
    emailAddresses = ref<string[]>([...(window._page?.emailAddresses ?? [])]);
    customDomains = ref<CustomDomain[]>([...(window._page?.customDomains ?? [])]);
  }

  const aliasesForDomain = (domainName: string) =>
    emailAddresses.value.filter((email) => endsWithDomain(email, domainName));

  const addAlias = (email: string) => {
    emailAddresses.value.push(email);
  };

  const removeAlias = (email: string) => {
    emailAddresses.value = emailAddresses.value.filter((item) => item !== email);
  };

  const removeAliasesForDomain = (domainName: string) => {
    emailAddresses.value = emailAddresses.value.filter((email) => !endsWithDomain(email, domainName));
  };

  // The page data is only a snapshot from load time, so domains added since then need to be fetched
  const refreshCustomDomains = async () => {
    try {
      customDomains.value = await listCustomDomains();
    } catch (e) {
      console.error(e);
    }
  };

  const requestCustomDomainsExpanded = () => {
    customDomainsExpandRequested = true;
  };

  // One-shot, so the section only opens for the visit that asked for it
  const consumeCustomDomainsExpandRequest = () => {
    const requested = customDomainsExpandRequested;
    customDomainsExpandRequested = false;
    return requested;
  };

  return {
    emailAddresses,
    customDomains,
    refreshCustomDomains,
    requestCustomDomainsExpanded,
    consumeCustomDomainsExpandRequest,     aliasesForDomain,
    addAlias,
    removeAlias,
    removeAliasesForDomain,
  };
};
