<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhCheckCircle } from '@phosphor-icons/vue';
import { BaseBadge, BaseBadgeTypes, VisualDivider, PrimaryButton, LinkButton } from '@thunderbirdops/services-ui';

const { t } = useI18n();

interface AuthenticationMethodData {
  set: boolean;
  setupDate?: string;
  lastUsedDate?: string;
  phoneNumber?: string;
  emailAddress?: string;
}

const authenticationMethods: Record<string, AuthenticationMethodData> = {
  authenticatorApp: {
    set: true,
    setupDate: '2025-01-13 09:32',
    lastUsedDate: '2025-06-23 17:28'
  },
  recoveryPhoneNumber: {
    set: false,
  },
  recoveryEmailAddress: {
    set: true,
    setupDate: '2025-01-13 09:32',
    lastUsedDate: '2025-06-23 17:28',
    emailAddress: 'te***@domain.example'
  }
}

const authenticationMethodEntries = computed(() => Object.entries(authenticationMethods));
</script>

<template>
  <div class="authentication-methods-container">
    <header>{{ t('views.manageMfa.authenticationMethods') }}</header>

    <div class="authentication-methods-content">
      <template v-for="([method, methodData], index) in authenticationMethodEntries" :key="method">
        <div class="authentication-method">
          <div class="authentication-method-content">
            <div class="authentication-method-header">
              <h3>{{ t(`views.manageMfa.${method}.title`) }}</h3>
    
              <base-badge :type="methodData.set ? BaseBadgeTypes.Set : BaseBadgeTypes.NotSet">
                {{ methodData.set ? t('views.manageMfa.states.set') : t('views.manageMfa.states.notSet') }}
    
                <template #icon v-if="methodData.set">
                  <PhCheckCircle size="16" weight="fill" />
                </template>
              </base-badge>
            </div>
  
            <p :class="{ 'block-margin': methodData.set }">
              {{ t(`views.manageMfa.${method}.description.${methodData.set ? 'set' : 'notSet'}`,
                { phoneNumber: methodData?.phoneNumber, emailAddress: methodData?.emailAddress }) }}
            </p>

            <template v-if="methodData.set">
              <p class="authentication-method-details">
                {{ t('views.manageMfa.setupDate') }}: {{ methodData.setupDate }} | {{ t('views.manageMfa.lastUsedDate') }}: {{ methodData.lastUsedDate }}
              </p>
            </template>
          </div>

          <div class="authentication-method-actions">
            <template v-if="methodData.set">
              <primary-button variant="outline" size="small">
                {{ t('views.manageMfa.actions.edit') }}
              </primary-button>
              <link-button size="small">
                {{ t('views.manageMfa.actions.remove') }}
              </link-button>
            </template>
            <template v-else>
              <primary-button variant="outline" size="small">
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