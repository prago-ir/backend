from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Subscription plan endpoints
    path('plans/', views.SubscriptionPlanListView.as_view(), name='plan_list'),
    path('plans/<slug:slug>/', views.SubscriptionPlanDetailView.as_view(), name='plan_detail'),
    
    # User subscription endpoints
    path('my-subscriptions/', views.UserSubscriptionListView.as_view(), name='user_subscription_list'),
    path('my-subscriptions/<int:id>/', views.UserSubscriptionDetailView.as_view(), name='user_subscription_detail'),
    
    # Direct subscription purchase endpoint
    path('plans/<slug:slug>/purchase/', views.SubscriptionPurchaseView.as_view(), name='subscription_purchase'),
]
