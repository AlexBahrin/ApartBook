import { createI18n } from 'vue-i18n'
import en from './en'
import ro from './ro'

// Other languages (ru, uk, de, fr, es) fall back to English until translated.
const messages = { en, ro }

const saved = localStorage.getItem('locale') || 'en'

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: messages[saved] ? saved : 'en',
  fallbackLocale: 'en',
  messages,
})

export function setLocale(locale) {
  i18n.global.locale.value = messages[locale] ? locale : 'en'
  localStorage.setItem('locale', locale)
  document.querySelector('html')?.setAttribute('lang', locale)
}

export default i18n
