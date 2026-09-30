<script setup lang="ts">
import { BrandButton } from '@thunderbirdops/services-ui';
import { PhArrowLeft } from '@phosphor-icons/vue';

const actionUrl = window._page.currentView?.actionUrl;
const actionText = window._page.currentView?.actionText;
// Set by error.ftl for the Thundermail provisioning gate's deny reason only.
const errorMessage = window._page.currentView?.errorMessage;
</script>

<script lang="ts">
export default {
  name: 'ErrorView'
};
</script>

<template>
  <h2>{{ $t('errorTitle') }}</h2>
  <p v-if="errorMessage" data-testid="error-message">{{ errorMessage }}</p>
  <template v-if="actionUrl">
    <div class="button-container">
      <brand-button :href="actionUrl" data-testid="action-url">{{ actionText }}
        <template #iconLeft>
          <ph-arrow-left size="20" />
        </template>
      </brand-button>
    </div>
  </template>
</template>

<style scoped>
.button-container {
  width: fit-content;
}
</style>
