export const isUsernameAvailable = async (username: string) => {
  const response = await fetch('/api/v1/mail/is-username-available/', {
    method: 'POST',
    body: JSON.stringify({
      'username': username,
    }),
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  if (response.status === 200) {
    return true;
  } else if (response.status === 429) { // Throttled
    return (await response.json())['detail'] || false;
  }

  return (await response.json())['0'] || false;
}
