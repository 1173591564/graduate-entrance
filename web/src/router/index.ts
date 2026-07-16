import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '../views/HomeView.vue'
import PlanningView from '../views/PlanningView.vue'
import ProblemsView from '../views/ProblemsView.vue'
import StatsView from '../views/StatsView.vue'
import SyllabusView from '../views/SyllabusView.vue'
import TodayView from '../views/TodayView.vue'

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
    {
      path: '/planning',
      name: 'planning',
      component: PlanningView,
    },
    {
      path: '/today',
      name: 'today',
      component: TodayView,
    },
    {
      path: '/stats',
      name: 'stats',
      component: StatsView,
    },
    {
      path: '/problems',
      name: 'problems',
      component: ProblemsView,
    },
  ],
})

export default router
