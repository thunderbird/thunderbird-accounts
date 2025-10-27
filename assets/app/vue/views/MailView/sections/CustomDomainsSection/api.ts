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

export const getDNSRecords = async (domainName: string) => {
  const response = await fetch(`/custom-domains/dns-records?domain-name=${domainName}`);
  return await response.json();
};
