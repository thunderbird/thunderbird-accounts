<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { MailIcon, SendIcon, AppointmentIcon } from '@thunderbirdops/services-ui';

const { t } = useI18n();

const tbProAppointmentUrl = window._page?.tbProAppointmentUrl;
const tbProSendUrl = window._page?.tbProSendUrl;
const tbProMailUrl = window._page?.webmailUrl;
</script>

<template>
  <section>
    <h2>{{ t('components.thunderbirdApps.heading') }}</h2>
    <p class="subheading">{{ t('components.thunderbirdApps.paragraph') }}</p>

    <div class="thunderbird-apps-card">
      <a class="service-icon-link" :href="tbProMailUrl" target="_blank">
        <span class="icon-tile"><MailIcon /></span>
        <p>Mail</p>
      </a>

      <a class="service-icon-link" :href="tbProSendUrl" target="_blank">
        <span class="icon-tile"><SendIcon /></span>
        <p>Send</p>
      </a>

      <a class="service-icon-link" :href="tbProAppointmentUrl" target="_blank">
        <span class="icon-tile"><AppointmentIcon /></span>
        <p>Appointment</p>
      </a>
    </div>
  </section>
</template>

<style scoped>
section {
  max-width: 345px;
  box-shadow: 4px 4px 16px 0 rgba(0, 0, 0, 0.04);
  background-color: var(--colour-neutral-base);
  padding: 2rem 1.5rem;
  border-radius: 24px;

  h2 {
    font-family: Metropolis;
    font-size: 1.5rem;
    font-weight: 400;
    line-height: 1.2;
    margin-block-end: 0.25rem;
    color: var(--colour-ti-highlight);
  }
}

p.subheading {
  font-size: 0.875rem;
  line-height: 1.23;
  color: var(--colour-ti-secondary);
  margin-block-end: 1.5rem;
}

.thunderbird-apps-card {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  border-radius: 1.5rem;
  box-shadow: inset 2px 2px 4px 0 rgba(0, 0, 0, 0.05), 1px 1px 0 0 rgba(255, 255, 255, 0.6);
  background-color: rgba(228, 228, 231, 0.5);
  padding: 1.5rem;

  .service-icon-link {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;
    text-decoration: none;

    &:focus-visible {
      outline: none;
    }

    .icon-tile {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0.5rem;
      border-radius: 1rem;
      background-color: var(--colour-neutral-base);
      box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.08), inset 0 1px 0 0 rgba(255, 255, 255, 0.6);
      color: var(--colour-ti-secondary);
    }

    &:hover .icon-tile,
    &:focus-visible .icon-tile {
      background-color: var(--colour-primary-soft);
      box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.12), inset 0 1px 0 0 rgba(255, 255, 255, 0.6);
      color: var(--colour-primary-default);
    }

    &:active .icon-tile {
      background-color: var(--colour-primary-soft);
      box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.1);
      color: var(--colour-primary-pressed);
    }

    &:focus-visible .icon-tile {
      outline: 2px solid var(--colour-primary-hover);
      outline-offset: 2px;
    }

    p {
      font-size: 0.5rem;
      font-weight: 600;
      color: var(--colour-ti-secondary);
    }
  }
}

.icon-tile :deep(svg) {
  width: 3rem;
  height: 3rem;
}

@media (min-width: 768px) {
  section {
    min-width: 345px;
  }
}
</style>
