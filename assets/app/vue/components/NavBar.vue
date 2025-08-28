<script setup lang="ts">
import Avatar from "@/components/Avatar.vue";

defineProps({
  pageContentId: String,
});

const username = window._page.username;
</script>

<template>
  <section class="screenreader-only">
    <a :href="pageContentId ?? '#content'">
      {{ $t('navbar.screenreader-skip-to-main-content') }}
    </a>
  </section>
  <nav class="navigation">
    <section class="nav-list">
    <img src="@/../../svg/logo-tb-pro.svg" alt="Thunderbird Pro">
    <avatar :username="username"/>
    </section>
  </nav>
</template>

<style scoped>
.screenreader-only {
  display: none;
}

.nav-list {
  width: 100%;
  display: flex;
  justify-content: space-between;
}

.navigation {
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  gap: 24px;
  margin: 0 0 43px;
  padding: 14px 56px;
  -webkit-backdrop-filter: blur(24px);
  backdrop-filter: blur(24px);
  box-shadow: 0 8px 24px 0 rgba(0, 0, 0, 0.1);
  background: linear-gradient(0deg, var(--colour-ti-base) -40%, #566a92 200%);
}

</style>
