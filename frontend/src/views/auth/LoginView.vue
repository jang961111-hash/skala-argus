<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api, { USE_MOCK } from '../../api/client'
import { session } from '../../store/session'
import { errorText } from '../../constants/domain'

// WRA_C_00 로그인 — POST /auth/login → {accessToken, role, redirectPath}
const router = useRouter()
const route = useRoute()

const form = reactive({ email: '', password: '' })
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  if (!form.email.trim() || !form.password) {
    error.value = '이메일과 비밀번호를 모두 입력하세요.'
    return
  }
  busy.value = true
  try {
    const res = await api.login({ email: form.email.trim(), password: form.password })
    session.setLogin(res)
    // GNB 에 이름·이메일을 띄우려면 사용자 상세가 필요하다 (로그인 응답에는 없다).
    try { session.setUser(await api.me()) } catch { /* 이름 표시는 실패해도 진입은 막지 않는다 */ }

    // 역할 분기는 서버가 준 redirectPath 를 그대로 쓴다.
    const next = typeof route.query.redirect === 'string' ? route.query.redirect : null
    router.replace(next || res.redirectPath || session.homePath.value)
  } catch (e) {
    error.value = errorText(e, '로그인에 실패했습니다.')
  } finally {
    busy.value = false
  }
}

function fill(email) {
  form.email = email
  form.password = 'Passw0rd!'
}
</script>

<template>
  <div class="auth-wrap">
    <form class="card auth-card stack" @submit.prevent="submit">
      <div class="head">
        <span class="logo">RF</span>
        <h1>ReplaceFlow</h1>
        <p class="muted small">부품 교체 요청·승인 시스템</p>
      </div>

      <div>
        <label for="email">이메일</label>
        <input id="email" v-model="form.email" type="email" autocomplete="username" placeholder="email@company.com" />
      </div>

      <div>
        <label for="password">비밀번호</label>
        <input id="password" v-model="form.password" type="password" autocomplete="current-password" placeholder="••••••••" />
      </div>

      <div v-if="error" class="alert error">{{ error }}</div>

      <button class="primary" type="submit" :disabled="busy">{{ busy ? '로그인 중…' : '로그인' }}</button>

      <p class="small center muted">
        계정이 없으신가요? <RouterLink to="/signup">회원가입</RouterLink>
      </p>

      <div v-if="USE_MOCK" class="demo">
        <p class="small muted">데모 계정 (비밀번호 <code>Passw0rd!</code>)</p>
        <div class="row" style="gap: 6px">
          <button class="sm" type="button" @click="fill('engineer@replaceflow.test')">엔지니어</button>
          <button class="sm" type="button" @click="fill('safety@replaceflow.test')">안전관리자</button>
        </div>
      </div>
    </form>
  </div>
</template>

<style scoped>
.auth-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
.auth-card { width: 420px; max-width: 100%; padding: 28px; gap: 14px; }
.head { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 6px; margin-bottom: 6px; }
.logo {
  width: 40px; height: 40px; border-radius: 10px; background: var(--primary); color: #fff;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 700;
}
.center { text-align: center; }
.demo { border-top: 1px solid var(--border); padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
</style>
