import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import NotFoundView from '../views/NotFoundView.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFoundView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Required route params keyed by route name — used by the navigation guard below
const requiredParamsByRoute = {
  Process: 'projectId',
  Simulation: 'simulationId',
  SimulationRun: 'simulationId',
  Report: 'reportId',
  Interaction: 'reportId'
}

// Redirect to Home when a required route param is missing or the literal "undefined" string
router.beforeEach((to) => {
  const requiredParam = requiredParamsByRoute[to.name]
  if (requiredParam) {
    const value = to.params[requiredParam]
    if (!value || value === 'undefined') {
      return { path: '/' }
    }
  }
  return true
})

export default router
