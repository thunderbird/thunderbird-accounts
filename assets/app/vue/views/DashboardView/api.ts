import { useAuthFetch } from "@/composables/useFetch";

export const getSubscriptionPortalLink = async () => {
  const { response } = await useAuthFetch('/api/v1/subscription/paddle/portal/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  return await response.value.json();
}

export const getSubscriptionPlanInfo = async () => {
  const { response } = await useAuthFetch('/api/v1/subscription/plan/info/', {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': window._page?.csrfToken,
    },
  });

  // If we're not getting a application/json response then return the status text
  if (!response.value.headers.get('content-type')?.includes('application/json')) {
    throw new Error(response.value.statusText);
  }

  return await response.value.json();
}
