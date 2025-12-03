from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# Non-i18n patterns (API endpoints, admin, etc.)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching
]

# i18n patterns (user-facing pages)
urlpatterns += i18n_patterns(
    path('', include('app.urls')),
    path('authentication/', include('authentication.urls')),
    prefix_default_language=False,  # Don't add /en/ prefix for default language
)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)