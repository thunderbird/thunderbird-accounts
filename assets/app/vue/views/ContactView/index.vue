<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { VisualDivider } from '@thunderbirdops/services-ui';
import ContactSupportForm from './components/ContactSupportForm.vue';
import YourServices from '@/components/YourServices.vue';
// import NeedSupportCard from '@/components/NeedSupportCard.vue';
import CardContainer from '@/components/CardContainer.vue';

const { t } = useI18n();

// TODO: Uncomment when we have support links
// const supportLinks = [
//   { label: 'Need help with your account?', link: '#' },
//   { label: 'Trouble receiving or sending emails?', link: '#' },
//   { label: 'Change your email address', link: '#' },
//   { label: 'Export your data', link: '#' },
// ];
</script>

<script lang="ts">
export default {
  name: 'ContactView',
};
</script>

<template>
  <div class="contact-view">
    <card-container class="contact-view-left-column">
      <h2>{{ t('views.contact.title') }}</h2>
      <p>{{ t('views.contact.requiredFieldsText') }}</p>
    
      <contact-support-form />
    </card-container>

    <visual-divider type="vertical" class="hidden-sm" />

    <div class="contact-view-right-column">
      <your-services />

      <!-- TODO: We don't have support links yet -->
      <!-- <need-support-card :support-links="supportLinks" /> -->
    </div>
  </div>
</template>

<style scoped>
.hidden-sm {
  display: none;
}

.contact-view {
  display: flex;
  justify-content: center;
  gap: 2rem;
  flex-wrap: wrap;
  align-items: stretch;
}

.contact-view-left-column {
  min-width: unset;

  h2 {
    font-family: metropolis;
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--colour-ti-highlight);
    margin-block-end: 1.5rem;
  }

  p {
    color: var(--colour-ti-secondary);
    line-height: 1.32;
    margin-block-end: 1.5rem;
  }
}

.contact-view-right-column {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  max-width: 345px;
}

@media (min-width: 768px) {
  .contact-view {
    gap: 4rem;
  }
}

@media (min-width: 1024px) {
  .contact-view-left-column {
    min-width: 568px;
  }

  .contact-view {
    gap: 2rem;
  }
}

@media (min-width: 1280px) {
  .hidden-sm {
    display: block;
  }

  .divider {
    align-self: stretch;
    height: auto;
  }
}
</style>