from django.urls import path

from thunderbird_accounts.legal import views


authenticated_urlpatterns = [
    path('api/v1/legal/current/', views.get_current_legal_docs, name='legal_current'),
    path('api/v1/legal/accept/', views.accept_legal_docs, name='legal_accept'),
    path('api/v1/legal/decline/', views.decline_legal_docs, name='legal_decline'),
]
