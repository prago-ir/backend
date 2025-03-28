from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Cart endpoints
    path('cart/', views.CartView.as_view(), name='cart'),
    path('cart/add/', views.AddToCartView.as_view(), name='add_to_cart'),
    path('cart/remove/', views.RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('cart/apply-coupon/', views.ApplyCouponView.as_view(), name='apply_coupon'),
    path('cart/remove-coupon/', views.RemoveCouponView.as_view(), name='remove_coupon'),
    path('cart/checkout/', views.CartCheckoutView.as_view(), name='checkout'),

    # Payment endpoints
    path('payment/zarinpal/verify/', views.ZarinpalVerifyView.as_view(), name='zarinpal_verify'),

    # Order endpoints
    path('orders/', views.OrderListView.as_view(), name='order_list'),
    path('orders/<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),
]
