from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase

from app.models import Apartment, Booking


def make_apartment(**overrides):
    defaults = dict(
        title='Test Apartment',
        description='A nice place',
        address='Str. Test 1',
        city='Iasi',
        country='Romania',
        capacity=4,
        bedrooms=2,
        bathrooms=1,
        pricing_type='APARTMENT',
        base_price_per_night=Decimal('100.00'),
        is_active=True,
    )
    defaults.update(overrides)
    return Apartment.objects.create(**defaults)


class BookingLifecycleTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='guest', password='pass12345', email='guest@example.com', is_active=True
        )
        self.apartment = make_apartment()
        self.check_in = date.today() + timedelta(days=5)
        self.check_out = self.check_in + timedelta(days=3)

    def _create_booking(self, status='PENDING'):
        booking = Booking(
            apartment=self.apartment,
            user=self.user,
            check_in=self.check_in,
            check_out=self.check_out,
            guests_count=2,
            status=status,
        )
        total, breakdown = booking.calculate_total_price()
        booking.total_price = total
        booking.price_breakdown = breakdown
        booking.save()
        return booking

    def test_create_booking_via_api(self):
        self.client.force_authenticate(self.user)
        url = reverse('my-booking-create-for', kwargs={'slug': self.apartment.slug})
        resp = self.client.post(url, {
            'check_in': self.check_in.isoformat(),
            'check_out': self.check_out.isoformat(),
            'guests_count': 2,
            'notes': 'Please',
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.status, 'PENDING')
        self.assertEqual(booking.total_price, Decimal('300.00'))

    def test_create_booking_rejects_over_capacity(self):
        self.client.force_authenticate(self.user)
        url = reverse('my-booking-create-for', kwargs={'slug': self.apartment.slug})
        resp = self.client.post(url, {
            'check_in': self.check_in.isoformat(),
            'check_out': self.check_out.isoformat(),
            'guests_count': 10,
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_user_can_cancel_pending_booking(self):
        booking = self._create_booking(status='PENDING')
        self.client.force_authenticate(self.user)
        url = reverse('my-booking-cancel', kwargs={'pk': booking.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED_BY_USER')

    def test_user_can_cancel_confirmed_booking(self):
        booking = self._create_booking(status='CONFIRMED')
        self.client.force_authenticate(self.user)
        url = reverse('my-booking-cancel', kwargs={'pk': booking.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'CANCELLED_BY_USER')

    def test_user_cannot_cancel_completed_booking(self):
        booking = self._create_booking(status='COMPLETED')
        self.client.force_authenticate(self.user)
        url = reverse('my-booking-cancel', kwargs={'pk': booking.pk})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'COMPLETED')

    def test_cannot_access_other_users_booking(self):
        other = User.objects.create_user(username='other', password='pass12345', is_active=True)
        booking = self._create_booking(status='PENDING')
        self.client.force_authenticate(other)
        url = reverse('my-booking-detail', kwargs={'pk': booking.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)


class BookingModelTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='guest', password='pass12345', is_active=True)
        self.apartment = make_apartment()

    def test_cancellable_helpers(self):
        booking = Booking(
            apartment=self.apartment, user=self.user,
            check_in=date.today(), check_out=date.today() + timedelta(days=1),
            guests_count=1, total_price=Decimal('100.00'), status='PENDING',
        )
        self.assertTrue(booking.can_be_cancelled_by_user())
        booking.status = 'CONFIRMED'
        self.assertTrue(booking.can_be_cancelled_by_user())
        booking.status = 'COMPLETED'
        self.assertFalse(booking.can_be_cancelled_by_user())


class PermissionTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='pass12345', is_staff=True, is_active=True)
        self.guest = User.objects.create_user(username='guest', password='pass12345', is_active=True)
        self.apartment = make_apartment()

    def test_guest_cannot_access_staff_bookings(self):
        self.client.force_authenticate(self.guest)
        resp = self.client.get(reverse('staff-booking-list'))
        self.assertEqual(resp.status_code, 403)

    def test_staff_can_list_bookings(self):
        self.client.force_authenticate(self.staff)
        resp = self.client.get(reverse('staff-booking-list'))
        self.assertEqual(resp.status_code, 200)

    def test_staff_cannot_create_booking(self):
        self.client.force_authenticate(self.staff)
        url = reverse('my-booking-create-for', kwargs={'slug': self.apartment.slug})
        resp = self.client.post(url, {
            'check_in': (date.today() + timedelta(days=2)).isoformat(),
            'check_out': (date.today() + timedelta(days=4)).isoformat(),
            'guests_count': 1,
        }, format='json')
        self.assertIn(resp.status_code, (403, 404))
