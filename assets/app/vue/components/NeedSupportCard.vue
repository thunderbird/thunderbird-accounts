<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import CardContainer from '@/components/CardContainer.vue';

defineProps<{
  supportLinks: {
    label: string;
    link: string;
  }[];
}>();

const { t } = useI18n();
</script>

<template>
  <card-container dark padding="small">
    <div class="card-container-inner">
      <h2>{{ t('components.needSupportCard.needSupport') }}</h2>

      <div class="support-links" v-for="link in supportLinks" :key="link.label">
        <hr class="divider" />
        <a :href="link.link">
          {{ link.label }} &rarr;
        </a>
      </div>
    </div>
  </card-container>
</template>

<style scoped>
.card-container-inner {
  border-radius: 1rem;
  border: solid 1px rgba(88, 201, 255, 0.2);
  background-color: rgba(0, 0, 0, 0.4);
  color: #eeeef0; /* TODO: --colour-ti-base forced dark */
  padding: 1rem 2rem;

  h2 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #d9d9de; /* TODO: --colour-ti-secondary forced dark */
    margin-block-end: 1.75rem;
    text-align: center;
  }

  .support-links {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;

    a {
      color: inherit;
      text-decoration: none;
      font-size: 0.875rem;
      line-height: 1.23;
      margin-block-end: 0.75rem;

      &:hover {
        text-decoration: underline;
      }
    }

    &:last-child {
      a {
        margin-block-end: 0;
      }
    }

    .divider {
      height: 1px;
      color: #26292d;
      box-shadow: none;
    }
  }
}
</style>