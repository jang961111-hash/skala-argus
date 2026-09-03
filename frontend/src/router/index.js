import { createRouter, createWebHistory } from 'vue-router'
import WorkRequestListView from '../views/WorkRequestListView.vue'
import WorkRequestDetailView from '../views/WorkRequestDetailView.vue'

const routes = [
  { path: '/', name: 'work-requests', component: WorkRequestListView },
  { path: '/work-requests/:id', name: 'work-request-detail', component: WorkRequestDetailView, props: true },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
