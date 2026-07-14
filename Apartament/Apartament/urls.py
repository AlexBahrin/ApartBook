from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.cache import never_cache


@never_cache
def spa_index(request):
    """Serve the built Vue SPA entry point (production)."""
    index_file = settings.FRONTEND_DIST / 'index.html'
    if not index_file.exists():
        return HttpResponseNotFound(
            'Vue frontend build not found. Run "npm run build" in the frontend/ directory, '
            'or use the Vite dev server (npm run dev) during development.'
        )
    return HttpResponse(index_file.read_text(encoding='utf-8'))


# Non-i18n patterns (API endpoints, admin, etc.)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Vue SPA REST API
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching
]

# i18n patterns (user-facing pages)
urlpatterns += i18n_patterns(
    path('', include('app.urls')),
    path('authentication/', include('authentication.urls')),
)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Vue SPA fallback: serve the built app for any route not handled above
# (API, admin, static, media, i18n and legacy /<lang>/ pages take precedence).
urlpatterns += [
    re_path(r'^.*$', spa_index, name='spa'),
]