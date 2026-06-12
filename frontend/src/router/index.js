import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/pipeline',
  },
  {
    path: '/pipeline',
    name: 'Pipeline',
    component: () => import('../views/PipelineView.vue'),
  },
  {
    path: '/report/:taskId',
    name: 'Report',
    component: () => import('../views/ReportView.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router