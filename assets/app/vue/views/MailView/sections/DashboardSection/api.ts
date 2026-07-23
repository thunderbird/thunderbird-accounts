export const getDesktopConnectToken = async () => {
  const response = await fetch('/desktop-connect/token', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  return await response.json();
};
