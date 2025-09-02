<script setup lang="ts">
/**
 * Note: afaik any urls with `@` need to be baked into the build. So we can't dynamically pull the svg here.
 * Well we can but we'll have to plumb the defined static url and that's a bit of work for 3 icons.
 */
import {computed} from "vue";
import {Services} from "@/../defines";

interface PropTypes {
  service: string;
}

const props = defineProps<PropTypes>();

const serviceName = computed(() => `services.${props.service}`);
</script>

<template>
  <div class="wrapper">
    <img v-if="service === Services.Thundermail" class="logo" src="@/../../svg/logo-thundermail.svg" alt=""/>
    <img v-else-if="service === Services.Appointment" class="logo" src="@/../../svg/logo-appointment.svg" alt=""/>
    <img v-else-if="service === Services.Send" class="logo" src="@/../../svg/logo-send.svg" alt=""/>
    {{ $t(serviceName) }}
  </div>
</template>

<style scoped>
.wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.logo {
  width: 64px;
}
</style>
