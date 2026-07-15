import { useAuthFetch } from "@/composables/useFetch";

export const addCustomDomain = async (domainName: string) => {
  const { response } = await useAuthFetch(`/custom-domains/add`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'domain-name': domainName }),
  });

  return await response.value.json();
};

export const getRemoteDNSRecords = async (domainName: string) => {
  const { response } = await useAuthFetch(`/custom-domains/dns-records?domain-name=${domainName}`);
  return await response.value.json();
};

export const verifyDomain = async (domainName: string) => {
  const { response } = await useAuthFetch(`/custom-domains/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'domain-name': domainName }),
  });

  return await response.value.json();
};

export const removeCustomDomain = async (domainName: string) => {
  const { response } = await useAuthFetch(`/custom-domains/remove`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'domain-name': domainName }),
  });
  return await response.value.json();
};
