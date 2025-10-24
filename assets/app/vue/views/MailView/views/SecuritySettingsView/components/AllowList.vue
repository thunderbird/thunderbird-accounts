<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhShieldCheck, PhX } from '@phosphor-icons/vue';
import { PrimaryButton, TextInput, LinkButton, NoticeBar, NoticeBarTypes } from '@thunderbirdops/services-ui';
import DetailsSummary from '@/components/DetailsSummary.vue';

const { t } = useI18n();

const allowListItems = ref([
  { id: 1, email: '@thunderblog.net' },
  { id: 2, email: '@UXdesignnewsblog.com' },
  { id: 3, email: '@a11ynewsblog.com' },
  { id: 4, email: '@thunderbirdproservices.com' },
  { id: 5, email: '@Fabriclandnews.ca' },
  { id: 6, email: 'sol@otherdomain.example' },
]);

const isManagingAllowList = ref(false);
const recentlyRemovedItem = ref<typeof allowListItems.value[number] | null>(null);
const emailOrDomainText = ref(null);

const onAddToAllowList = () => {
  allowListItems.value.push({ id: allowListItems.value.length + 1, email: emailOrDomainText.value });
  emailOrDomainText.value = null;
};

const onSaveAllowList = () => {
  isManagingAllowList.value = false;
};

const onRemoveFromAllowList = (id: number) => {
  recentlyRemovedItem.value = allowListItems.value.find(item => item.id === id);
  allowListItems.value = allowListItems.value.filter(item => item.id !== id);
};

const onUndoRemoveFromAllowList = () => {
  allowListItems.value.push(recentlyRemovedItem.value);
  recentlyRemovedItem.value = null;
};

const onShowMore = () => {
  // TODO: Implement show more logic
};
</script>

<template>
  <details-summary :title="t('views.mail.views.securitySettings.allowList')" :expandable="false" default-open>
    <template #icon>
      <ph-shield-check size="24" />
    </template>

    <p>{{ t('views.mail.views.securitySettings.allowListDescription') }}</p>

    <notice-bar :type="NoticeBarTypes.Success" class="recently-removed-item-notice-bar" v-if="recentlyRemovedItem">
      <p>{{ t('views.mail.views.securitySettings.removedSuccessfully', { email: recentlyRemovedItem.email }) }}</p>

      <template #cta>
        <link-button size="small" class="undo-remove-from-allow-list-button" @click="onUndoRemoveFromAllowList">
          {{ t('views.mail.views.securitySettings.undo') }}
        </link-button>
      </template>
    </notice-bar>

    <div class="allow-list-items-wrapper">
      <div class="allow-list-item" v-for="item in allowListItems" :key="item.id">
        <p>{{ item.email }}</p>

        <button class="remove-from-allow-list-button" @click="onRemoveFromAllowList(item.id)" v-show="isManagingAllowList">
          <ph-x size="16" />
        </button>
      </div>

      <link-button size="small" class="show-more-button" @click="onShowMore">
        {{ t('views.mail.views.securitySettings.showMore') }}
      </link-button>
    </div>

    <template v-if="isManagingAllowList">
      <div class="manage-allow-list-form-wrapper">
        <text-input
          name="email-or-domain"
          :placeholder="t('views.mail.views.securitySettings.manageAllowListPlaceholder')"
          :help="t('views.mail.views.securitySettings.manageAllowListHelperText')"
          v-model="emailOrDomainText"
        >
          {{ t('views.mail.views.securitySettings.manageAllowListLabel') }}
        </text-input>

        <link-button size="small" class="add-to-allow-list-button" @click="onAddToAllowList" :disabled="!emailOrDomainText">
          {{ t('views.mail.views.securitySettings.addToAllowList') }}
        </link-button>

        <primary-button class="save-allow-list-button" @click="onSaveAllowList">
          {{ t('views.mail.views.securitySettings.save') }}
        </primary-button>
      </div>
    </template>
    <template v-else>
      <div class="manage-allow-list-button-wrapper">
        <primary-button variant="outline" class="manage-allow-list-button" @click="isManagingAllowList = true">
          {{ t('views.mail.views.securitySettings.manageAllowList') }}
        </primary-button>
      </div>
    </template>
  </details-summary>
</template>

<style scoped>
p {
  color: var(--colour-ti-secondary);
  line-height: 1.32;
  margin-block-end: 1rem;

  &:not(:has(~ .recently-removed-item-notice-bar)) {
    margin-block-end: 1.5rem;
  }
}

/* Overriding the link button styles */
:deep(.show-more-button > span.text) {
  font-size: 0.75rem;
}

:deep(.add-to-allow-list-button > span.text) {
  font-size: 0.75rem;
}

:deep(.undo-remove-from-allow-list-button.base.link.small.filled) {
  color: var(--colour-ti-secondary);
  text-transform: lowercase;
}

.recently-removed-item-notice-bar {
  margin-block-end: 1rem;
  word-break: break-all;

  p {
    margin-block-end: 0;
  }
}

.allow-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0.5rem;
  border-block-end: 1px solid var(--colour-neutral-border);
  word-break: break-all;

  p {
    font-size: 0.75rem;
    line-height: normal;
    margin-block-end: 0;
    height: 1rem;
  }

  &:nth-child(odd) {
    background-color: var(--colour-neutral-lower);
  }

  .remove-from-allow-list-button {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    color: var(--colour-ti-base);
    width: 1rem;
    height: 1rem;
  }
}

.allow-list-items-wrapper {
  overflow-x: auto;
  padding: 0.25rem;
  margin: -0.25rem;
  margin-block-end: 1rem;

  .show-more-button {
    margin-block-start: 0.55rem;
  }
}

.manage-allow-list-form-wrapper {
  .add-to-allow-list-button {
    margin-block-end: 1.5rem;
  }

  .save-allow-list-button {
    width: 128px;
  }
}

.manage-allow-list-button-wrapper {
  display: flex;
  justify-content: flex-end;
}

@media (min-width: 768px) {
  .manage-allow-list-form-wrapper {
    max-width: 50%;
  }
}
</style>