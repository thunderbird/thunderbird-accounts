export const getSubscriptionPortalLink = async () => {
  const response = await fetch('/api/v1/subscription/paddle/portal', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  return await response.json();
}

export const getSubscriptionPlanInfo = async () => {
  const response = await fetch('/api/v1/subscription/plan/info', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  return await response.json();
}
