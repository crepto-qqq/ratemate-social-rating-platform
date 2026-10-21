import { createRouter, createWebHistory } from 'vue-router'

import LoginPage from '../LoginPage.vue'
import CreateTemplatePage from '../views/CreateTemplatePage.vue'
import HomePage from '../views/HomePage.vue'
import MessagesPage from '../views/MessagesPage.vue'
import ProfilePage from '../views/ProfilePage.vue'
import RateTemplatePage from '../views/RateTemplatePage.vue'
import TemplateDetailPage from '../views/TemplateDetailPage.vue'
import PublicRatingPage from '../views/PublicRatingPage.vue'
import AdminPage from '../views/AdminPage.vue'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    return savedPosition || { top: 0 }
  },
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
      path: '/ratings/:id',
      component: PublicRatingPage,
      meta: { title: 'Community rating', section: 'Discover' },
    },
    {
      path: '/templates/:id',
      component: TemplateDetailPage,
      meta: { title: 'Template', section: 'Discover' },
    },
    {
      path: '/create',
      component: CreateTemplatePage,
      meta: { title: 'Create Template', section: 'Create' },
    },
    {
      path: '/rate',
      component: RateTemplatePage,
      meta: { title: 'Rate Template', section: 'Rate' },
    },
    {
      path: '/messages',
      component: MessagesPage,
      meta: { title: 'Messages', section: 'Messages' },
    },
    {
      path: '/admin',
      component: AdminPage,
      meta: { title: 'Admin', section: 'Admin' },
    },
    {
      path: '/profile',
      component: ProfilePage,
      meta: { title: 'Personal Space', section: 'Profile' },
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/home_page',
    },
  ],
})

router.afterEach((to, from, failure) => {
  if (!failure) document.title = to.meta.title || 'Ratemate'
})

export default router
