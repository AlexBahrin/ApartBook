from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
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


def robots_txt(request):
    """Serve robots.txt with a link to the sitemap."""
    sitemap_url = request.build_absolute_uri('/sitemap.xml')
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /api/',
        'Allow: /',
        f'Sitemap: {sitemap_url}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')


def sitemap_xml(request):
    """Serve a basic sitemap covering public pages and active apartments."""
    from app.models import Apartment

    urls = [request.build_absolute_uri('/'), request.build_absolute_uri('/apartments')]
    for slug in Apartment.objects.filter(is_active=True).values_list('slug', flat=True):
        urls.append(request.build_absolute_uri(f'/apartments/{slug}'))

    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in urls:
        body.append(f'  <url><loc>{url}</loc></url>')
    body.append('</urlset>')
    return HttpResponse('\n'.join(body), content_type='application/xml')


# API endpoints, admin and language switching.
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Vue SPA REST API
    path('i18n/', include('django.conf.urls.i18n')),  # Language switching
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Vue SPA fallback: serve the built app for any route not handled above
# (API, admin, static, media and i18n take precedence).
urlpatterns += [
    re_path(r'^.*$', spa_index, name='spa'),
]