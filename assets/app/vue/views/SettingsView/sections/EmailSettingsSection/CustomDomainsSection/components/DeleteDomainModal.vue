<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { BaseButton, CheckboxInput, DangerButton, ModalDialog, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';

// API
import { removeCustomDomain } from '../api';

const emit = defineEmits<{
  'custom-domain-removed': [domainName: string];
}>();

const { t } = useI18n();

const modal = useTemplateRef<InstanceType<typeof ModalDialog>>('modal');
const domainName = ref('');
const aliases = ref<string[]>([]);
const confirmedAliases = ref<Record<string, boolean>>({});
const isDeleting = ref(false);
const errorMessage = ref<string | null>(null);

const allAliasesConfirmed = computed(() => aliases.value.every((alias) => confirmedAliases.value[alias]));

const show = (name: string) => {
  domainName.value = name;
  aliases.value = (window._page?.emailAddresses ?? []).filter((email: string) =>
    email.toLowerCase().endsWith(`@${name.toLowerCase()}`)
  );
  confirmedAliases.value = {};
  errorMessage.value = null;
  modal.value?.show();
};

const hide = () => modal.value?.hide();

const handleDelete = async () => {
  isDeleting.value = true;
  errorMessage.value = null;

  try {
    const data = await removeCustomDomain(domainName.value);
    if (data.success) {
      emit('custom-domain-removed', domainName.value);
      hide();
    } else {
      errorMessage.value = data.error;
    }
  } catch (error) {
    errorMessage.value = String(error);
  } finally {
    isDeleting.value = false;
  }
};

defineExpose({ show, hide });
</script>

<template>
  <modal-dialog ref="modal">
    <template #header>
      {{ t('views.mail.sections.customDomains.deleteModal.title') }}
    </template>

    <p v-if="aliases.length > 0" class="delete-domain-description">
      <i18n-t keypath="views.mail.sections.customDomains.deleteModal.description" tag="span" scope="global">
        <template #domain><strong>{{ domainName }}</strong></template>
        <template #count>{{ aliases.length }}</template>
      </i18n-t>
    </p>
    <p v-else class="delete-domain-description">
      <i18n-t keypath="views.mail.sections.customDomains.deleteModal.descriptionNoAliases" tag="span" scope="global">
        <template #domain><strong>{{ domainName }}</strong></template>
      </i18n-t>
    </p>

    <notice-bar v-if="errorMessage" :type="NoticeBarTypes.Critical" class="delete-domain-error">
      <p>{{ errorMessage }}</p>
    </notice-bar>

    <template v-if="aliases.length > 0">
      <h3 class="existing-aliases-heading">{{ t('views.mail.sections.customDomains.deleteModal.existingAliases') }}</h3>
      <div class="aliases-checkboxes">
        <checkbox-input
          v-for="alias in aliases"
          :key="alias"
          :name="`delete-alias-${alias}`"
          :label="alias"
          v-model="confirmedAliases[alias]"
          :disabled="isDeleting"
        />
      </div>
    </template>

    <template #actions>
      <base-button :disabled="isDeleting" @click="hide" variant="outline">
        {{ t('views.mail.sections.customDomains.deleteModal.cancel') }}
      </base-button>
      <danger-button :disabled="isDeleting || !allAliasesConfirmed" @click="handleDelete">
        {{ t('views.mail.sections.customDomains.deleteModal.confirm') }}
      </danger-button>
    </template>
  </modal-dialog>
</template>

<style scoped>
.delete-domain-description {
  margin-block-end: 1.5rem;
}

.delete-domain-error {
  margin-block-end: 1.5rem;

  p {
    margin-block-end: 0;
  }
}

.existing-aliases-heading {
  font-size: 1rem;
  margin-block-end: 1rem;
}

.aliases-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
