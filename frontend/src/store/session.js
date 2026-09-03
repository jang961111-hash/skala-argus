import { reactive, computed } from 'vue'
import { ROLE, ROLE_LABEL, FALLBACK_REDIRECT } from '../constants/domain'

/**
 * 세션 — CONTRACT v3.0 §4-2.
 * 로그인 응답은 {accessToken, role, redirectPath} 이고 사용자 상세는 GET /auth/me 로 받는다.
 * redirectPath 는 서버가 정한다. 프론트가 역할로 직접 계산하지 않는다(폴백만 둔다).
 */
const KEY = 'argus.session'

const state = reactive({
  accessToken: null,
  role: null,
  redirectPath: null,
  user: null, // { id, name, email, role, createdAt }
})

function restore() {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return
    const p = JSON.parse(raw)
    if (p?.accessToken) {
      state.accessToken = p.accessToken
      state.role = p.role || null
      state.redirectPath = p.redirectPath || null
      state.user = p.user || null
    }
  } catch {
    /* 손상된 저장값은 무시하고 미로그인으로 시작 */
  }
}
restore()

function persist() {
  if (state.accessToken) {
    localStorage.setItem(KEY, JSON.stringify({
      accessToken: state.accessToken, role: state.role, redirectPath: state.redirectPath, user: state.user,
    }))
  } else {
    localStorage.removeItem(KEY)
  }
}

export const session = {
  state,
  user: computed(() => state.user),
  role: computed(() => state.role || state.user?.role || null),
  roleLabel: computed(() => ROLE_LABEL[state.role || state.user?.role] || ''),
  isAuthenticated: computed(() => Boolean(state.accessToken)),
  isEngineer: computed(() => (state.role || state.user?.role) === ROLE.ENGINEER),
  isSafetyManager: computed(() => (state.role || state.user?.role) === ROLE.SAFETY_MANAGER),
  // 서버가 준 redirectPath 를 우선한다
  homePath: computed(() => state.redirectPath || FALLBACK_REDIRECT[state.role || state.user?.role] || '/login'),

  setLogin({ accessToken, role, redirectPath }) {
    state.accessToken = accessToken
    state.role = role
    state.redirectPath = redirectPath || FALLBACK_REDIRECT[role] || null
    persist()
  },
  setUser(user) {
    state.user = user
    if (user?.role) state.role = user.role
    if (!state.redirectPath) state.redirectPath = FALLBACK_REDIRECT[state.role] || null
    persist()
  },
  clear() {
    state.accessToken = null
    state.role = null
    state.redirectPath = null
    state.user = null
    persist()
  },
}
