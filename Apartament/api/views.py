import logging
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.db.models import Q, Exists, OuterRef
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from rest_framework import viewsets, status, filters
from rest_framework.decorators import api_view, action, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from app.models import (
    Apartment, ApartmentImage, Availability, PricingRule,
    Booking, Conversation, Message, ICalFeed,
)
from app.emails import (
    send_new_booking_notification,
    send_booking_confirmed_notification,
    send_booking_cancelled_notification,
)
from .permissions import IsStaffUser, IsNonStaffUser, IsStaffOrReadOnly
from .serializers import (
    UserSerializer, RegisterSerializer, CustomTokenObtainPairSerializer,
    ApartmentListSerializer, ApartmentDetailSerializer, ApartmentWriteSerializer,
    ApartmentImageSerializer, AvailabilitySerializer, PricingRuleSerializer,
    ICalFeedSerializer, BookingSerializer, BookingCreateSerializer,
    BookingStatusSerializer, BookingEditSerializer,
    ConversationSerializer, ConversationDetailSerializer, MessageSerializer,
)


logger = logging.getLogger('apartbook')


class PasswordResetThrottle(ScopedRateThrottle):
    scope = 'password_reset'


# =============================================================================
# AUTH
# =============================================================================

class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_scope = 'login'


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'register'

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send activation email pointing at the Vue frontend
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        activation_link = f"{frontend}/activate/{uid}/{token}"
        try:
            message = render_to_string('authentication/email_activation/activate_email_message.html', {
                'user': user.username,
                'username': user.username,
                'activation_link': activation_link,
                'domain': frontend,
                'uid': uid,
                'token': token,
            })
            from django.core.mail import EmailMessage
            email = EmailMessage('Activate your account.', message, to=[user.email])
            email.send(fail_silently=False)
        except Exception:
            logger.exception('Failed to send activation email to user id=%s', user.pk)

        return Response(
            {'detail': 'Account created successfully. Please check your email to activate your account.'},
            status=status.HTTP_201_CREATED,
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def activate_account(request):
    uidb64 = request.data.get('uid')
    token = request.data.get('token')
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return Response({'detail': 'Account activated successfully. You can now log in.'})
    return Response(
        {'detail': 'Activation link is invalid or has expired.'},
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([PasswordResetThrottle])
def password_reset_request(request):
    email = request.data.get('email', '')
    form = PasswordResetForm(data={'email': email})
    if form.is_valid():
        frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        for user in form.get_users(email):
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = f"{frontend}/password-reset/{uid}/{token}"
            try:
                from django.core.mail import EmailMessage
                body = render_to_string('authentication/password_reset_email.html', {
                    'user': user, 'reset_link': reset_link,
                }) if _template_exists('authentication/password_reset_email.html') else (
                    f"Use the following link to reset your password:\n{reset_link}"
                )
                EmailMessage('Password reset', body, to=[user.email]).send(fail_silently=False)
            except Exception:
                logger.exception('Failed to send password reset email to user id=%s', user.pk)
    # Always return success to avoid user enumeration
    return Response({'detail': 'If an account exists for that email, a reset link has been sent.'})


def _template_exists(name):
    from django.template.loader import get_template
    try:
        get_template(name)
        return True
    except Exception:
        return False


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    uidb64 = request.data.get('uid')
    token = request.data.get('token')
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is None or not default_token_generator.check_token(user, token):
        return Response({'detail': 'Reset link is invalid or has expired.'},
                        status=status.HTTP_400_BAD_REQUEST)

    form = SetPasswordForm(user, data={
        'new_password1': request.data.get('new_password1'),
        'new_password2': request.data.get('new_password2'),
    })
    if form.is_valid():
        form.save()
        return Response({'detail': 'Password has been reset. You can now log in.'})
    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        user = request.user
        for field in ['first_name', 'last_name', 'email']:
            if field in request.data:
                setattr(user, field, request.data[field])
        user.save()
        profile = getattr(user, 'profile', None)
        if profile:
            if 'phone_country_code' in request.data:
                profile.phone_country_code = request.data['phone_country_code']
            if 'phone_number' in request.data:
                profile.phone_number = request.data['phone_number']
            profile.save()
        return Response(UserSerializer(user).data)


# =============================================================================
# PUBLIC: APARTMENTS
# =============================================================================

class PublicApartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Public apartment browsing with filters."""
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    serializer_class = ApartmentListSerializer

    def get_queryset(self):
        queryset = Apartment.objects.filter(is_active=True)
        params = self.request.query_params

        check_in = params.get('check_in')
        check_out = params.get('check_out')
        if check_in and check_out:
            try:
                ci = datetime.strptime(check_in, '%Y-%m-%d').date()
                co = datetime.strptime(check_out, '%Y-%m-%d').date()
                available_ids = [
                    a.pk for a in queryset
                    if a.is_available_for_booking(ci, co)[0]
                ]
                queryset = queryset.filter(pk__in=available_ids)
            except ValueError:
                pass

        city = params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        country = params.get('country')
        if country:
            queryset = queryset.filter(country__icontains=country)
        guests = params.get('guests')
        if guests and guests.isdigit():
            queryset = queryset.filter(capacity__gte=int(guests))
        min_price = params.get('min_price')
        if min_price:
            try:
                queryset = queryset.filter(base_price_per_night__gte=float(min_price))
            except ValueError:
                pass
        max_price = params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(base_price_per_night__lte=float(max_price))
            except ValueError:
                pass
        return queryset

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ApartmentDetailSerializer
        return ApartmentListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        guests = self.request.query_params.get('guests')
        if guests and guests.isdigit():
            ctx['filtered_guests'] = int(guests)
        return ctx

    @action(detail=False, methods=['get'])
    def featured(self, request):
        apartments = Apartment.objects.filter(is_active=True)[:6]
        serializer = ApartmentListSerializer(apartments, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def availability(self, request, slug=None):
        apartment = self.get_object()
        today = date.today()
        end_date = today + timedelta(days=365)
        calendar_data = apartment.get_calendar_data(today, end_date)
        return Response({
            **calendar_data,
            'base_price': str(apartment.base_price_per_night),
        })

    @action(detail=True, methods=['get'])
    def price(self, request, slug=None):
        apartment = self.get_object()
        check_in_str = request.query_params.get('check_in')
        check_out_str = request.query_params.get('check_out')
        guests_count = request.query_params.get('guests_count', 1)

        if not check_in_str or not check_out_str:
            return Response({'error': 'check_in and check_out are required'}, status=400)
        try:
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
            guests_count = int(guests_count)
        except ValueError:
            return Response({'error': 'Invalid date format or guest count'}, status=400)
        if check_out <= check_in:
            return Response({'error': 'check_out must be after check_in'}, status=400)

        base_price_for_guests = apartment.get_price_for_guests(guests_count)
        total = 0
        current_date = check_in
        daily_prices = []
        while current_date < check_out:
            rule = PricingRule.objects.filter(
                apartment=apartment,
                start_date__lte=current_date,
                end_date__gte=current_date,
            ).order_by('-priority').first()
            day_price = rule.price_per_night if rule else base_price_for_guests
            daily_prices.append({'date': current_date.isoformat(), 'price': str(day_price)})
            total += day_price
            current_date += timedelta(days=1)

        return Response({
            'total_price': str(total),
            'nights': (check_out - check_in).days,
            'base_price': str(base_price_for_guests),
            'pricing_type': apartment.pricing_type,
            'guests_count': guests_count,
            'daily_prices': daily_prices,
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def apartment_ical_export(request, pk):
    apartment = Apartment.objects.filter(pk=pk).first()
    if not apartment:
        return Response({'detail': 'Not found'}, status=404)
    ical_content = apartment.generate_ical()
    response = HttpResponse(ical_content, content_type='text/calendar')
    response['Content-Disposition'] = f'attachment; filename="{apartment.slug}-calendar.ics"'
    return response


# =============================================================================
# USER: BOOKINGS
# =============================================================================

class MyBookingViewSet(viewsets.ModelViewSet):
    """Regular users manage their own bookings."""
    permission_classes = [IsNonStaffUser]
    serializer_class = BookingSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related('apartment').order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='create-for/(?P<slug>[^/.]+)')
    def create_for(self, request, slug=None):
        apartment = Apartment.objects.filter(slug=slug, is_active=True).first()
        if not apartment:
            return Response({'detail': 'Apartment not found'}, status=404)

        serializer = BookingCreateSerializer(data=request.data, context={'apartment': apartment})
        serializer.is_valid(raise_exception=True)

        booking = serializer.save(apartment=apartment, user=request.user)

        send_new_booking_notification(booking)
        return Response(BookingSerializer(booking, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        booking = self.get_object()
        if not booking.can_be_cancelled_by_user():
            return Response(
                {'detail': 'Only pending or confirmed bookings can be cancelled.'},
                status=400,
            )
        booking.status = 'CANCELLED_BY_USER'
        booking.save()
        send_booking_cancelled_notification(booking, cancelled_by='user')
        return Response(BookingSerializer(booking, context={'request': request}).data)


# =============================================================================
# USER: CONVERSATIONS
# =============================================================================

class MyConversationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsNonStaffUser]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).order_by('-updated_at')

    def get_serializer_class(self):
        return ConversationDetailSerializer if self.action == 'retrieve' else ConversationSerializer

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='send')
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        body = (request.data.get('body') or '').strip()
        if not body:
            return Response({'body': ['This field is required.']}, status=400)
        message = Message.objects.create(conversation=conversation, sender=request.user, body=body)
        conversation.save()
        return Response(MessageSerializer(message, context={'request': request}).data, status=201)

    @action(detail=False, methods=['post'], url_path='start/(?P<booking_pk>[^/.]+)')
    def start(self, request, booking_pk=None):
        booking = Booking.objects.filter(pk=booking_pk, user=request.user).first()
        if not booking:
            return Response({'detail': 'Booking not found'}, status=404)
        conversation, _ = Conversation.objects.get_or_create(booking=booking, user=request.user)
        return Response(ConversationSerializer(conversation, context={'request': request}).data)


# =============================================================================
# STAFF: APARTMENTS
# =============================================================================

class StaffApartmentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaffUser]
    queryset = Apartment.objects.all().order_by('-created_at')

    def get_queryset(self):
        today = date.today()
        active_booking_subquery = Booking.objects.filter(
            apartment=OuterRef('pk'),
            status='CONFIRMED',
            check_in__lte=today,
            check_out__gt=today,
        )
        blocked_today_subquery = Availability.objects.filter(
            apartment=OuterRef('pk'),
            date=today,
            is_available=False,
        )
        return Apartment.objects.all().order_by('-created_at').annotate(
            has_active_booking_today=Exists(active_booking_subquery),
            is_blocked_today=Exists(blocked_today_subquery),
        )

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return ApartmentDetailSerializer
        return ApartmentWriteSerializer

    @action(detail=True, methods=['get'])
    def images(self, request, pk=None):
        apartment = self.get_object()
        serializer = ApartmentImageSerializer(
            apartment.images.all().order_by('order'), many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='images/upload')
    def upload_images(self, request, pk=None):
        apartment = self.get_object()
        files = request.FILES.getlist('images')
        if not files:
            return Response({'detail': 'No images provided'}, status=400)
        from django.db.models import Max
        max_order = apartment.images.aggregate(Max('order'))['order__max']
        max_order = max_order if max_order is not None else -1
        created = 0
        for f in files:
            max_order += 1
            ApartmentImage.objects.create(apartment=apartment, image=f, order=max_order, is_main=False)
            created += 1
        if not apartment.images.filter(is_main=True).exists():
            first = apartment.images.order_by('order').first()
            if first:
                first.is_main = True
                first.save()
        serializer = ApartmentImageSerializer(
            apartment.images.all().order_by('order'), many=True, context={'request': request}
        )
        return Response({'uploaded': created, 'images': serializer.data}, status=201)

    @action(detail=True, methods=['post'], url_path='images/reorder')
    def reorder_images(self, request, pk=None):
        apartment = self.get_object()
        order = request.data.get('order', [])
        for index, image_id in enumerate(order):
            img = ApartmentImage.objects.filter(pk=image_id, apartment=apartment).first()
            if img:
                img.order = index
                img.is_main = (index == 0)
                img.save()
        return Response({'success': True})

    @action(detail=True, methods=['delete'], url_path='images/(?P<image_id>[0-9]+)')
    def delete_image(self, request, pk=None, image_id=None):
        apartment = self.get_object()
        img = ApartmentImage.objects.filter(pk=image_id, apartment=apartment).first()
        if not img:
            return Response({'detail': 'Image not found'}, status=404)
        img.delete()
        return Response(status=204)

    # ---- Availability ----
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        apartment = self.get_object()
        today = date.today()
        three_months = today + timedelta(days=90)
        qs = apartment.availability.filter(date__gte=today, date__lte=three_months).order_by('date')
        return Response(AvailabilitySerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], url_path='block')
    def block_dates(self, request, pk=None):
        apartment = self.get_object()
        try:
            start_date = date.fromisoformat(request.data.get('start_date'))
            end_date = date.fromisoformat(request.data.get('end_date'))
        except (TypeError, ValueError):
            return Response({'detail': 'Invalid dates'}, status=400)
        note = (request.data.get('note') or '').strip()

        if start_date > end_date:
            return Response({'detail': 'Start date must be before end date'}, status=400)
        if start_date < date.today():
            return Response({'detail': 'Cannot block past dates'}, status=400)

        conflicting = Booking.objects.filter(
            apartment=apartment, status__in=['PENDING', 'CONFIRMED'],
            check_in__lte=end_date, check_out__gt=start_date,
        )
        if conflicting.exists():
            return Response({'detail': 'Cannot block nights that have existing bookings'}, status=400)

        current = start_date
        count = 0
        while current <= end_date:
            Availability.objects.update_or_create(
                apartment=apartment, date=current,
                defaults={'is_available': False, 'note': note or 'Blocked'},
            )
            count += 1
            current += timedelta(days=1)
        return Response({'success': True, 'blocked': count})

    @action(detail=True, methods=['delete'], url_path='availability/(?P<availability_id>[0-9]+)')
    def unblock_date(self, request, pk=None, availability_id=None):
        apartment = self.get_object()
        entry = Availability.objects.filter(pk=availability_id, apartment=apartment).first()
        if not entry:
            return Response({'detail': 'Not found'}, status=404)
        entry.delete()
        return Response(status=204)

    # ---- Calendar events ----
    @action(detail=True, methods=['get'], url_path='calendar-events')
    def calendar_events(self, request, pk=None):
        apartment = self.get_object()
        return Response(_apartment_calendar_events(apartment))

    # ---- iCal feeds ----
    @action(detail=True, methods=['get', 'post'], url_path='ical-feeds')
    def ical_feeds(self, request, pk=None):
        apartment = self.get_object()
        if request.method == 'POST':
            serializer = ICalFeedSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            feed = serializer.save(apartment=apartment)
            success, message = feed.sync()
            return Response(
                {'feed': ICalFeedSerializer(feed).data, 'sync_success': success, 'sync_message': message},
                status=201,
            )
        feeds = apartment.ical_feeds.all()
        export_url = request.build_absolute_uri(f'/api/apartments/{apartment.pk}/calendar.ics')
        return Response({'feeds': ICalFeedSerializer(feeds, many=True).data, 'export_url': export_url})

    @action(detail=True, methods=['post'], url_path='ical-feeds/(?P<feed_id>[0-9]+)/sync')
    def sync_feed(self, request, pk=None, feed_id=None):
        apartment = self.get_object()
        feed = ICalFeed.objects.filter(pk=feed_id, apartment=apartment).first()
        if not feed:
            return Response({'detail': 'Feed not found'}, status=404)
        success, message = feed.sync()
        return Response({'success': success, 'message': message})

    @action(detail=True, methods=['delete'], url_path='ical-feeds/(?P<feed_id>[0-9]+)')
    def delete_feed(self, request, pk=None, feed_id=None):
        apartment = self.get_object()
        feed = ICalFeed.objects.filter(pk=feed_id, apartment=apartment).first()
        if not feed:
            return Response({'detail': 'Feed not found'}, status=404)
        feed.delete()
        return Response(status=204)


def _guest_display_name(user):
    """Return "Last Name First Name" for calendar labels, falling back to username."""
    name = f"{user.last_name} {user.first_name}".strip()
    return name or user.username


def _apartment_calendar_events(apartment):
    events = []
    bookings = Booking.objects.filter(apartment=apartment, status__in=['PENDING', 'CONFIRMED'])
    for booking in bookings:
        color = '#198754' if booking.status == 'CONFIRMED' else '#ffc107'
        events.append({
            'id': f'booking-{booking.pk}',
            'title': f'{_guest_display_name(booking.user)} ({booking.guests_count} guests)',
            'start': booking.check_in.isoformat(),
            # Add one day so checkout morning can be rendered as a short tail.
            'end': (booking.check_out + timedelta(days=1)).isoformat(),
            'color': color,
            'url': f'/staff/bookings/{booking.pk}',
            'extendedProps': {'type': 'booking', 'status': booking.status},
        })
    blocked_dates = Availability.objects.filter(apartment=apartment, is_available=False)
    for blocked in blocked_dates:
        events.append({
            'id': f'blocked-{blocked.pk}',
            'title': blocked.note or 'Blocked',
            'start': blocked.date.isoformat(),
            'end': blocked.date.isoformat(),
            'color': '#dc3545',
            'display': 'background',
            'extendedProps': {'type': 'blocked'},
        })
    return events


@api_view(['GET'])
@permission_classes([IsStaffUser])
def staff_global_calendar_events(request):
    events = []
    bookings = Booking.objects.filter(status__in=['PENDING', 'CONFIRMED']).select_related('apartment', 'user')
    for booking in bookings:
        color = '#198754' if booking.status == 'CONFIRMED' else '#ffc107'
        title = f'{booking.apartment.title} - {_guest_display_name(booking.user)} ({booking.guests_count} guests)'
        events.append({
            'id': f'booking-{booking.pk}',
            'title': title,
            'start': booking.check_in.isoformat(),
            # Add one day so checkout morning can be rendered as a short tail.
            'end': (booking.check_out + timedelta(days=1)).isoformat(),
            'color': color,
            'url': f'/staff/bookings/{booking.pk}',
            'extendedProps': {
                'type': 'booking',
                'status': booking.status,
                'apartment': booking.apartment.title,
                'apartmentId': booking.apartment.pk,
            },
        })
    blocked_dates = Availability.objects.filter(is_available=False).select_related('apartment')
    for blocked in blocked_dates:
        events.append({
            'id': f'blocked-{blocked.pk}',
            'title': f'{blocked.apartment.title} - {blocked.note or "Blocked"}',
            'start': blocked.date.isoformat(),
            'end': blocked.date.isoformat(),
            'color': '#dc3545',
            'display': 'background',
            'extendedProps': {'type': 'blocked', 'apartment': blocked.apartment.title},
        })
    return Response(events)


# =============================================================================
# STAFF: BOOKINGS
# =============================================================================

class StaffBookingViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStaffUser]
    serializer_class = BookingSerializer

    def get_queryset(self):
        queryset = Booking.objects.all().select_related('apartment', 'user').order_by('-created_at')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        apartment_id = self.request.query_params.get('apartment')
        if apartment_id:
            queryset = queryset.filter(apartment_id=apartment_id)
        return queryset

    @action(detail=True, methods=['post'], url_path='status')
    def update_status(self, request, pk=None):
        booking = self.get_object()
        old_status = booking.status
        serializer = BookingStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        booking.status = new_status
        booking.save()
        if new_status == 'CONFIRMED' and old_status != 'CONFIRMED':
            send_booking_confirmed_notification(booking)
        elif new_status == 'CANCELLED_BY_ADMIN':
            send_booking_cancelled_notification(booking, cancelled_by='admin')
        return Response(BookingSerializer(booking, context={'request': request}).data)

    @action(detail=True, methods=['patch'], url_path='edit')
    def edit(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingEditSerializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        total_price, price_breakdown = booking.calculate_total_price()
        booking.total_price = total_price
        booking.price_breakdown = price_breakdown
        booking.save()
        return Response(BookingSerializer(booking, context={'request': request}).data)


# =============================================================================
# STAFF: CONVERSATIONS
# =============================================================================

class StaffConversationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsStaffUser]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.all().order_by('-updated_at')

    def get_serializer_class(self):
        return ConversationDetailSerializer if self.action == 'retrieve' else ConversationSerializer

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response(self.get_serializer(conversation).data)

    @action(detail=True, methods=['post'], url_path='send')
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        body = (request.data.get('body') or '').strip()
        if not body:
            return Response({'body': ['This field is required.']}, status=400)
        message = Message.objects.create(conversation=conversation, sender=request.user, body=body)
        conversation.save()
        return Response(MessageSerializer(message, context={'request': request}).data, status=201)


# =============================================================================
# MISC
# =============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def config_view(request):
    """Expose config the frontend needs (currencies, languages)."""
    return Response({
        'currencies': settings.CURRENCIES,
        'default_currency': settings.DEFAULT_CURRENCY,
        'languages': [{'code': c, 'name': str(n)} for c, n in settings.LANGUAGES],
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_counts(request):
    """Unread message counts for the navbar badge."""
    if request.user.is_staff:
        count = Message.objects.filter(is_read=False, sender__is_staff=False).count()
    else:
        count = Message.objects.filter(
            conversation__user=request.user, is_read=False, sender__is_staff=True,
        ).count()
    return Response({'unread_messages': count})


# =============================================================================
# CRON ENDPOINTS (for external cron services like cron-job.org)
# =============================================================================

def _check_cron_key(request):
    """Validate the cron secret key. Returns an error Response or None if valid."""
    provided_key = request.GET.get('key', '')
    expected_key = getattr(settings, 'CRON_SECRET_KEY', None)
    if not expected_key:
        return Response({'success': False, 'error': 'CRON_SECRET_KEY not configured'}, status=500)
    if provided_key != expected_key:
        return Response({'success': False, 'error': 'Invalid key'}, status=403)
    return None


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def cron_sync_ical(request):
    """Cron endpoint to sync all due iCal feeds. URL: /api/cron/sync-ical/?key=SECRET"""
    import time
    from django.utils import timezone

    error = _check_cron_key(request)
    if error:
        return error

    start_time = time.time()
    now = timezone.now()
    results = []

    feeds = ICalFeed.objects.filter(
        is_active=True, is_circuit_open=False,
    ).filter(
        Q(next_sync_at__isnull=True) | Q(next_sync_at__lte=now)
    ).order_by('priority', 'next_sync_at')[:10]

    half_open = ICalFeed.objects.filter(
        is_active=True, is_circuit_open=True,
        circuit_opened_at__lte=now - timedelta(hours=1),
    )[:2]

    for feed in list(feeds) + list(half_open):
        try:
            success, message = feed.sync()
            results.append({'feed': f"{feed.apartment.title} - {feed.name}", 'success': success, 'message': message})
        except Exception as e:
            logger.exception('iCal sync failed for feed id=%s', feed.pk)
            results.append({'feed': f"{feed.apartment.title} - {feed.name}", 'success': False, 'message': str(e)})

    return Response({
        'success': True,
        'synced': len(results),
        'duration_seconds': round(time.time() - start_time, 2),
        'results': results,
    })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def cron_auto_complete_bookings(request):
    """Cron endpoint to auto-complete past bookings. URL: /api/cron/auto-complete/?key=SECRET"""
    error = _check_cron_key(request)
    if error:
        return error

    today = date.today()
    bookings_to_complete = Booking.objects.filter(status='CONFIRMED', check_out__lt=today)
    count = bookings_to_complete.count()
    if count:
        bookings_to_complete.update(status='COMPLETED')
    return Response({'success': True, 'completed': count})


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def cron_cleanup_old_events(request):
    """Cron endpoint to clean up old iCal events. URL: /api/cron/cleanup/?key=SECRET"""
    from app.models import ICalEvent

    error = _check_cron_key(request)
    if error:
        return error

    cutoff = date.today() - timedelta(days=90)
    deleted_count, _ = ICalEvent.objects.filter(dtend__lt=cutoff).delete()
    return Response({'success': True, 'deleted': deleted_count})
