import { createRouter, createWebHistory } from 'vue-router'
import api from '../api/client'
import { session } from '../store/session'
import { ROLE } from '../constants/domain'

import LoginView from '../views/auth/LoginView.vue'
import SignupView from '../views/auth/SignupView.vue'
import EngineerHomeView from '../views/engineer/EngineerHomeView.vue'
import RequestNewView from '../views/engineer/RequestNewView.vue'
import AgentRunView from '../views/engineer/AgentRunView.vue'
import ResultEditView from '../views/engineer/ResultEditView.vue'
import MyRequestsView from '../views/engineer/MyRequestsView.vue'
import ManageRequestsView from '../views/safety/ManageRequestsView.vue'
import ManageRequestDetailView from '../views/safety/ManageRequestDetailView.vue'
import ManageHistoryView from '../views/safety/ManageHistoryView.vue'

const E = [ROLE.ENGINEER]
const S = [ROLE.SAFETY_MANAGER]

// :id 는 UUID v4 다 (계약 §1). 화면 표시용 번호는 requestNo 로 따로 온다.
const routes = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true, bare: true } },
  { path: '/signup', name: 'signup', component: SignupView, meta: { public: true, bare: true } },

  { path: '/home', name: 'engineer-home', component: EngineerHomeView, meta: { roles: E } },
  { path: '/requests/new', name: 'request-new', component: RequestNewView, meta: { roles: E } },
  { path: '/requests/:id/run', name: 'request-run', component: AgentRunView, props: true, meta: { roles: E } },
  { path: '/requests/:id/result', name: 'request-result', component: ResultEditView, props: true, meta: { roles: E } },
  { path: '/my/requests', name: 'my-requests', component: MyRequestsView, meta: { roles: E } },

  { path: '/manage/requests', name: 'manage-requests', component: ManageRequestsView, meta: { roles: S } },
  { path: '/manage/requests/:id', name: 'manage-request-detail', component: ManageRequestDetailView, props: true, meta: { roles: S } },
  { path: '/manage/history', name: 'manage-history', component: ManageHistoryView, meta: { roles: S } },

  { path: '/', redirect: () => (session.state.accessToken ? session.homePath.value : '/login') },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({ history: createWebHistory(), routes })

// 새로고침·직접 URL 진입 시 GET /auth/me 로 사용자·역할을 한 번만 복원한다 (계약 §4-3).
let hydrated = false
async function hydrate() {
  if (hydrated) return
  hydrated = true
  if (!session.state.accessToken) return
  try {
    session.setUser(await api.me())
  } catch {
    session.clear()
  }
}

router.beforeEach(async (to) => {
  await hydrate()

  const authed = Boolean(session.state.accessToken)
  const role = session.role.value

  if (!to.meta.public && !authed) {
    return { path: '/login', query: to.fullPath === '/' ? {} : { redirect: to.fullPath } }
  }
  if (to.meta.public && authed) return session.homePath.value
  if (to.meta.roles && !to.meta.roles.includes(role)) return session.homePath.value
  return true
})

export default router
