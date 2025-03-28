from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import SubscriptionPlan, UserSubscription
from courses.models import Course
from billing.models import Order, Transaction
import uuid
import json
import requests

class SubscriptionPlanListView(generics.ListAPIView):
    """
    View for listing available subscription plans
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        
        plan_list = []
        for plan in plans:
            # Get courses included in this plan
            included_courses = []
            for course in plan.included_courses.all():
                course_data = {
                    'id': course.id,
                    'title': course.title,
                    'image': course.thumbnail.url if hasattr(course, 'thumbnail') and course.thumbnail else None,
                    'description': course.short_description if hasattr(course, 'short_description') else None
                }
                included_courses.append(course_data)
            
            # Calculate savings compared to individual course prices
            total_course_price = sum(course.price for course in plan.included_courses.all())
            savings = total_course_price - plan.price if total_course_price > plan.price else 0
            
            plan_data = {
                'id': plan.id,
                'name': plan.name,
                'slug': plan.slug,
                'description': plan.description,
                'price': float(plan.price),
                'duration_days': plan.duration_days,
                'included_courses_count': plan.included_courses.count(),
                'included_courses': included_courses,
                'savings': float(savings),
                'savings_percentage': int((savings / total_course_price) * 100) if total_course_price > 0 else 0
            }
            
            plan_list.append(plan_data)
        
        return Response(plan_list)

class SubscriptionPlanDetailView(generics.RetrieveAPIView):
    """
    View for retrieving details of a specific subscription plan
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, slug):
        plan = get_object_or_404(SubscriptionPlan, slug=slug, is_active=True)
        
        # Get detailed course information for this plan
        included_courses = []
        for course in plan.included_courses.all():
            course_data = {
                'id': course.id,
                'title': course.title,
                'slug': course.slug if hasattr(course, 'slug') else None,
                'image': course.thumbnail.url if hasattr(course, 'thumbnail') and course.thumbnail else None,
                'description': course.short_description if hasattr(course, 'short_description') else None,
                'price': float(course.price),
                'instructor': course.instructor.user.get_full_name() if hasattr(course, 'instructor') and course.instructor else None
            }
            included_courses.append(course_data)
        
        # Calculate savings
        total_course_price = sum(course.price for course in plan.included_courses.all())
        savings = total_course_price - plan.price if total_course_price > plan.price else 0
        
        plan_data = {
            'id': plan.id,
            'name': plan.name,
            'slug': plan.slug,
            'description': plan.description,
            'price': float(plan.price),
            'duration_days': plan.duration_days,
            'included_courses_count': plan.included_courses.count(),
            'included_courses': included_courses,
            'created_at': plan.created_at.isoformat(),
            'total_course_value': float(total_course_price),
            'savings': float(savings),
            'savings_percentage': int((savings / total_course_price) * 100) if total_course_price > 0 else 0
        }
        
        return Response(plan_data)

class UserSubscriptionListView(APIView):
    """
    View for listing a user's subscriptions
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        subscriptions = UserSubscription.objects.filter(user=request.user).order_by('-start_date')
        
        subscription_list = []
        for sub in subscriptions:
            # Get courses available in this subscription
            available_courses = []
            for course in sub.subscription_plan.included_courses.all():
                course_data = {
                    'id': course.id,
                    'title': course.title,
                    'slug': course.slug if hasattr(course, 'slug') else None,
                    'image': course.thumbnail.url if hasattr(course, 'thumbnail') and course.thumbnail else None
                }
                available_courses.append(course_data)
            
            # Calculate remaining days
            now = timezone.now()
            remaining_days = (sub.end_date - now).days if sub.end_date > now else 0
            
            subscription_data = {
                'id': sub.id,
                'plan_name': sub.subscription_plan.name,
                'plan_id': sub.subscription_plan.id,
                'start_date': sub.start_date.isoformat(),
                'end_date': sub.end_date.isoformat(),
                'is_active': sub.is_active,
                'is_valid': sub.is_valid(),
                'remaining_days': remaining_days,
                'courses_count': len(available_courses),
                'available_courses': available_courses
            }
            
            subscription_list.append(subscription_data)
        
        return Response(subscription_list)

class UserSubscriptionDetailView(APIView):
    """
    View for retrieving details of a specific user subscription
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, id):
        subscription = get_object_or_404(UserSubscription, id=id, user=request.user)
        
        # Get detailed course information
        available_courses = []
        for course in subscription.subscription_plan.included_courses.all():
            course_data = {
                'id': course.id,
                'title': course.title,
                'slug': course.slug if hasattr(course, 'slug') else None,
                'image': course.thumbnail.url if hasattr(course, 'thumbnail') and course.thumbnail else None,
                'description': course.short_description if hasattr(course, 'short_description') else None,
                'instructor': course.instructor.user.get_full_name() if hasattr(course, 'instructor') and course.instructor else None
            }
            available_courses.append(course_data)
        
        # Calculate remaining days
        now = timezone.now()
        remaining_days = (subscription.end_date - now).days if subscription.end_date > now else 0
        
        # Get related order if available
        order_data = None
        if hasattr(subscription.subscription_plan, 'orders'):
            order = subscription.subscription_plan.orders.filter(user=request.user, status='paid').first()
            if order:
                order_data = {
                    'order_number': order.order_number,
                    'paid_at': order.paid_at.isoformat() if order.paid_at else None,
                    'amount': float(order.final_amount)
                }
        
        subscription_data = {
            'id': subscription.id,
            'plan': {
                'id': subscription.subscription_plan.id,
                'name': subscription.subscription_plan.name,
                'description': subscription.subscription_plan.description,
                'duration_days': subscription.subscription_plan.duration_days,
                'price': float(subscription.subscription_plan.price)
            },
            'start_date': subscription.start_date.isoformat(),
            'end_date': subscription.end_date.isoformat(),
            'is_active': subscription.is_active,
            'is_valid': subscription.is_valid(),
            'remaining_days': remaining_days,
            'progress_percentage': int((subscription.end_date - now).days / subscription.subscription_plan.duration_days * 100) if subscription.is_valid() else 0,
            'courses_count': len(available_courses),
            'available_courses': available_courses,
            'order': order_data
        }
        
        return Response(subscription_data)

class SubscriptionPurchaseView(APIView):
    """
    View for directly purchasing a subscription (bypassing cart)
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, slug):
        subscription_plan = get_object_or_404(SubscriptionPlan, slug=slug, is_active=True)
        user = request.user
        
        # Check if user already has an active subscription to this plan
        existing_subscription = UserSubscription.objects.filter(
            user=user,
            subscription_plan=subscription_plan,
            is_active=True,
            end_date__gt=timezone.now()
        ).first()
        
        if existing_subscription:
            return Response(
                {"error": "You already have an active subscription to this plan"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Create order directly (without cart)
            order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
            
            order = Order.objects.create(
                user=user,
                order_number=order_number,
                order_type='subscription',
                subscription_plan=subscription_plan,
                total_amount=subscription_plan.price,
                final_amount=subscription_plan.price,  # No discounts for direct purchase
                status='pending'
            )
            
            # Create a transaction for payment
            transaction_id = f"TRX-{uuid.uuid4().hex[:12].upper()}"
            transaction = Transaction.objects.create(
                order=order,
                transaction_id=transaction_id,
                amount=order.final_amount,
                payment_method='zarinpal'
            )
            
            # Initiate Zarinpal payment
            zarinpal_response = self.initiate_zarinpal_payment(
                amount=int(order.final_amount),
                description=f"Payment for Subscription: {subscription_plan.name}",
                email=user.email,
                mobile=user.phone,
                order_id=order.order_number,
                transaction_id=transaction_id
            )
            
            if 'errors' in zarinpal_response:
                raise Exception(f"Payment initiation failed: {zarinpal_response['errors']}")
            
            # Store the payment URL and authority in the transaction
            transaction.extra_data = {
                'authority': zarinpal_response.get('data', {}).get('authority'),
                'payment_url': zarinpal_response.get('data', {}).get('payment_url')
            }
            transaction.payment_gateway_reference = zarinpal_response.get('data', {}).get('authority')
            transaction.save()
            
            return Response({
                "message": "Subscription order created successfully",
                "order_id": order.id,
                "order_number": order.order_number,
                "transaction_id": transaction.transaction_id,
                "payment_url": zarinpal_response.get('data', {}).get('payment_url')
            })
                
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def initiate_zarinpal_payment(self, amount, description, email=None, mobile=None, order_id=None, transaction_id=None):
        """
        Initiate a payment through Zarinpal
        """
        zarinpal_merchant_id = settings.ZARINPAL_MERCHANT_ID
        callback_url = settings.SITE_URL + reverse('billing:zarinpal_verify')
        
        # Add order_id and transaction_id as query parameters to callback URL
        if order_id and transaction_id:
            callback_url += f"?order_id={order_id}&transaction_id={transaction_id}"
        
        # Zarinpal API endpoint
        request_url = 'https://api.zarinpal.com/pg/v4/payment/request.json'
        
        # Prepare the request payload
        request_data = {
            'merchant_id': zarinpal_merchant_id,
            'amount': amount,
            'description': description,
            'callback_url': callback_url
        }
        
        if email:
            request_data['metadata'] = {'email': email}
        if mobile:
            if 'metadata' not in request_data:
                request_data['metadata'] = {}
            request_data['metadata']['mobile'] = mobile
        
        # Make the request to Zarinpal
        headers = {'Content-Type': 'application/json'}
        response = requests.post(request_url, data=json.dumps(request_data), headers=headers)
        
        return response.json()
