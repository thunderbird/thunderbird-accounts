type KeycloakWindow = Window & {
  stopKeycloakSessionPolling?: () => void;
};

export function submitKeycloakForm(form?: HTMLFormElement | null) {
  (window as KeycloakWindow).stopKeycloakSessionPolling?.();
  form?.submit();
}
