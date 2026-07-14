import { createI18n } from 'vue-i18n'
import en from './en'
import ro from './ro'
import de from './de'
import fr from './fr'
import es from './es'
import ru from './ru'
import uk from './uk'

// Core chrome is translated for all locales; untranslated keys fall back to English.
const messages = { en, ro, de, fr, es, ru, uk }

// Romanian is the default language for first-time visitors.
const saved = localStorage.getItem('locale') || 'ro'

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: messages[saved] ? saved : 'ro',
  fallbackLocale: 'en',
  messages,
})

export function setLocale(locale) {
  i18n.global.locale.value = messages[locale] ? locale : 'en'
  localStorage.setItem('locale', locale)
  document.querySelector('html')?.setAttribute('lang', locale)
}

export default i18n
