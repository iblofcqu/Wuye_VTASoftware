import { createRouter, createWebHistory } from 'vue-router'

import HomeView from '@/views/HomeView.vue'

const placeholder = () => import('@/views/PlaceholderView.vue')
const preprocessGuide = () => import('@/views/preprocess/GuideView.vue')
const qualityGuide = () => import('@/views/quality/GuideView.vue')

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/preprocess/guide', meta: { title: '点云预处理 · 说明书' }, component: preprocessGuide },
    { path: '/preprocess/discretize', meta: { title: '网格离散' }, component: placeholder },
    { path: '/preprocess/scale', meta: { title: '尺寸缩放' }, component: placeholder },
    { path: '/preprocess/downsample', meta: { title: '下采样' }, component: placeholder },
    { path: '/preprocess/registration', meta: { title: '配准' }, component: placeholder },
    { path: '/quality/guide', meta: { title: '尺寸质量评估 · 说明书' }, component: qualityGuide },
    { path: '/quality/assess', meta: { title: '几何质量评估' }, component: placeholder },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

export default router
