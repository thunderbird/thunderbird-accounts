export const deleteAccount = async (password: string) => {
  const response = await fetch('/delete-account', {
    method: 'DELETE',
    headers: {
      'X-CSRFToken': window._page.csrfToken,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ password }),
  });

  return await response.json();
};
