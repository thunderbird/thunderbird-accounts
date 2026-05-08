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
              {{ t(`views.manageMfa.${method}.description.${methodData.set ? 'set' : 'notSet'}`) }}
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
              <primary-button :data-testid="`mfa-${method}-edit-button`" variant="outline" size="small" @click="openMethodModal(method)">
                {{ t('views.manageMfa.actions.edit') }}
              </primary-button>
              <link-button :data-testid="`mfa-${method}-remove-button`" size="small" @click="beginRemove(method, methodData)">
                {{ t('views.manageMfa.actions.remove') }}
              </link-button>
            </template>
            <template v-else>
              <primary-button :data-testid="`mfa-${method}-setup-button`" variant="outline" size="small" @click="openMethodModal(method)">
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
      grid-template-columns: auto 15%;
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

        button.link {
          color: var(--colour-ti-secondary);
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
