<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useConfigStore } from '@/stores/config'
import { setLocale } from '@/i18n'
import { useI18n } from 'vue-i18n'

const auth = useAuthStore()
const config = useConfigStore()
const router = useRouter()
const { locale } = useI18n()

const languages = computed(() => config.languages)

const FLAGS = { ro: '🇷🇴', en: '🇬🇧', ru: '🇷🇺', uk: '🇺🇦', de: '🇩🇪', fr: '🇫🇷', es: '🇪🇸' }
function flag(code) {
  return FLAGS[code] || ''
}

function changeLanguage(code) {
  setLocale(code)
}

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm sticky-top">
    <div class="container">
      <RouterLink class="navbar-brand" :to="{ name: 'landing' }">
        <i class="bi bi-house-heart-fill"></i> Iași Cazare
      </RouterLink>

      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
        <span class="navbar-toggler-icon"></span>
      </button>

      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav me-auto">
          <li class="nav-item">
            <RouterLink class="nav-link" :to="{ name: 'apartments' }">{{ $t('nav.browse') }}</RouterLink>
          </li>
        </ul>

        <ul class="navbar-nav align-items-lg-center">
          <!-- Language selector -->
          <li class="nav-item dropdown me-lg-2">
            <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
              <span class="flag">{{ flag(locale) }}</span> {{ locale.toUpperCase() }}
            </a>
            <ul class="dropdown-menu dropdown-menu-end">
              <li v-for="lang in languages" :key="lang.code">
                <button class="dropdown-item" :class="{ active: locale === lang.code }" @click="changeLanguage(lang.code)">
                  <span class="flag">{{ flag(lang.code) }}</span> {{ lang.name }}
                </button>
              </li>
            </ul>
          </li>

          <template v-if="auth.isAuthenticated">
            <template v-if="!auth.isStaff">
              <li class="nav-item">
                <RouterLink class="nav-link" :to="{ name: 'my-bookings' }">
                  <i class="bi bi-calendar-check"></i> {{ $t('nav.myBookings') }}
                </RouterLink>
              </li>
              <li class="nav-item">
                <RouterLink class="nav-link position-relative" :to="{ name: 'my-messages' }">
                  <i class="bi bi-chat-dots"></i> {{ $t('nav.messages') }}
                  <span v-if="config.unreadMessages" class="badge rounded-pill bg-danger">{{ config.unreadMessages }}</span>
                </RouterLink>
              </li>
            </template>
            <template v-else>
              <li class="nav-item">
                <RouterLink class="nav-link" :to="{ name: 'staff-bookings' }">{{ $t('nav.bookings') }}</RouterLink>
              </li>
              <li class="nav-item">
                <RouterLink class="nav-link" :to="{ name: 'staff-apartments' }">{{ $t('nav.apartments') }}</RouterLink>
              </li>
              <li class="nav-item">
                <RouterLink class="nav-link" :to="{ name: 'staff-global-calendar' }">{{ $t('nav.calendar') }}</RouterLink>
              </li>
              <li class="nav-item">
                <RouterLink class="nav-link position-relative" :to="{ name: 'staff-messages' }">
                  <i class="bi bi-chat-dots"></i> {{ $t('nav.messages') }}
                  <span v-if="config.unreadMessages" class="badge rounded-pill bg-danger">{{ config.unreadMessages }}</span>
                </RouterLink>
              </li>
            </template>

            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                <i class="bi bi-person-circle"></i> {{ auth.user.username }}
              </a>
              <ul class="dropdown-menu dropdown-menu-end">
                <li>
                  <RouterLink class="dropdown-item" :to="{ name: 'profile' }">
                    <i class="bi bi-person"></i> {{ $t('nav.profile') }}
                  </RouterLink>
                </li>
                <li><hr class="dropdown-divider" /></li>
                <li>
                  <button class="dropdown-item" @click="logout">
                    <i class="bi bi-box-arrow-right"></i> {{ $t('nav.logout') }}
                  </button>
                </li>
              </ul>
            </li>
          </template>

          <template v-else>
            <li class="nav-item">
              <RouterLink class="nav-link" :to="{ name: 'login' }">{{ $t('nav.login') }}</RouterLink>
            </li>
            <li class="nav-item">
              <RouterLink class="btn btn-primary btn-sm ms-lg-2" :to="{ name: 'register' }">{{ $t('nav.register') }}</RouterLink>
            </li>
          </template>
        </ul>
      </div>
    </div>
  </nav>
</template>

<style scoped>
.flag {
  font-size: 1.1em;
  line-height: 1;
}
</style>
