from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase


class AuthFlowTests(APITestCase):
    def test_register_creates_inactive_user(self):
        resp = self.client.post(reverse('api_register'), {
            'first_name': 'Ana',
            'last_name': 'Pop',
            'username': 'anapop',
            'email': 'ana@example.com',
            'password1': 'StrongPass123',
            'password2': 'StrongPass123',
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        user = User.objects.get(username='anapop')
        self.assertFalse(user.is_active)

    def test_register_rejects_password_mismatch(self):
        resp = self.client.post(reverse('api_register'), {
            'username': 'bob',
            'email': 'bob@example.com',
            'password1': 'StrongPass123',
            'password2': 'Different123',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_activation_activates_user(self):
        user = User.objects.create_user(
            username='pending', password='StrongPass123', email='p@example.com', is_active=False
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        resp = self.client.post(reverse('api_activate'), {'uid': uid, 'token': token}, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_login_returns_tokens(self):
        User.objects.create_user(username='loginuser', password='StrongPass123', is_active=True)
        resp = self.client.post(reverse('api_login'), {
            'username': 'loginuser', 'password': 'StrongPass123',
        }, format='json')
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)
        self.assertIn('user', resp.data)

    def test_login_rejects_bad_credentials(self):
        User.objects.create_user(username='loginuser', password='StrongPass123', is_active=True)
        resp = self.client.post(reverse('api_login'), {
            'username': 'loginuser', 'password': 'wrong',
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_password_reset_request_always_succeeds(self):
        resp = self.client.post(reverse('api_password_reset'), {'email': 'nobody@example.com'}, format='json')
        self.assertEqual(resp.status_code, 200)
