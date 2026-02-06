<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { PhArrowRight } from '@phosphor-icons/vue';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();
</script>

<template>
  <card-container class="get-started-card">
    <h2>{{ t('views.dashboard.getStartedCard.getStarted') }}</h2>

    <div class="content-container">
      <strong>{{ t('views.dashboard.getStartedCard.enableThunderbirdPro') }}</strong>
      <p>{{ t('views.dashboard.getStartedCard.enableThunderbirdProDescription') }}</p>

      <ol class="steps-list">
        <i18n-t keypath="views.dashboard.getStartedCard.stepOne" tag="li">
          <template #accountSettings>
            <strong>{{ t('views.dashboard.getStartedCard.accountSettings') }}</strong>
          </template>
        </i18n-t>
  
        <i18n-t keypath="views.dashboard.getStartedCard.stepTwo" tag="li">
          <template #addonsAndThemes>
            <strong>{{ t('views.dashboard.getStartedCard.addonsAndThemes') }}</strong>
          </template>
        </i18n-t>
  
        <i18n-t keypath="views.dashboard.getStartedCard.stepThree" tag="li">
          <template #thunderbirdPro>
            <strong>{{ t('views.dashboard.getStartedCard.thunderbirdPro') }}</strong>
          </template>
        </i18n-t>
      </ol>
    </div>

    <div class="need-thunderbird-desktop-container">
      <span>{{ t('views.dashboard.getStartedCard.needThunderbirdDesktop') }}</span>
      <a href="https://www.thunderbird.net/thunderbird/all/?utm_campaign=main&utm_medium=tb_pro&utm_source=accounts_dashboard&utm_content=get_started" target="_blank">
        <span>{{ t('views.dashboard.getStartedCard.installNow') }}</span>
        <ph-arrow-right size="16" />
      </a>
    </div>
  </card-container>
</template>

<style scoped>
.get-started-card {
  min-width: unset;

  h2 {
    font-family: metropolis;
    font-weight: 400;
    font-size: 1.5rem;
    line-height: 1.2;
    color: var(--colour-ti-highlight);
    margin-block-end: 1rem;
  }

  .content-container {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    color: var(--colour-ti-secondary);
    line-height: 1.32;

    strong {
      font-weight: 600;
    }
  }

  .steps-list {
    list-style-position: inside;
    padding: 0;
    line-height: 1.32;
    margin-block-end: 2rem;
  }

  .need-thunderbird-desktop-container {
    display: flex;
    gap: 0.5rem;

    span {
      font-size: 0.875rem;
      line-height: 1.23;
      color: var(--colour-ti-secondary);
    }

    a {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: .5rem;
      color: var(--colour-service-primary);
      cursor: pointer;

      span {
        color: var(--colour-service-primary);
        font-size: 0.75rem;
        text-decoration: underline;
      }
    }
  }
}
</style>