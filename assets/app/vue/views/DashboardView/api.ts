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

export const getAppleMailQrCode = async (): Promise<string> => {
  const response = await fetch('/apple-mail/qr', { credentials: 'same-origin' });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const svgText = await response.text();

  return `data:image/svg+xml,${encodeURIComponent(svgText)}`;
}

export const getSubscriptionPlanInfo = async () => {
  const response = await fetch('/api/v1/subscription/plan/info/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  return await response.json();
}
