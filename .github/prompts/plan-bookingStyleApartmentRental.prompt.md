# Plan: Single-Owner Booking-Style Apartment Rental Website

Build a Booking-style platform for a single owner where guests can browse apartments, check availability, submit bookings, and message the admin. The admin manages listings, availability, pricing, bookings, and messages via a dedicated dashboard.

> **Note:** Django project with PostgreSQL and authentication app already in place.

---

## 1. Domain & Data Model Design

### 1.1 User Roles
- **Guest**: Default `User` (can browse, book, review, message)
- **Admin/Owner**: `User` with `is_staff=True` (can manage everything)

### 1.2 Core Models

#### Apartment
| Field | Type | Notes |
|-------|------|-------|
| `title` | CharField | |
| `slug` | SlugField | SEO-friendly URLs |
| `description` | TextField | |
| `address`, `city`, `country` | CharField | |
| `latitude`, `longitude` | DecimalField | Optional, for maps |
| `capacity` | PositiveIntegerField | Max guests |
| `bedrooms`, `bathrooms` | PositiveIntegerField | |
| `amenities` | JSONField | Or ManyToMany to `Amenity` |
| `base_price_per_night` | DecimalField | |
| `is_active` | BooleanField | |
| `created_at`, `updated_at` | DateTimeField | |

#### ApartmentImage
| Field | Type | Notes |
|-------|------|-------|
| `apartment` | ForeignKey | `related_name="images"` |
| `image` | ImageField | |
| `is_main` | BooleanField | |
| `order` | PositiveIntegerField | Gallery sorting |

#### Availability
| Field | Type | Notes |
|-------|------|-------|
| `apartment` | ForeignKey | |
| `date` | DateField | |
| `is_available` | BooleanField | |
| `min_stay_nights`, `max_stay_nights` | PositiveIntegerField | Optional |
| `note` | CharField | e.g. "Owner using apartment" |

#### PricingRule
| Field | Type | Notes |
|-------|------|-------|
| `apartment` | ForeignKey | |
| `start_date`, `end_date` | DateField | |
| `weekday` | IntegerField | Optional (0=Mon, 6=Sun) |
| `rule_type` | CharField | SEASONAL, WEEKEND, DISCOUNT |
| `price_per_night` | DecimalField | Or `price_modifier` for % |

> **Pricing Algorithm:** Start from `base_price_per_night`, apply matching `PricingRule`s (last/highest priority wins).

#### Booking
| Field | Type | Notes |
|-------|------|-------|
| `apartment` | ForeignKey | |
| `user` | ForeignKey | |
| `check_in`, `check_out` | DateField | |
| `guests_count` | PositiveIntegerField | |
| `total_price` | DecimalField | |
| `currency` | CharField | Default "EUR" |
| `status` | CharField | PENDING, CONFIRMED, CANCELLED_BY_USER, CANCELLED_BY_ADMIN, COMPLETED |
| `payment_status` | CharField | NOT_REQUIRED, UNPAID, PAID, REFUNDED |
| `notes` | TextField | Guest message |
| `created_at`, `updated_at` | DateTimeField | |

**Validation:**
- `check_out > check_in`
- `guests_count <= apartment.capacity`
- No overlapping CONFIRMED bookings

**Helper methods:** `get_nights()`, `calculate_total_price()`

#### Conversation & Message
| Conversation | Message |
|--------------|---------|
| `booking` (FK, optional) | `conversation` (FK) |
| `user` (FK, the guest) | `sender` (FK to User) |
| `created_at`, `updated_at` | `body` (TextField) |
| | `is_read` (BooleanField) |
| | `created_at` |

> One conversation per booking (guest ↔ admin).

#### Review
| Field | Type | Notes |
|-------|------|-------|
| `booking` | OneToOneField | 1 review per booking |
| `user` | ForeignKey | |
| `apartment` | ForeignKey | |
| `rating` | PositiveIntegerField | 1–5 |
| `comment` | TextField | |
| `created_at` | DateTimeField | |

> User can review only if `booking.status == COMPLETED`.

---

## 2. Project Setup & Config

### 2.1 Media Files in `settings.py`
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### 2.2 URL Config for Media (dev only)
```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ...
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

---

## 3. URL Structure & Views

### 3.1 Public Views (Unauthenticated)
| URL | View | Description |
|-----|------|-------------|
| `/` | `LandingView` | Landing page / search |
| `/apartments/` | `ApartmentListView` | Listing with filters |
| `/apartments/<slug>/` | `ApartmentDetailView` | Detail + calendar + reviews |
| `/apartments/<slug>/book/` | `BookingCreateView` | Booking form (login required) |

**Filters:** date range, city/country, capacity, price range

### 3.2 User Dashboard (`/dashboard/`)
| URL | View | Description |
|-----|------|-------------|
| `/dashboard/` | `DashboardOverviewView` | Next trip, quick links |
| `/dashboard/bookings/` | `MyBookingsListView` | User's bookings |
| `/dashboard/bookings/<id>/` | `BookingDetailView` | Booking detail |
| `/dashboard/messages/` | `MyConversationsListView` | Conversations |
| `/dashboard/messages/<id>/` | `ConversationDetailView` | Chat view |
| `/dashboard/profile/` | `ProfileUpdateView` | Profile settings |

> All protected with `@login_required`

### 3.3 Admin Dashboard (`/staff/`)
| URL | View | Description |
|-----|------|-------------|
| `/staff/apartments/` | `ApartmentListView` | List apartments |
| `/staff/apartments/create/` | `ApartmentCreateView` | Add apartment |
| `/staff/apartments/<id>/edit/` | `ApartmentUpdateView` | Edit apartment |
| `/staff/apartments/<id>/calendar/` | `CalendarView` | Visual calendar |
| `/staff/apartments/<id>/availability/` | `AvailabilityManageView` | Manage dates |
| `/staff/apartments/<id>/pricing-rules/` | `PricingRulesView` | Manage pricing |
| `/staff/bookings/` | `BookingsListView` | All bookings |
| `/staff/bookings/<id>/` | `BookingManageView` | Confirm/cancel/complete |
| `/staff/messages/` | `ConversationsListView` | All conversations |
| `/staff/messages/<id>/` | `ConversationDetailView` | Reply to guest |

> All protected with `@staff_member_required`

---

## 4. Templates Structure

```
templates/
├── base.html                          # Global layout
├── public/
│   ├── landing.html
│   ├── apartment_list.html
│   ├── apartment_detail.html
│   └── booking_form.html
├── dashboard/
│   ├── base_dashboard.html
│   ├── overview.html
│   ├── bookings_list.html
│   ├── booking_detail.html
│   ├── messages_list.html
│   ├── conversation_detail.html
│   └── profile.html
└── staff/
    ├── base_staff.html
    ├── apartments_list.html
    ├── apartment_form.html
    ├── calendar.html
    ├── availability.html
    ├── pricing_rules.html
    ├── bookings_list.html
    ├── booking_detail.html
    ├── messages_list.html
    └── conversation_detail.html
```

---

## 5. Forms

| Form | Fields | Validation |
|------|--------|------------|
| `BookingForm` | check_in, check_out, guests_count, notes | Date order, capacity, availability |
| `ProfileForm` | first_name, last_name, email, phone | |
| `ApartmentForm` | All apartment fields | ModelForm |
| `ApartmentImageForm` | Inline formset for images | |
| `AvailabilityForm` | date, is_available, notes | |
| `PricingRuleForm` | date range, rule_type, price | |
| `MessageForm` | body | |
| `ReviewForm` | rating, comment | Only for COMPLETED bookings |

---

## 6. Phased Implementation

### Phase 1: MVP ✅
> Goal: Guest can browse, request booking; Admin can confirm.

- [ ] **Models:** Apartment, ApartmentImage, Booking, Availability (basic)
- [ ] **Public:** Apartment list & detail, booking request form
- [ ] **User Dashboard:** My bookings list + detail
- [ ] **Admin Dashboard:** Apartment CRUD, booking list (change status)
- [ ] **Emails:** New booking → admin, status change → user
- [ ] No payments, no reviews, no messaging (just "notes" field in booking)

### Phase 2: v1 🚀
> Goal: Complete product with messaging & reviews.

- [ ] **Messaging:** Conversations tied to bookings
- [ ] **Reviews:** Users review after COMPLETED stays
- [ ] **Availability UI:** Better calendar (flatpickr for guests, FullCalendar for admin)
- [ ] **Pricing Rules:** Seasonal/weekend pricing in price calculation

### Phase 3: Nice-to-Have 🌟
- [ ] **Payments:** Stripe Checkout integration
- [ ] **Real-time Chat:** Django Channels WebSocket
- [ ] **Map View:** Apartments on map (Leaflet/Google Maps)
- [ ] **Discount Codes:** Promo system
- [ ] **Multi-language/currency:** i18n support

---

## 7. Calendar Strategy

### MVP (Phase 1)
- Simple date picker (flatpickr) for booking form
- Disabled dates fetched from `/api/apartments/<id>/availability/` JSON endpoint

### v1 (Phase 2)
- FullCalendar.js for admin calendar:
  - Bookings as events
  - Unavailable days as background events
  - Click to block/unblock dates

---

## 8. Payment Strategy

### Phase 1: Request-to-Book
- Booking created with `status=PENDING`, `payment_status=NOT_REQUIRED`
- Admin confirms or cancels manually
- Email notifications for changes

### Phase 3: Stripe Integration
- After admin confirms → send Stripe payment link
- Webhook updates `payment_status=PAID`
- Store `payment_intent_id` on Booking

---

## 9. Messaging Strategy

### Phase 1: None
- Just `notes` field in Booking for guest message

### Phase 2: Simple Messaging
- Conversation detail page with message list + form
- Page refresh to see new messages

### Phase 3: Real-time (Optional)
- Django Channels WebSocket per conversation

---

## 10. Email Notifications

| Event | Recipient | Content |
|-------|-----------|---------|
| New booking request | Admin | Summary + link to booking |
| Booking confirmed | User | Confirmation details |
| Booking cancelled | User | Cancellation notice |
| New message | Recipient | Notification + link |

> Start synchronous, move to Celery/RQ later.

---

## 11. Security & Compliance

- [x] Django CSRF protection (already enabled)
- [ ] Filter all user views by logged-in user
- [ ] Strict access checks on all endpoints
- [ ] Terms & Conditions page
- [ ] Privacy Policy page
- [ ] Cookie banner (if EU users)
