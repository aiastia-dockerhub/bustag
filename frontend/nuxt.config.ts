// https://nuxt.com/docs/api/configuration/nuxt-config
import { execSync } from 'child_process'

let version = 'dev'
try {
  version = execSync('git rev-parse --short HEAD').toString().trim()
} catch {}

export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',
  devtools: { enabled: true },

  app: {
    head: {
      title: 'Bustag',
      htmlAttrs: { lang: 'zh-CN' },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, shrink-to-fit=no' },
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
      ],
    },
  },

  css: [
    'bootstrap/dist/css/bootstrap.min.css',
    '~/assets/css/main.css',
  ],

  runtimeConfig: {
    public: {
      appVersion: version,
    },
  },

  routeRules: {
    '/api/**': { proxy: 'http://localhost:8000/api/**' },
    '/img_proxy': { proxy: 'http://localhost:8000/img_proxy' },
  },
})