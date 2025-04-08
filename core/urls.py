"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api/v1/prag/', admin.site.urls),
    path('api/v1/auth/', include(('accounts.urls', 'auth'), namespace='auth')),
    path('api/v1/courses/', include(('courses.urls', 'courses'), namespace='courses')),
    # path('api/v1/taxonomy', include(('taxonomy.urls', 'taxonomy'), namespace='taxonomy')),
    # path('api/v1/subscriptions/', include(('subscriptions.urls', 'subscriptions'), namespace='subscriptions')),
    path('api/v1/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),   
]

# Add static file serving for development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_title = _("Prago site admin (DEV)")
admin.site.site_header = _("Prago administration")
admin.site.index_title = _("Prago Site administration")