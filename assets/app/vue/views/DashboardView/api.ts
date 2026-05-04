export const getSubscriptionPortalLink = async () => {
  const response = await fetch('/api/v1/subscription/paddle/portal/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  return await response.json();
}

export const getSubscriptionPlanInfo = async () => {
  const response = await fetch('/api/v1/subscription/plan/info/', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  // If we're not getting a application/json response then return the status text
  if (!response.headers.get('content-type')?.includes('application/json')) {
    throw new Error(response.statusText);
  }

  return await response.json();
}
