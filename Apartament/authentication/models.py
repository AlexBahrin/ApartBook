from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Extended user profile to store additional information like phone number."""
    
    COUNTRY_CODES = [
        ('+40', '🇷🇴 Romania (+40)'),
        ('+373', '🇲🇩 Moldova (+373)'),
        ('+380', '🇺🇦 Ukraine (+380)'),
        ('+1', '🇺🇸 USA/Canada (+1)'),
        ('+44', '🇬🇧 UK (+44)'),
        ('+49', '🇩🇪 Germany (+49)'),
        ('+33', '🇫🇷 France (+33)'),
        ('+34', '🇪🇸 Spain (+34)'),
        ('+39', '🇮🇹 Italy (+39)'),
        ('+43', '🇦🇹 Austria (+43)'),
        ('+41', '🇨🇭 Switzerland (+41)'),
        ('+31', '🇳🇱 Netherlands (+31)'),
        ('+32', '🇧🇪 Belgium (+32)'),
        ('+48', '🇵🇱 Poland (+48)'),
        ('+36', '🇭🇺 Hungary (+36)'),
        ('+420', '🇨🇿 Czech Republic (+420)'),
        ('+359', '🇧🇬 Bulgaria (+359)'),
        ('+30', '🇬🇷 Greece (+30)'),
        ('+90', '🇹🇷 Turkey (+90)'),
        ('+7', '🇷🇺 Russia (+7)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_country_code = models.CharField(max_length=10, choices=COUNTRY_CODES, default='+40')
    phone_number = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    def get_full_phone(self):
        """Return the full phone number with country code."""
        if self.phone_number:
            return f"{self.phone_country_code} {self.phone_number}"
        return ""


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile when a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the UserProfile when the User is saved."""
    if hasattr(instance, 'profile'):
        instance.profile.save()
