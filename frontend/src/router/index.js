import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import i18n from '@/i18n'

const routes = [
  { path: '/', name: 'landing', component: () => import('@/views/public/LandingView.vue'), meta: { titleKey: 'seo.landing' } },
  { path: '/apartments', name: 'apartments', component: () => import('@/views/public/ApartmentListView.vue'), meta: { titleKey: 'seo.apartments' } },
  { path: '/apartments/:slug', name: 'apartment-detail', component: () => import('@/views/public/ApartmentDetailView.vue'), meta: { titleKey: 'seo.apartmentDetail' } },

  // Auth
  { path: '/login', name: 'login', component: () => import('@/views/auth/LoginView.vue'), meta: { guestOnly: true, titleKey: 'seo.login' } },
  { path: '/register', name: 'register', component: () => import('@/views/auth/RegisterView.vue'), meta: { guestOnly: true, titleKey: 'seo.register' } },
  { path: '/activate/:uid/:token', name: 'activate', component: () => import('@/views/auth/ActivateView.vue') },
  { path: '/password-reset', name: 'password-reset', component: () => import('@/views/auth/PasswordResetView.vue') },
  { path: '/password-reset/:uid/:token', name: 'password-reset-confirm', component: () => import('@/views/auth/PasswordResetConfirmView.vue') },

  // User dashboard
  { path: '/dashboard/bookings', name: 'my-bookings', component: () => import('@/views/dashboard/MyBookingsView.vue'), meta: { requiresAuth: true, nonStaff: true } },
  { path: '/dashboard/bookings/:id', name: 'my-booking-detail', component: () => import('@/views/dashboard/BookingDetailView.vue'), meta: { requiresAuth: true, nonStaff: true } },
  { path: '/dashboard/messages', name: 'my-messages', component: () => import('@/views/dashboard/MyMessagesView.vue'), meta: { requiresAuth: true, nonStaff: true } },
  { path: '/dashboard/messages/:id', name: 'my-conversation', component: () => import('@/views/dashboard/ConversationDetailView.vue'), meta: { requiresAuth: true, nonStaff: true } },
  { path: '/profile', name: 'profile', component: () => import('@/views/dashboard/ProfileView.vue'), meta: { requiresAuth: true } },

  // Staff
  { path: '/staff', redirect: '/staff/bookings' },
  { path: '/staff/apartments', name: 'staff-apartments', component: () => import('@/views/staff/StaffApartmentsView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/apartments/new', name: 'staff-apartment-new', component: () => import('@/views/staff/StaffApartmentFormView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/apartments/:id/edit', name: 'staff-apartment-manage', component: () => import('@/views/staff/StaffApartmentManageView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/apartments/:id/edit/general', name: 'staff-apartment-edit', component: () => import('@/views/staff/StaffApartmentFormView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/apartments/:id/images', name: 'staff-apartment-images', component: () => import('@/views/staff/StaffApartmentImagesView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/apartments/:id/availability', name: 'staff-availability', component: () => import('@/views/staff/StaffAvailabilityView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/apartments/:id/calendar', name: 'staff-calendar', component: () => import('@/views/staff/StaffCalendarView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/apartments/:id/ical', name: 'staff-ical', component: () => import('@/views/staff/StaffIcalFeedsView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/calendar', name: 'staff-global-calendar', component: () => import('@/views/staff/StaffGlobalCalendarView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/bookings', name: 'staff-bookings', component: () => import('@/views/staff/StaffBookingsView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/bookings/:id', name: 'staff-booking-detail', component: () => import('@/views/staff/StaffBookingDetailView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/messages', name: 'staff-messages', component: () => import('@/views/staff/StaffMessagesView.vue'), meta: { requiresAuth: true, staff: true } },
  { path: '/staff/messages/:id', name: 'staff-conversation', component: () => import('@/views/staff/StaffConversationDetailView.vue'), meta: { requiresAuth: true, staff: true } },

  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('@/views/NotFoundView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) {
    await auth.fetchMe()
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { next: to.fullPath } }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: auth.isStaff ? 'staff-bookings' : 'landing' }
  }
  if (to.meta.staff && !auth.isStaff) {
    return { name: 'landing' }
  }
  if (to.meta.nonStaff && auth.isStaff) {
    return { name: 'staff-bookings' }
  }
  return true
})

const BASE_TITLE = 'Iași Cazare'

router.afterEach((to) => {
  const t = i18n.global.t
  const titleKey = to.meta.titleKey
  document.title = titleKey ? `${t(titleKey)} — ${BASE_TITLE}` : BASE_TITLE
})

export default router
