export const isEmailInAllowList = async (email: string) => {
  const response = await fetch('/api/v1/contact/check-email-is-on-allow-list/', {
    method: 'POST',
    body: JSON.stringify({
      email,
    }),
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });
  
  return await response.json();
}