import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'

const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/tagit', name: 'tagit', component: () => import('../views/TagitView.vue') },
  { path: '/local', name: 'local', component: () => import('../views/LocalView.vue') },
  { path: '/local_fanhao', name: 'local_fanhao', component: () => import('../views/LocalFanhaoView.vue') },
  { path: '/model', name: 'model', component: () => import('../views/ModelView.vue') },
  { path: '/load_db', name: 'load_db', component: () => import('../views/LoadDbView.vue') },
  { path: '/search', name: 'search', component: () => import('../views/SearchView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router