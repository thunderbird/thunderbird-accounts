import { createFetch } from "@vueuse/core"

//const { isFetching, error, data } = useMyFetch('users')
export const useAuthFetch = createFetch({
  options: {
    async beforeFetch(ctx) {
      // If we don't explicitly set an accept header, make sure it's set to application/json
      if (!ctx.options?.headers['Accept']) {
        ctx.options.headers['Accept'] = 'application/json';
      }
      return ctx;
    },
    async onFetchError(ctx) {
      // Try and handle reauth responses (this happens if the refresh token is also invalid.)
      try {
        const data = JSON.parse(ctx.data);
        // If it's a 403 we need to ship them to auth
        if (ctx.response.status === 403 && data?.type === 'auth_error') {
          if (data?.refresh_url) {
            window.location = data?.refresh_url;
            return ctx;
          }
        }
      } catch {
        // ...
      } 

      return ctx;
    },
  },
  fetchOptions: {
    mode: 'cors',
  },
});
