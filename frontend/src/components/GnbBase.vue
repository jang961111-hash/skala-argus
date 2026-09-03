<script setup>
import { useRouter } from 'vue-router'
import { session } from '../store/session'
import { USE_MOCK } from '../api/client'

defineProps({
  roleLabel: { type: String, required: true },
  tabs: { type: Array, required: true }, // [{ to, label }]
})

const router = useRouter()

function logout() {
  session.clear()
  router.replace('/login')
}
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
      <span class="brand">
        <span class="logo">AR</span>
        <strong>Argus</strong>
      </span>

      <span class="role-badge">{{ roleLabel }}</span>

      <nav class="nav">
        <RouterLink v-for="t in tabs" :key="t.to" :to="t.to">{{ t.label }}</RouterLink>
      </nav>

      <div class="right">
        <span v-if="USE_MOCK" class="mock-badge" title="VITE_USE_MOCK=true">MOCK</span>
        <span class="user">
          <span class="avatar">{{ session.user.value?.name?.[0] || '?' }}</span>
          {{ session.user.value?.name }}
          <span class="muted small">{{ session.user.value?.email }}</span>
        </span>
        <button class="sm" @click="logout">로그아웃</button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 10;
}
.topbar-inner {
  max-width: 1280px; margin: 0 auto; padding: 0 20px;
  height: 56px; display: flex; align-items: center; gap: 16px;
}
.brand { display: flex; align-items: center; gap: 10px; color: var(--text); }
.logo {
  width: 32px; height: 32px; border-radius: 8px; background: var(--primary); color: #fff;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px;
}
.role-badge {
  font-size: 12px; font-weight: 600; background: var(--primary-soft); color: var(--primary);
  padding: 3px 10px; border-radius: 999px;
}
.nav { display: flex; gap: 18px; margin-left: 8px; }
.nav a { color: var(--muted); font-weight: 500; }
.nav a:hover { text-decoration: none; color: var(--text); }
.nav a.router-link-active { color: var(--primary); font-weight: 600; }
.right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.mock-badge {
  font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  background: var(--warning-soft); color: var(--warning); padding: 2px 8px; border-radius: 999px;
}
.user { display: inline-flex; align-items: center; gap: 6px; }
.avatar {
  width: 26px; height: 26px; border-radius: 50%; background: #e5e7eb;
  display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;
}
</style>
