<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { WAFFLE_SWITCH } from '@/types';
import { isWaffleSwitchActive } from '@/utils';

const { t } = useI18n();

// Only shown while the increased-traffic-banner waffle switch is active
const showBanner = computed(() => isWaffleSwitchActive(WAFFLE_SWITCH.INCREASED_TRAFFIC_BANNER));
</script>

<template>
  <div v-if="showBanner" class="traffic-banner" data-testid="traffic-banner" role="status">
    {{ t('components.trafficBanner.message') }}
  </div>
</template>

<style scoped>
/* Styled after the thunderbird.net top-of-page nav banner */
.traffic-banner {
  width: 100%;
  padding: 0.625rem 1rem;
  text-align: center;
  font-size: 0.875rem;
  font-weight: 600;
  color: #fff;
  background-image: linear-gradient(to right, #1373d9, #7f27ff);
}
</style>
