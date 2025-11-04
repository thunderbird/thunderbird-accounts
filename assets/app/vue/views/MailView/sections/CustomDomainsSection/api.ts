export const addCustomDomain = async (domainName: string) => {
  const response = await fetch(`/custom-domains/add`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'domain-name': domainName }),
  });

  return await response.json();
};

export const getRemoteDNSRecords = async (domainName: string) => {
  const response = await fetch(`/custom-domains/dns-records?domain-name=${domainName}`);
  return await response.json();
};

export const verifyDomain = async (domainName: string) => {
  const response = await fetch(`/custom-domains/verify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'domain-name': domainName }),
  });

  return await response.json();
};

export const removeCustomDomain = async (domainName: string) => {
  const response = await fetch(`/custom-domains/remove`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'domain-name': domainName }),
  });
  return await response.json();
};
