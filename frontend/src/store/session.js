import { reactive, computed } from 'vue'

// CONTRACT.md 샘플 사용자. 역할 전환 데모용 단순 reactive store (Pinia 미사용).
export const USERS = {
  ENGINEER: { id: 'U-001', name: '김민준', role: 'ENGINEER', label: '엔지니어' },
  SAFETY_MANAGER: { id: 'U-002', name: '이정호', role: 'SAFETY_MANAGER', label: '안전관리자' },
}

const state = reactive({
  role: 'ENGINEER',
})

export const session = {
  state,
  user: computed(() => USERS[state.role]),
  isEngineer: computed(() => state.role === 'ENGINEER'),
  isSafetyManager: computed(() => state.role === 'SAFETY_MANAGER'),
  setRole(role) {
    if (USERS[role]) state.role = role
  },
}
