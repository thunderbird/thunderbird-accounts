<script setup lang="ts">
import { onMounted, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCheckCircle } from '@phosphor-icons/vue';
import { BaseBadge, BaseBadgeTypes, VisualDivider, PrimaryButton, LinkButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';

// Modals
import ManageAuthenticatorAppModal from './ManageAuthenticatorAppModal.vue';
import ManageRecoveryCodesModal from './ManageRecoveryCodesModal.vue';
import VerifyYourIdentityModal from './VerifyYourIdentityModal.vue';
import RemoveMfaMethodModal from './RemoveMfaMethodModal.vue';

import { AUTHENTICATION_METHODS, useMfaMethods } from '../useMfaMethods';

const { t } = useI18n();

const manageAuthenticatorAppModal = useTemplateRef<InstanceType<typeof ManageAuthenticatorAppModal>>('manageAuthenticatorAppModal');
const manageRecoveryCodesModal = useTemplateRef<InstanceType<typeof ManageRecoveryCodesModal>>('manageRecoveryCodesModal');
const verifyYourIdentityModal = useTemplateRef<InstanceType<typeof VerifyYourIdentityModal>>('verifyYourIdentityModal');
const removeMfaMethodModal = useTemplateRef<InstanceType<typeof RemoveMfaMethodModal>>('removeMfaMethodModal');

const {
  authenticationMethods,
  authenticationMethodEntries,
  isLoading,
  errorMessage,
  reauthenticationUrl,
  isRemoving,
  removeModalTitle,
  removeModalDescription,
  loadMfaMethods,
  setRecoveryCodesCredentials,
  handleAuthenticatorConfigured,
  requestMfaVerification,
  beginRemove,
  confirmRemove,
  cancelRemove,
  clearPendingRemove,
} = useMfaMethods({
  openVerifyModal: () => verifyYourIdentityModal.value?.open(),
  openRecoveryCodesModal: () => manageRecoveryCodesModal.value?.open(),
  openRemoveModal: () => removeMfaMethodModal.value?.open(),
  closeRemoveModal: () => removeMfaMethodModal.value?.close(),
});

// "Set up" and "Edit" open the same modal for a given method; editing recovery codes
// re-enters the confirm-then-regenerate flow.
const openMethodModal = (method: string) => {
  if (method === AUTHENTICATION_METHODS.AUTHENTICATOR_APP) {
    manageAuthenticatorAppModal.value.open();
  } else if (method === AUTHENTICATION_METHODS.RECOVERY_CODES) {
    manageRecoveryCodesModal.value.open();
  }
};

// The authenticator app cannot be edited in place: registration is enrollment-only on
// the Keycloak side (replacing an authenticator with a bearer token alone is the
// "someone else's bike lock" attack). Re-enrollment is Remove, then Set up. Recovery
// codes keep Edit since regenerating them is the whole operation (step-up gated).
const isEditable = (method: string) => method !== AUTHENTICATION_METHODS.AUTHENTICATOR_APP;

// Recovery codes don't get "edited" — the action regenerates them — so label it
// accordingly. Other editable methods keep the generic "Edit".
const editLabel = (method: string) =>
  method === AUTHENTICATION_METHODS.RECOVERY_CODES
    ? t('views.manageMfa.actions.regenerate')
    : t('views.manageMfa.actions.edit');

// Recovery codes are strictly a backup for the authenticator app, never a standalone
// factor (Keycloak deletes the credential once the last code is spent, leaving the
// account unprotected) — so they can't be set up until an authenticator exists.
const isSetupDisabled = (method: string) =>
  method === AUTHENTICATION_METHODS.RECOVERY_CODES
  && !authenticationMethods.value[AUTHENTICATION_METHODS.AUTHENTICATOR_APP].set;

const methodDescription = (method: string, isSet: boolean) => {
  if (!isSet && isSetupDisabled(method)) {
    return t('views.manageMfa.recoveryCodes.requiresAuthenticator');
  }
  return t(`views.manageMfa.${method}.description.${isSet ? 'set' : 'notSet'}`);
};

onMounted(loadMfaMethods);
</script>

<template>
  <div class="authentication-methods-container">
    <header>{{ t('views.manageMfa.authenticationMethods') }}</header>

    <div class="authentication-methods-content">
      <notice-bar :type="NoticeBarTypes.Critical" v-if="errorMessage">{{ errorMessage }}</notice-bar>
      <p v-if="isLoading">{{ t('views.manageMfa.loading') }}</p>

      <template v-for="([method, methodData], index) in authenticationMethodEntries" :key="method">
        <div class="authentication-method">
          <div class="authentication-method-content">
            <div class="authentication-method-header">
              <h3>{{ t(`views.manageMfa.${method}.title`) }}</h3>
    
              <base-badge :type="methodData.set ? BaseBadgeTypes.Set : BaseBadgeTypes.NotSet">
                {{ methodData.set ? t('views.manageMfa.states.set') : t('views.manageMfa.states.notSet') }}
    
                <template #icon v-if="methodData.set">
                  <ph-check-circle size="16" weight="fill" />
                </template>
              </base-badge>
            </div>
  
            <p :class="{ 'block-margin': methodData.set }">
              {{ methodDescription(method, methodData.set) }}
            </p>

            <template v-if="methodData.set && (methodData.setupDate || methodData.lastUsedDate)">
              <p class="authentication-method-details">
                <template v-if="methodData.setupDate">
                  {{ t('views.manageMfa.setupDate') }}: {{ methodData.setupDate }}
                </template>
                <template v-if="methodData.lastUsedDate">
                  | {{ t('views.manageMfa.lastUsedDate') }}: {{ methodData.lastUsedDate }}
                </template>
              </p>
            </template>

            <template v-if="method === AUTHENTICATION_METHODS.RECOVERY_CODES && methodData.set && typeof methodData.totalCodes === 'number'">
              <p class="authentication-method-details">
                {{ t('views.manageMfa.remainingCodes', { remaining: methodData.remainingCodes ?? 0, total: methodData.totalCodes }) }}
              </p>
            </template>
          </div>

          <div class="authentication-method-actions">
            <template v-if="methodData.set">
              <!-- When a method has an Edit action, Remove sits beneath it as a subtle
                   underlined link (matches the designs). When there's no Edit (e.g. the
                   authenticator app, which is enrollment-only), a lone underlined link
                   looks out of place, so Remove takes the same outline-button style Edit
                   would have used. -->
              <template v-if="isEditable(method)">
                <primary-button :data-testid="`mfa-${method}-edit-button`" variant="outline" size="small" @click="openMethodModal(method)">
                  {{ editLabel(method) }}
                </primary-button>
                <link-button :data-testid="`mfa-${method}-remove-button`" size="small" @click="beginRemove(method, methodData)">
                  {{ t('views.manageMfa.actions.remove') }}
                </link-button>
              </template>
              <primary-button v-else :data-testid="`mfa-${method}-remove-button`" variant="outline" size="small" @click="beginRemove(method, methodData)">
                {{ t('views.manageMfa.actions.remove') }}
              </primary-button>
            </template>
            <template v-else>
              <primary-button :data-testid="`mfa-${method}-setup-button`" variant="outline" size="small" :disabled="isSetupDisabled(method)" @click="openMethodModal(method)">
                {{ t('views.manageMfa.actions.setUp') }}
              </primary-button>
            </template>
          </div>

          <visual-divider
            v-if="index < authenticationMethodEntries.length - 1"
            class="authentication-method-divider"
          />
        </div>
      </template>
    </div>
  </div>

  <!-- Modals -->
  <manage-authenticator-app-modal
    ref="manageAuthenticatorAppModal"
    @configured="handleAuthenticatorConfigured"
    @reauth-required="requestMfaVerification"
  />
  <manage-recovery-codes-modal
    ref="manageRecoveryCodesModal"
    @configured="setRecoveryCodesCredentials"
    @reauth-required="requestMfaVerification"
  />
  <verify-your-identity-modal
    ref="verifyYourIdentityModal"
    :reauth-url="reauthenticationUrl"
  />
  <remove-mfa-method-modal
    ref="removeMfaMethodModal"
    :title="removeModalTitle"
    :description="removeModalDescription"
    :is-removing="isRemoving"
    @confirm="confirmRemove"
    @cancel="cancelRemove"
    @close="clearPendingRemove"
  />
</template>

<style scoped>
.authentication-methods-container {
  border: 1px solid var(--colour-neutral-border);
  border-radius: 0.5rem;
  background-color: white;

  header {
    padding: 1rem 1.125rem;
    border-radius: 0.5rem 0.5rem 0 0;
    color: #eeeef0; /* TODO: --colour-ti-base forced dark */
    background-color: #262d3b; /* TODO: --colour-neutral-raised forced dark */
    font-size: 1.25rem;
    font-weight: 500;
  }

  .authentication-methods-content {
    padding: 1rem 1.5rem 2rem;
    border-radius: 0 0 0.5rem 0.5rem;

    .authentication-method {
      display: grid;
      /* Each method row is its own grid, so the actions column needs a shared fixed width
         (rather than auto) for the buttons to line up across rows. It's sized to fit the
         longest label ("Regenerate"); the content column takes the rest and may shrink
         (minmax 0) so it never pushes the buttons out. */
      grid-template-columns: minmax(0, 1fr) 6.5rem;
      column-gap: 2.5rem;
      color: var(--colour-ti-secondary);

      .authentication-method-header {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
        margin-block-end: 0.25rem;

        h3 {
          font-size: 1rem;
        }
      }

      .authentication-method-content {
        p {
          font-size: 0.875rem;
          line-height: 1.23;

          &.block-margin {
            margin-block-end: 1rem;
          }

          &.authentication-method-details {
            font-size: 0.75rem;
            line-height: normal;
            margin-block-end: 0;
          }
        }
      }

      .authentication-method-actions {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;

        button {
          /* Keep labels on a single line so they don't wrap inside the fixed-width column. */
          white-space: nowrap;
        }

        button.link {
          color: var(--colour-ti-secondary);
          /* The "small" button variant locks every button to a fixed 2rem height and
             vertically centers its label, which leaves the underlined Remove floating
             well below the Edit button. Collapse the link button to its own text height
             so Remove sits snugly beneath Edit. */
          height: auto;
          min-height: 0;
          padding-block: 0;
        }
      }

      .authentication-method-divider {
        grid-column: 1 / -1;
        margin-block: 1rem;
      }
    }
  }
}
</style>
