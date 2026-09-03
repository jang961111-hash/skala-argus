<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/client'
import { SIGNUP_ROLES, errorText } from '../../constants/domain'

// WRA_C_01 회원가입 — POST /auth/signup {name, email, password, passwordConfirm, role}
const router = useRouter()

const form = reactive({ name: '', email: '', password: '', passwordConfirm: '', role: '' })
const error = ref('')
const done = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  done.value = ''
  if (!form.name.trim() || !form.email.trim() || !form.password || !form.passwordConfirm) {
    error.value = '이름·이메일·비밀번호·비밀번호 확인을 모두 입력하세요.'
    return
  }
  if (form.name.trim().length < 2 || form.name.trim().length > 20) {
    error.value = '이름은 2~20자로 입력하세요.'
    return
  }
  if (!form.role) {
    error.value = '역할을 선택하세요. (필수)'
    return
  }
  if (form.password.length < 8) {
    error.value = '비밀번호는 8자 이상이며 영문·숫자·특수문자를 포함해야 합니다.'
    return
  }
  if (form.password !== form.passwordConfirm) {
    error.value = '비밀번호가 일치하지 않습니다.'
    return
  }
  busy.value = true
  try {
    await api.signup({
      name: form.name.trim(), email: form.email.trim(),
      password: form.password, passwordConfirm: form.passwordConfirm, role: form.role,
    })
    done.value = '가입이 완료되었습니다. 로그인 화면으로 이동합니다.'
    setTimeout(() => router.replace('/login'), 900)
  } catch (e) {
    error.value = errorText(e, '가입에 실패했습니다.')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="auth-wrap">
    <form class="card auth-card stack" @submit.prevent="submit">
      <div class="head">
        <h1>회원가입</h1>
        <p class="muted small">Argus 계정을 만듭니다</p>
      </div>

      <div>
        <label for="name">이름</label>
        <input id="name" v-model="form.name" placeholder="홍길동" />
      </div>
      <div>
        <label for="su-email">이메일</label>
        <input id="su-email" v-model="form.email" type="email" autocomplete="username" placeholder="email@company.com" />
      </div>
      <div class="grid2">
        <div>
          <label for="pw">비밀번호</label>
          <input id="pw" v-model="form.password" type="password" autocomplete="new-password" placeholder="••••••••" />
        </div>
        <div>
          <label for="pw2">비밀번호 확인</label>
          <input id="pw2" v-model="form.passwordConfirm" type="password" autocomplete="new-password" placeholder="••••••••" />
        </div>
      </div>
      <p class="muted small">8자 이상 · 영문 + 숫자 + 특수문자</p>

      <div>
        <label>역할 선택 <span class="req">*</span></label>
        <div class="roles">
          <label v-for="r in SIGNUP_ROLES" :key="r.value" class="role" :class="{ on: form.role === r.value }">
            <input v-model="form.role" type="radio" :value="r.value" name="role" />
            {{ r.label }}
          </label>
        </div>
      </div>

      <div v-if="error" class="alert error">{{ error }}</div>
      <div v-if="done" class="alert success">{{ done }}</div>

      <button class="primary" type="submit" :disabled="busy">{{ busy ? '처리 중…' : '가입하기' }}</button>

      <p class="small center muted">
        이미 계정이 있으신가요? <RouterLink to="/login">로그인</RouterLink>
      </p>
    </form>
  </div>
</template>

<style scoped>
.auth-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }
.auth-card { width: 420px; max-width: 100%; padding: 28px; gap: 14px; }
.head { text-align: center; display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
.center { text-align: center; }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.req { color: var(--danger); }
.roles { display: flex; gap: 8px; }
.role {
  flex: 1; display: flex; align-items: center; justify-content: center; gap: 6px; margin: 0;
  border: 1px solid var(--border); border-radius: 8px; padding: 9px 10px; cursor: pointer;
  font-size: 14px; color: var(--text);
}
.role.on { border-color: var(--primary); background: var(--primary-soft); color: var(--primary); font-weight: 600; }
.role input { width: auto; }
</style>
