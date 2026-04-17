<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter, useRoute } from 'vue-router';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import { defaultLocale } from '@/utils';
import {
  getCurrentLegalDocs,
  acceptLegalDocs,
  declineLegalDocs,
  type LegalDocMeta,
} from './api';
import { LEGAL_DOCUMENT_TYPES } from './types';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const declineButtonLabel = window._page?.hasActiveSubscription ? t('views.tosPrivacy.declineAfterPayment') : t('views.tosPrivacy.declineButton');

const tosSelectedTab = ref<LEGAL_DOCUMENT_TYPES>(LEGAL_DOCUMENT_TYPES.TOS);
const loading = ref(true);
const accepting = ref(false);
const declining = ref(false);
const error = ref('');

const tosDoc = ref<LegalDocMeta | null>(null);
const privacyDoc = ref<LegalDocMeta | null>(null);
const tosContent = ref('');
const privacyContent = ref('');

const renderedTosHtml = computed(() => tosContent.value);

const renderedPrivacyHtml = computed(() => privacyContent.value);

const sourceContext = computed(() => {
  return (route.query.source as string) || 'accounts-dashboard';
});

async function handleAccept() {
  accepting.value = true;
  error.value = '';
  try {
    await acceptLegalDocs(sourceContext.value);
    window._page.needsTosAcceptance = false;
    router.push({ name: 'dashboard' });
  } catch (e) {
    error.value = t('views.tosPrivacy.errorAccepting');
  } finally {
    accepting.value = false;
  }
}

async function handleDecline() {
  declining.value = true;
  error.value = '';
  try {
    const { redirect_url } = await declineLegalDocs(sourceContext.value);
    window.location.href = redirect_url;
  } catch (e) {
    error.value = t('views.tosPrivacy.errorDeclining');
    declining.value = false;
  }
}

onMounted(async () => {
  try {
    const locale = defaultLocale();
    const { documents } = await getCurrentLegalDocs(locale);

    for (const doc of documents) {
      if (doc.document_type === LEGAL_DOCUMENT_TYPES.TOS) {
        tosDoc.value = doc;
        tosContent.value = doc.content;
      } else if (doc.document_type === LEGAL_DOCUMENT_TYPES.PRIVACY) {
        privacyDoc.value = doc;
        privacyContent.value = doc.content;
      }
    }
  } catch (e) {
    error.value = t('views.tosPrivacy.errorLoading');
  } finally {
    loading.value = false;
  }
});
</script>

<script lang="ts">
export default {
  name: 'TosPrivacyView',
};
</script>

<template>
  <h1>{{ t('views.tosPrivacy.title') }}</h1>
  <p class="description">{{ t('views.tosPrivacy.description') }}</p>

  <div v-if="error" class="error-message">{{ error }}</div>

  <div v-if="loading" class="loading">{{ t('views.tosPrivacy.loading') }}</div>

  <template v-else>
    <div class="tabs">
      <button
        :class="{ 'active': tosSelectedTab === LEGAL_DOCUMENT_TYPES.TOS }"
        class="tab"
        @click="tosSelectedTab = LEGAL_DOCUMENT_TYPES.TOS"
      >
        {{ t('views.tosPrivacy.tosTab') }}
      </button>
      <button
        :class="{ 'active': tosSelectedTab === LEGAL_DOCUMENT_TYPES.PRIVACY }"
        class="tab"
        @click="tosSelectedTab = LEGAL_DOCUMENT_TYPES.PRIVACY"
      >
        {{ t('views.tosPrivacy.privacyTab') }}
      </button>
    </div>

    <div class="content-container">
      <div class="content legal-content">
        <div
          v-if="tosSelectedTab === LEGAL_DOCUMENT_TYPES.TOS"
          v-html="renderedTosHtml"
        />
        <div
          v-else
          v-html="renderedPrivacyHtml"
        />
      </div>

      <p class="acknowledgment">{{ t('views.tosPrivacy.acknowledgment') }}</p>

      <div class="buttons">
        <primary-button variant="outline" :disabled="declining" @click="handleDecline">
          {{ declining ? t('views.tosPrivacy.loading') : declineButtonLabel }}
        </primary-button>
        <primary-button :disabled="accepting" @click="handleAccept">
          {{ accepting ? t('views.tosPrivacy.loading') : t('views.tosPrivacy.acceptButton') }}
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

.error-message {
  color: var(--colour-danger-default, #d32f2f);
  padding: 0.75rem 1rem;
  margin-block-end: 1rem;
  border-radius: 0.5rem;
  background-color: var(--colour-danger-lower, #fdecea);
}

.loading {
  text-align: center;
  padding: 3rem;
  color: var(--colour-ti-base);
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
    width: 100%;
    max-height: 28rem;
    overflow-y: auto;
    padding: 1rem 2rem 1rem 0;
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

/* Styles for the rendered markdown content */
.legal-content :deep(h1) {
  font-size: 1.5rem;
  font-weight: 400;
  color: var(--colour-ti-highlight);
  margin-block: 0 1.5rem;
}

.legal-content :deep(h2) {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--colour-ti-secondary);
  margin-block: 1.5rem 0.75rem;
}

.legal-content :deep(h3) {
  font-size: 1rem;
  font-weight: 600;
  color: var(--colour-ti-secondary);
  margin-block: 1rem 0.5rem;
}

.legal-content :deep(p) {
  margin-block: 0.5rem;
  color: var(--colour-ti-secondary);
  line-height: 1.32;
}

.legal-content :deep(ul),
.legal-content :deep(ol) {
  padding-inline-start: 1.5rem;
  color: var(--colour-ti-secondary);
  margin-block: 0.5rem;
}

.legal-content :deep(li) {
  margin-block: 0.25rem;
  color: var(--colour-ti-secondary);
  line-height: 1.6;
}

.legal-content :deep(strong) {
  font-weight: 600;
  color: var(--colour-ti-secondary);
}

.legal-content :deep(a) {
  color: var(--colour-ti-highlight);
}
</style>
