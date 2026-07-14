from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from app.models import (
    Apartment, ApartmentImage, Availability, PricingRule,
    Booking, Conversation, Message, ICalFeed,
)
from authentication.models import UserProfile


# =============================================================================
# USERS / AUTH
# =============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone_country_code', 'phone_number']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_staff', 'full_name', 'profile',
        ]

    def get_full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or obj.username


class RegisterSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    phone_country_code = serializers.CharField(required=False, default='+40')
    phone_number = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'username', 'email',
            'phone_country_code', 'phone_number', 'password1', 'password2',
        ]

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with that username already exists.')
        return value

    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with that email already exists.')
        return value

    def validate(self, attrs):
        if attrs['password1'] != attrs['password2']:
            raise serializers.ValidationError({'password2': 'The two password fields do not match.'})
        validate_password(attrs['password1'])
        return attrs

    def create(self, validated_data):
        phone_country_code = validated_data.pop('phone_country_code', '+40')
        phone_number = validated_data.pop('phone_number', '')
        password = validated_data.pop('password1')
        validated_data.pop('password2', None)

        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            is_active=False,  # requires email activation
        )
        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.phone_country_code = phone_country_code
        profile.phone_number = phone_number
        profile.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """JWT login that also returns the user payload."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


# =============================================================================
# APARTMENTS
# =============================================================================

class ApartmentImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApartmentImage
        fields = ['id', 'image', 'is_main', 'order']


class ApartmentListSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()
    display_price = serializers.SerializerMethodField()

    class Meta:
        model = Apartment
        fields = [
            'id', 'title', 'slug', 'city', 'country', 'address',
            'capacity', 'bedrooms', 'bathrooms', 'pricing_type',
            'base_price_per_night', 'display_price', 'main_image', 'is_active',
        ]

    def get_main_image(self, obj):
        image = obj.get_main_image()
        if not image:
            return None
        request = self.context.get('request')
        url = image.image.url
        return request.build_absolute_uri(url) if request else url

    def get_display_price(self, obj):
        guests = self.context.get('filtered_guests')
        if guests:
            return str(obj.get_price_for_guests(guests))
        return str(obj.get_display_price())


class ApartmentDetailSerializer(serializers.ModelSerializer):
    images = ApartmentImageSerializer(many=True, read_only=True)
    calendar = serializers.SerializerMethodField()

    class Meta:
        model = Apartment
        fields = [
            'id', 'title', 'slug', 'description', 'address', 'city', 'country',
            'latitude', 'longitude', 'capacity', 'bedrooms', 'bathrooms',
            'amenities', 'pricing_type', 'base_price_per_night', 'price_per_guest',
            'is_active', 'images', 'calendar',
        ]

    def get_calendar(self, obj):
        today = date.today()
        end = today + timedelta(days=90)
        return obj.get_calendar_data(today, end)


class ApartmentWriteSerializer(serializers.ModelSerializer):
    """Create/update apartments (staff)."""
    amenities = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )

    class Meta:
        model = Apartment
        fields = [
            'id', 'title', 'description', 'address', 'city', 'country',
            'latitude', 'longitude', 'capacity', 'bedrooms', 'bathrooms',
            'amenities', 'pricing_type', 'base_price_per_night',
            'price_per_guest', 'is_active',
        ]

    def validate(self, attrs):
        pricing_type = attrs.get('pricing_type', getattr(self.instance, 'pricing_type', 'APARTMENT'))
        base_price = attrs.get('base_price_per_night', getattr(self.instance, 'base_price_per_night', None))
        price_per_guest = attrs.get('price_per_guest', getattr(self.instance, 'price_per_guest', None))

        if pricing_type == 'GUEST':
            if not price_per_guest:
                raise serializers.ValidationError(
                    {'price_per_guest': 'Set prices for each guest count when using per-guest pricing.'}
                )
            if not base_price or base_price <= 0:
                if price_per_guest and '1' in price_per_guest:
                    attrs['base_price_per_night'] = Decimal(str(price_per_guest['1']))
                else:
                    attrs['base_price_per_night'] = Decimal('1.00')
        else:
            if not base_price or base_price <= 0:
                raise serializers.ValidationError(
                    {'base_price_per_night': 'Please set a base price per night.'}
                )
            attrs['price_per_guest'] = {}
        return attrs


# =============================================================================
# AVAILABILITY / PRICING / ICAL
# =============================================================================

class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = [
            'id', 'date', 'is_available', 'min_stay_nights',
            'max_stay_nights', 'note', 'source',
        ]
        read_only_fields = ['source']


class PricingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingRule
        fields = [
            'id', 'start_date', 'end_date', 'weekday',
            'rule_type', 'price_per_night', 'priority',
        ]


class ICalFeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ICalFeed
        fields = [
            'id', 'name', 'url', 'is_active', 'last_synced',
            'last_sync_status', 'sync_error', 'is_circuit_open',
        ]
        read_only_fields = [
            'last_synced', 'last_sync_status', 'sync_error', 'is_circuit_open',
        ]


# =============================================================================
# BOOKINGS
# =============================================================================

class BookingApartmentMiniSerializer(serializers.ModelSerializer):
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Apartment
        fields = ['id', 'title', 'slug', 'city', 'country', 'main_image']

    def get_main_image(self, obj):
        image = obj.get_main_image()
        if not image:
            return None
        request = self.context.get('request')
        url = image.image.url
        return request.build_absolute_uri(url) if request else url


class BookingSerializer(serializers.ModelSerializer):
    apartment = BookingApartmentMiniSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    nights = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    has_conversation = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'apartment', 'user', 'check_in', 'check_out', 'guests_count',
            'total_price', 'price_breakdown', 'currency', 'status', 'status_display',
            'payment_status', 'notes', 'nights', 'has_conversation',
            'created_at', 'updated_at',
        ]

    def get_nights(self, obj):
        return obj.get_nights()

    def get_has_conversation(self, obj):
        return hasattr(obj, 'conversation') and obj.conversation is not None


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['check_in', 'check_out', 'guests_count', 'notes']

    def validate(self, attrs):
        apartment = self.context['apartment']
        check_in = attrs['check_in']
        check_out = attrs['check_out']
        guests = attrs['guests_count']

        if check_out <= check_in:
            raise serializers.ValidationError({'check_out': 'Check-out must be after check-in.'})
        if check_in < date.today():
            raise serializers.ValidationError({'check_in': 'Check-in cannot be in the past.'})
        if guests > apartment.capacity:
            raise serializers.ValidationError(
                {'guests_count': f'Number of guests exceeds apartment capacity ({apartment.capacity}).'}
            )
        is_available, message = apartment.is_available_for_booking(check_in, check_out)
        if not is_available:
            raise serializers.ValidationError({'non_field_errors': [message]})
        return attrs


class BookingStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['CONFIRMED', 'CANCELLED_BY_ADMIN'])


class BookingEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['check_in', 'check_out', 'guests_count']

    def validate(self, attrs):
        check_in = attrs.get('check_in', self.instance.check_in)
        check_out = attrs.get('check_out', self.instance.check_out)
        if check_out <= check_in:
            raise serializers.ValidationError({'check_out': 'Check-out must be after check-in.'})
        return attrs


# =============================================================================
# CONVERSATIONS / MESSAGES
# =============================================================================

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender', 'body', 'is_read', 'is_mine', 'created_at']

    def get_is_mine(self, obj):
        request = self.context.get('request')
        return bool(request and request.user == obj.sender)


class ConversationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    apartment_title = serializers.SerializerMethodField()
    booking_id = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'user', 'booking_id', 'apartment_title',
            'last_message', 'unread_count', 'created_at', 'updated_at',
        ]

    def get_last_message(self, obj):
        msg = obj.get_last_message()
        if not msg:
            return None
        return {'body': msg.body, 'created_at': msg.created_at, 'sender': msg.sender.username}

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request:
            return obj.get_unread_count(request.user)
        return 0

    def get_apartment_title(self, obj):
        return obj.booking.apartment.title if obj.booking else None

    def get_booking_id(self, obj):
        return obj.booking_id


class ConversationDetailSerializer(ConversationSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']
