<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhDownloadSimple } from '@phosphor-icons/vue';
import { PrimaryButton } from '@thunderbirdops/services-ui';
import CardContainer from '@/components/CardContainer.vue';
import WelcomeHeader from './components/WelcomeHeader.vue';

const { t } = useI18n();
</script>

<script lang="ts">
export default {
  name: 'DashboardSection',
};
</script>

<template>
  <section id="dashboard">
    <welcome-header />

    <card-container>
      <h2>{{ t('views.mail.sections.dashboard.setUpAnEmailApp') }}</h2>

      <div class="download-card">
        <div class="content">
          <p>{{ t('views.mail.sections.dashboard.downloadDescription') }}</p>
          <primary-button>
            <template #iconLeft>
              <ph-download-simple size="16"/>
            </template>
            {{ t('views.mail.sections.dashboard.downloadButtonLabel') }}
          </primary-button>
        </div>

        <!-- <img src="@/assets/png/thundermail-dashboard-client.png" alt="Thunderbird client" /> -->
      </div>
    </card-container>
  </section>
</template>

<style scoped>
h2 {
  font-size: 1.5rem;
  font-weight: 500;
  font-family: metropolis;
  color: var(--colour-ti-highlight);
  margin-block-end: 1rem;
}

.download-card {
  border-radius: 8px;
  background-image:
    linear-gradient(125deg, rgba(88, 201, 255, 0) 74%, rgba(88, 201, 255, 1) 135%),
    linear-gradient(to bottom, var(--colour-neutral-lower), var(--colour-neutral-lower));

  .content {
    padding: 1.5rem 1rem;
  }

  p {
    max-width: 478px;
    font-family: Inter;
    font-size: 1rem;
    line-height: 1.32;
    color: var(--colour-ti-secondary);
    margin-block: 1.5rem;
  }

  :deep(.icon) {
    width: 1rem;
    height: 1rem;
  }
}
</style>