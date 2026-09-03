<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { session } from './store/session'
import { ROLE } from './constants/domain'
import GnbEngineer from './components/GnbEngineer.vue'
import GnbSafety from './components/GnbSafety.vue'

const route = useRoute()

// 인증 화면(C_00/C_01)은 GNB 없이 카드만 표시한다.
const bare = computed(() => Boolean(route.meta.bare))
const gnb = computed(() => {
  if (bare.value || !session.state.accessToken) return null
  return session.role.value === ROLE.SAFETY_MANAGER ? GnbSafety : GnbEngineer
})
</script>

<template>
  <div class="app">
    <component :is="gnb" v-if="gnb" />
    <main :class="bare ? 'bare' : 'content'">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.content { max-width: 1280px; margin: 0 auto; padding: 24px 20px 48px; }
.bare { padding: 0; }
</style>
