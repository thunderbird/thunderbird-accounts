<script setup lang="ts">
interface PropTypes {
  username: string,
  avatarUrl?: string,
}

defineProps<PropTypes>()
</script>

<template>
  <aside class="avatar">
    <img :src="avatarUrl" v-if="avatarUrl" :alt="$t('avatar.alt-text', {'username': username})"/>
    <span class="initials" :title="username" v-else>{{ username[0].toUpperCase() }}</span>
  </aside>
</template>

<style scoped>
.avatar {
  width: 40px;
  height: 40px;

  display: flex;
  justify-content: center;
  align-items: center;

  border: solid 1px #0a84ff;
  border-radius: 100%;
  background-color: rgba(10, 132, 255, 0.15);

  .initials {
    font-size: 14px;
    font-weight: bold;
    font-stretch: normal;
    font-style: normal;
    line-height: 1.43;
    letter-spacing: 0.1px;
    color: var(--colour-neutral-raised);
  }
}
</style>
