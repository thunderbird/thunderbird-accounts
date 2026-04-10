<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { PrimaryButton } from '@thunderbirdops/services-ui';

const { t } = useI18n();

enum TOS_TABS {
  TOS = 'tos',
  PRIVACY = 'privacy',
}

const tosSelectedTab = ref<TOS_TABS>(TOS_TABS.TOS);
</script>

<template>
  <h1>{{ t('views.tosPrivacy.title') }}</h1>
  <p class="description">{{ t('views.tosPrivacy.description') }}</p>

  <div class="tabs">
    <button
      :class="{ 'active': tosSelectedTab === TOS_TABS.TOS }"
      class="tab"
      @click="tosSelectedTab = TOS_TABS.TOS"
    >
      {{ t('views.tosPrivacy.tosTab') }}
    </button>
    <button
      :class="{ 'active': tosSelectedTab === TOS_TABS.PRIVACY }"
      class="tab"
      @click="tosSelectedTab = TOS_TABS.PRIVACY"
    >
      {{ t('views.tosPrivacy.privacyTab') }}
    </button>
  </div>

  <div class="content-container">
    <div class="content">
      <template v-if="tosSelectedTab === TOS_TABS.TOS">
        <h2>{{ t('views.tosPrivacy.tosTitle') }}</h2>
      </template>
      <template v-else>
        <h2>{{ t('views.tosPrivacy.privacyTitle') }}</h2>
      </template>
    </div>

    <p class="acknowledgment">{{ t('views.tosPrivacy.acknowledgment') }}</p>

    <div class="buttons">
      <primary-button variant="outline">
        {{ t('views.tosPrivacy.declineButton') }}
      </primary-button>
      <primary-button>
        {{ t('views.tosPrivacy.acceptButton') }}
      </primary-button>
    </div>

    <i18n-t keypath="views.tosPrivacy.questionsToSupport" tag="p" class="questions-to-support">
      <template #supportLink>
        <router-link to="/contact">
          {{ t('views.tosPrivacy.contactSupport') }}
        </router-link>
      </template>
    </i18n-t>
  </div>
</template>

<style scoped>
h1 {
  font-family: metropolis;
  font-size: 2.25rem;
  font-weight: 300;
  color: var(--colour-ti-highlight);
  margin-block: 1.25rem 1rem;
}

.description {
  font-size: 1.25rem;
  margin-block-end: 2rem;
}

.tabs {
  display: flex;

  .tab {
    cursor: pointer;
    width: 100%;
    border: none;
    border-block-end: 2px solid transparent;
    padding-block: 1rem;
    text-align: center;
    background-color: var(--colour-neutral-lower);

    &.active {
      border-block-end-color: var(--colour-primary-default);
      background-color: var(--colour-neutral-base);
    }
  }
}

.content-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2rem;
  padding: 2rem 1.5rem 1.5rem 1.5rem;
  background-color: var(--colour-neutral-base);
  border-end-start-radius: 1rem;
  border-end-end-radius: 1rem;

  .content {
    padding: 1rem 2rem 1rem 0;
    max-height: 436px;
    overflow-y: auto;
  }

  .acknowledgment {
    font-size: 0.875rem;
    color: var(--colour-ti-base);
  }

  .buttons {
    display: flex;
    gap: 1rem;
  }

  .questions-to-support {
    font-size: 0.875rem;

    a {
      color: var(--colour-primary-default);
    }
  }
}
</style>