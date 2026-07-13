<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PrimaryButton, TextInput, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';

defineProps<{
  customDomain: string | null;
  customDomainError: string | null;
  domainAlreadyConfigured: boolean;
  isAddingCustomDomain: boolean;
}>();

const emit = defineEmits<{
  submit: [];
  'update:customDomain': [value: string | null];
}>();

const { t } = useI18n();
</script>

<template>
  <form @submit.prevent="emit('submit')">
    <text-input
      :placeholder="t('views.mail.sections.customDomains.domainPlaceholder')"
      name="custom-domain"
      :help="t('views.mail.sections.customDomains.domainHelp')"
      :error="customDomainError"
      class="custom-domain-text-input"
      :model-value="customDomain"
      @update:model-value="emit('update:customDomain', $event)"
    >
      {{ t('views.mail.sections.customDomains.enterCustomDomain') }}
    </text-input>

    <notice-bar
      :type="NoticeBarTypes.Critical"
      v-if="domainAlreadyConfigured"
      class="domain-already-configured-notice-bar"
    >
      <i18n-t keypath="views.mail.sections.customDomains.domainAlreadyConfigured" tag="span">
        <template #link>
          <router-link to="/contact">{{ t('views.mail.sections.customDomains.reachOutToSupport') }}</router-link>
        </template>
      </i18n-t>
    </notice-bar>

    <primary-button variant="outline" @click="emit('submit')" :disabled="isAddingCustomDomain">
      {{ t('views.mail.sections.customDomains.continue') }}
    </primary-button>
  </form>
</template>

<style scoped>
.custom-domain-text-input {
  margin-block-end: 1.5rem;
}

.domain-already-configured-notice-bar {
  margin-block-end: 1.5rem;

  a {
    color: var(--colour-ti-secondary);
  }
}

@media (min-width: 768px) {
  .custom-domain-text-input {
    max-width: 50%;
  }

  .domain-already-configured-notice-bar {
    max-width: 50%;
  }
}
</style>
