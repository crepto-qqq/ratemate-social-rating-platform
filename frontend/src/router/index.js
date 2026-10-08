import { createRouter, createWebHistory } from 'vue-router'

import LoginPage from '../LoginPage.vue'
import CreateTemplatePage from '../views/CreateTemplatePage.vue'
import HomePage from '../views/HomePage.vue'
import MessagesPage from '../views/MessagesPage.vue'
import ProfilePage from '../views/ProfilePage.vue'
import RateTemplatePage from '../views/RateTemplatePage.vue'
import TemplateDetailPage from '../views/TemplateDetailPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      component: LoginPage,
      meta: { title: 'Login' },
    },
    {
      path: '/home_page',
      component: HomePage,
      meta: { title: 'Discover', section: 'Discover' },
    },
    {
      path: '/templates/:id',
      component: TemplateDetailPage,
      meta: { title: 'Template', section: 'Discover' },
    },
    {
      path: '/create',
      component: CreateTemplatePage,
      meta: { title: 'Create a template', section: 'Create' },
    },
    {
      path: '/rate',
      component: RateTemplatePage,
      meta: { title: 'Rate a template', section: 'Rate' },
    },
    {
      path: '/messages',
      component: MessagesPage,
      meta: { title: 'Messages', section: 'Messages' },
    },
    {
      path: '/profile',
      component: ProfilePage,
      meta: { title: 'Personal space', section: 'Profile' },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/home_page',
    },
  ],
})

export default router
