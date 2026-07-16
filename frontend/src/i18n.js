import { createI18n } from 'vue-i18n'

import en from './locales/en.json'
import es from './locales/es.json'

const savedLocale = localStorage.getItem('retention-checker-locale')
const supportedLocales = ['en', 'es']

const initialLocale = supportedLocales.includes(savedLocale)
  ? savedLocale
  : 'en'

const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages: {
    en,
    es
  }
})

export default i18n