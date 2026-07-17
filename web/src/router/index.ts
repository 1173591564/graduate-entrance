import { createRouter, createWebHistory } from 'vue-router'

import EssayView from '../views/EssayView.vue'
import HomeView from '../views/HomeView.vue'
import InsightsView from '../views/InsightsView.vue'
import PapersView from '../views/PapersView.vue'
import PlanningView from '../views/PlanningView.vue'
import ProblemsView from '../views/ProblemsView.vue'
import RetroView from '../views/RetroView.vue'
import ReviewsView from '../views/ReviewsView.vue'
import StatsView from '../views/StatsView.vue'
import SyllabusView from '../views/SyllabusView.vue'
import TodayView from '../views/TodayView.vue'
import VocabView from '../views/VocabView.vue'

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
    {
      path: '/reviews',
      name: 'reviews',
      component: ReviewsView,
    },
    {
      path: '/vocab',
      name: 'vocab',
      component: VocabView,
    },
    {
      path: '/papers',
      name: 'papers',
      component: PapersView,
    },
    {
      path: '/retro',
      name: 'retro',
      component: RetroView,
    },
    {
      path: '/insights',
      name: 'insights',
      component: InsightsView,
    },
    {
      path: '/essay',
      name: 'essay',
      component: EssayView,
    },
  ],
})

export default router
