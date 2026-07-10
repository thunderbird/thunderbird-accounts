from django.urls import path

from thunderbird_accounts.subscription import views


authenticated_urlpatterns = [
    path('subscription/paddle/complete/', views.paddle_transaction_complete, name='paddle_completed'),
    path('api/v1/subscription/paddle/info/', views.get_paddle_information, name='paddle_info'),
    path('api/v1/subscription/paddle/tx/set/', views.set_paddle_transaction_id, name='paddle_txid'),
    path('api/v1/subscription/paddle/tx/is-done/', views.is_paddle_transaction_done, name='paddle_is_done'),
]

paddle_portal_urlpatterns = [
    path('api/v1/subscription/paddle/portal/', views.get_paddle_portal_link, name='paddle_portal'),
]

subscription_plan_info_urlpatterns = [
    path('api/v1/subscription/plan/info/', views.get_subscription_plan_info, name='subscription_plan_info'),
]

public_urlpatterns = [
    path('api/v1/subscription/paddle/webhook/', views.handle_paddle_webhook, name='paddle_webhook'),
]
