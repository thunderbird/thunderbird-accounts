<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { PhGlobe, PhCheckCircle } from '@phosphor-icons/vue';
import { BaseBadge, BaseBadgeTypes } from '@thunderbirdops/services-ui';

// Types
import { CustomDomain, DOMAIN_STATUS, STEP } from './types';

// Shared components
import CardContainer from '@/components/CardContainer.vue';

// Local components
import CustomDomainForm from './components/CustomDomainForm.vue';
import ActionsMenu from './components/ActionsMenu.vue';

const { t } = useI18n();

const currentStep = ref<STEP>(STEP.INITIAL);
const customDomains = ref<CustomDomain[]>(window._page?.customDomains || []);
const customDomainsDescription = computed(() =>
  currentStep.value === STEP.INITIAL
  ? t('views.mail.sections.customDomains.customDomainsDescriptionInitial')
  : t('views.mail.sections.customDomains.customDomainsDescriptionAdd')
);
const lastDomainRemoved = ref<string>(null);

const handleStepChange = (step: STEP) => {
  currentStep.value = step;
};

const handleCustomDomainAdded = (customDomain: string) => {
  customDomains.value.push({ name: customDomain, status: DOMAIN_STATUS.PENDING });
};

const handleCustomDomainVerified = (customDomain: { name: string, status: DOMAIN_STATUS }) => {
  const index = customDomains.value.findIndex((domain) => domain.name === customDomain.name);

  if (index !== -1) {
    customDomains.value[index] = customDomain;
  }
};

const handleCustomDomainRemoved = (domainName: string) => {
  const index = customDomains.value.findIndex((domain) => domain.name === domainName);
  if (index !== -1) {
    lastDomainRemoved.value = domainName;
    customDomains.value.splice(index, 1);
  }
};
</script>

<script lang="ts">
export default {
  name: 'CustomDomainsSection',
};
</script>

<template>
  <section id="custom-domains">
    <card-container>
      <h2>{{ t('views.mail.sections.customDomains.customDomains') }}</h2>
      <p class="custom-domains-description">{{ customDomainsDescription }}</p>
      <strong>{{ t('views.mail.sections.customDomains.domainsAdded', { domainCount: customDomains.length, domainLimit: 3 }) }}</strong>

      <div class="custom-domains-list" v-if="customDomains.length > 0">
        <div class="custom-domain-item" v-for="domain in customDomains" :key="domain.name">
          <ph-globe size="20" />
          <p>{{ domain.name }}</p>

          <template v-if="domain.status === DOMAIN_STATUS.VERIFIED">
            <base-badge :type="BaseBadgeTypes.Verified">
              <template #icon>
                <ph-check-circle size="16" weight="fill" />
              </template>
              {{ t('views.mail.sections.customDomains.verified') }}
            </base-badge>
          </template>
          <template v-else-if="domain.status === DOMAIN_STATUS.FAILED">
            <base-badge :type="BaseBadgeTypes.NotSet">{{ t('views.mail.sections.customDomains.failed') }}</base-badge>
          </template>
          <template v-else>
            <base-badge :type="BaseBadgeTypes.Pending">{{ t('views.mail.sections.customDomains.pending') }}</base-badge>
          </template>

          <template v-if="domain.emailsCount > 0">
            <base-badge :type="BaseBadgeTypes.Emails">{{ t('views.mail.sections.customDomains.emailsCount', domain.emailsCount) }}</base-badge>
          </template>

          <actions-menu
            :domain="domain"
            @custom-domain-removed="handleCustomDomainRemoved"
            @custom-domain-verified="handleCustomDomainVerified"
          />
        </div>
      </div>

      <custom-domain-form
        @step-change="handleStepChange"
        @custom-domain-added="handleCustomDomainAdded"
        @custom-domain-verified="handleCustomDomainVerified"
        :last-domain-removed="lastDomainRemoved"
        :custom-domains="customDomains"
      />
    </card-container>
  </section>
</template>

<style scoped>
section#custom-domains {
  color: var(--colour-ti-secondary);

  h2 {
    font-size: 1.5rem;
    font-weight: 500;
    font-family: metropolis;
    color: var(--colour-ti-highlight);
    margin-block-end: 0.25rem;
  }

  p {
    font-family: Inter;
    line-height: 1.32;
    margin-block-end: 1.5rem;

    &.custom-domains-description {
      max-width: 730px;
    }
  }

  strong {
    display: block;
    font-family: Inter;
    font-size: 1rem;
    font-weight: 600;
    letter-spacing: 0.48px;
    margin-block-end: 1rem;
  }

  .custom-domains-list {
    border-block-start: 1px solid var(--colour-neutral-border);
    border-block-end: 1px solid var(--colour-neutral-border);
    margin-block-end: 1.5rem;

    .custom-domain-item {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      padding: 1rem 0.5rem;
      gap: 0.5rem;

      & + .custom-domain-item {
        border-block-start: 1px solid var(--colour-neutral-border);
      }

      p {
        flex: 1;
        margin-block-end: 0;
      }
    }
  }
}
</style>
