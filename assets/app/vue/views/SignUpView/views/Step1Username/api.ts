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
    return { success: true, error: null };
  } else if (response.status === 429) { // Throttled
    return { success: false, error: (await response.json())['detail'] || false };
  }

  return { success: false, error: (await response.json())['0'] || false };
}
