from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [

    # Payment endpoints
    path('payment/zarinpal/request/',
         views.ZarinpalPaymentView.as_view(), name='zarinpal_request'),
    path('payment/zarinpal/verify/',
         views.ZarinpalVerifyView.as_view(), name='zarinpal_verify'),

    # Subscription purchase endpoint
    path('subscription/purchase/', views.SubscriptionPurchaseView.as_view(),
         name='subscription_purchase'),

    # Order endpoints
    #     path('orders/', views.OrderListView.as_view(), name='order_list'),
    #     path('orders/<str:order_number>/',
    #          views.OrderDetailView.as_view(), name='order_detail'),
]
