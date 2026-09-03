<script setup>
import { session, USERS } from './store/session'
import { USE_MOCK } from './api/client'

const roles = Object.values(USERS)
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="topbar-inner">
        <RouterLink to="/" class="brand">
          <span class="logo">RF</span>
          <span>
            <strong>ReplaceFlow</strong>
            <span class="muted small tagline">설비 부품 교체 승인 에이전트</span>
          </span>
        </RouterLink>

        <nav class="nav">
          <RouterLink to="/">작업요청</RouterLink>
        </nav>

        <div class="right">
          <span v-if="USE_MOCK" class="mock-badge" title="VITE_USE_MOCK=true">MOCK</span>
          <div class="role-switch" role="group" aria-label="역할 전환">
            <button
              v-for="u in roles"
              :key="u.role"
              :class="{ active: session.state.role === u.role }"
              @click="session.setRole(u.role)"
            >
              {{ u.label }}
            </button>
          </div>
          <span class="user">
            <span class="avatar">{{ session.user.value.name[0] }}</span>
            {{ session.user.value.name }}
            <span class="muted small">({{ session.user.value.id }})</span>
          </span>
        </div>
      </div>
    </header>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.topbar {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 10;
}
.topbar-inner {
  max-width: 1280px; margin: 0 auto; padding: 0 20px;
  height: 56px; display: flex; align-items: center; gap: 24px;
}
.brand { display: flex; align-items: center; gap: 10px; color: var(--text); }
.brand:hover { text-decoration: none; }
.logo {
  width: 32px; height: 32px; border-radius: 8px; background: var(--primary); color: #fff;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px;
}
.tagline { margin-left: 8px; }
.nav a { color: var(--muted); font-weight: 500; }
.nav a.router-link-active { color: var(--primary); }
.right { margin-left: auto; display: flex; align-items: center; gap: 14px; }
.mock-badge {
  font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  background: var(--warning-soft); color: var(--warning); padding: 2px 8px; border-radius: 999px;
}
.role-switch { display: inline-flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
.role-switch button { border: 0; border-radius: 0; padding: 6px 12px; font-size: 13px; }
.role-switch button + button { border-left: 1px solid var(--border); }
.role-switch button.active { background: var(--primary-soft); color: var(--primary); font-weight: 600; }
.user { display: inline-flex; align-items: center; gap: 6px; }
.avatar {
  width: 26px; height: 26px; border-radius: 50%; background: #e5e7eb;
  display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600;
}
.content { max-width: 1280px; margin: 0 auto; padding: 24px 20px 48px; }
</style>
