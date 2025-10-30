export const addEmailAlias = async (emailAlias: string, domain: string) => {
  const response = await fetch(`/email-aliases/add`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'email-alias': emailAlias, 'domain': domain }),
  });

  return await response.json();
};

export const removeEmailAlias = async (emailAlias: string) => {
  const response = await fetch(`/email-aliases/remove`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page.csrfToken,
    },
    body: JSON.stringify({ 'email-alias': emailAlias }),
  });

  return await response.json();
};
