import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import SyllabusView from '../views/SyllabusView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/syllabus',
      name: 'syllabus',
      component: SyllabusView,
    },
  ],
})

export default router
