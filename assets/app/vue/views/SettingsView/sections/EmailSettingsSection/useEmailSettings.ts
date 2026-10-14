import { ref } from 'vue';
import type { Ref } from 'vue';
import type { CustomDomain } from './CustomDomainsSection/types';

let emailAddresses: Ref<string[]> | null = null;
let customDomains: Ref<CustomDomain[]> | null = null;

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

  return { emailAddresses, customDomains, aliasesForDomain, addAlias, removeAlias, removeAliasesForDomain };
};
