import { ref, type Ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { MfaReauthenticationRequiredError } from './api';

interface RunOptions {
  /** i18n key for the message shown when the failure isn't an Error with a usable message. */
  fallbackErrorKey: string;
  /** Called when the action triggers an OIDC step-up (403 with a reauth URL). */
  onReauthRequired: (reauthUrl: string) => void;
  /** Drive a caller-owned loading flag (e.g. a dedicated `isRemoving`) instead of the shared one. */
  loadingRef?: Ref<boolean>;
}

/**
 * Shared loading/error/step-up handling for MFA API calls. Owns `isLoading` and
 * `errorMessage`, and `run` wraps an async action so the reauth handoff and error mapping
 * live in one place instead of being copy-pasted across every modal and flow.
 *
 * `run` resolves to the action's value on success, or `undefined` when it errored or
 * triggered a step-up, so callers branch with a simple `if (!result) return;`.
 */
export function useMfaAction() {
  const { t } = useI18n();
  const isLoading = ref(false);
  const errorMessage = ref('');

  const run = async <T>(
    action: () => Promise<T>,
    { fallbackErrorKey, onReauthRequired, loadingRef }: RunOptions,
  ): Promise<T | undefined> => {
    const loading = loadingRef ?? isLoading;
    if (loading.value) return undefined;

    loading.value = true;
    errorMessage.value = '';

    try {
      return await action();
    } catch (error) {
      if (error instanceof MfaReauthenticationRequiredError) {
        onReauthRequired(error.reauthUrl);
        return undefined;
      }

      errorMessage.value = error instanceof Error ? error.message : t(fallbackErrorKey);
      return undefined;
    } finally {
      loading.value = false;
    }
  };

  return { isLoading, errorMessage, run };
}
