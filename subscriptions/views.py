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
from .serializers import SubscriptionPlanSerializer  # Import your serializer
import uuid
import json
import requests
import logging

logger = logging.getLogger(__name__)


class SubscriptionPlanListView(generics.ListAPIView):
    """
    View for listing available subscription plans
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)  # Use queryset
    serializer_class = SubscriptionPlanSerializer  # Use the serializer
    permission_classes = [permissions.AllowAny]

    # Optional: Add logging here if you want to debug this view specifically
    # def list(self, request, *args, **kwargs):
    #     response = super().list(request, *args, **kwargs)
    #     if hasattr(response, 'data') and response.data:
    #         logger.info("---- SubscriptionPlanListView (Generic) Response Data ----")
    #         if isinstance(response.data, list) and len(response.data) > 0:
    #             first_item = response.data[0]
    #             if isinstance(first_item, dict):
    #                 cp = first_item.get('current_price')
    #                 op = first_item.get('original_price')
    #                 logger.info(f"GENERIC VIEW LOG - First item current_price: '{cp}', Type: {type(cp)}")
    #                 logger.info(f"GENERIC VIEW LOG - First item original_price: '{op}', Type: {type(op)}")
    #     return response


class PragoPlusPlansView(APIView):
    """
    View for listing only the three Prago Plus subscription plans.
    This view will now use the SubscriptionPlanSerializer.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        prago_plans_slugs = ['prago-plus-monthly',
                             'prago-plus-3-month', 'prago-plus-6-month']

        # Fetch plans in the desired order if possible, or sort later
        # A more robust way to order if slugs don't guarantee order:
        from django.db.models import Case, When
        preserved_order = Case(*[When(slug=slug, then=pos)
                               for pos, slug in enumerate(prago_plans_slugs)])
        plans = SubscriptionPlan.objects.filter(
            slug__in=prago_plans_slugs, is_active=True
        ).order_by(preserved_order)

        # Use the serializer
        serializer = SubscriptionPlanSerializer(
            plans, many=True, context={'request': request})
        serialized_data = serializer.data

        # Log the data produced by the serializer for this view
        logger.info(
            "---- PragoPlusPlansView Response Data (using serializer) ----")
        if isinstance(serialized_data, list) and len(serialized_data) > 0:
            first_item = serialized_data[0]
            if isinstance(first_item, dict):
                cp = first_item.get('current_price')
                op = first_item.get('original_price')
                logger.info(
                    f"PRAGO PLUS VIEW LOG - First item current_price: '{cp}', Type: {type(cp)}")
                logger.info(
                    f"PRAGO PLUS VIEW LOG - First item original_price: '{op}', Type: {type(op)}")
        logger.info("---- End PragoPlusPlansView Response Data ----")

        return Response(serialized_data)


class SubscriptionPlanDetailView(generics.RetrieveAPIView):
    """
    View for retrieving details of a specific subscription plan
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)  # Use queryset
    serializer_class = SubscriptionPlanSerializer  # Use the serializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'  # Ensure this matches your URL conf

    # Optional: Add logging here if you want to debug this view specifically
    # def retrieve(self, request, *args, **kwargs):
    #     response = super().retrieve(request, *args, **kwargs)
    #     if hasattr(response, 'data') and response.data:
    #         logger.info(f"---- SubscriptionPlanDetailView ({kwargs.get('slug')}) Response Data ----")
    #         if isinstance(response.data, dict):
    #             cp = response.data.get('current_price')
    #             op = response.data.get('original_price')
    #             logger.info(f"DETAIL VIEW LOG - current_price: '{cp}', Type: {type(cp)}")
    #             logger.info(f"DETAIL VIEW LOG - original_price: '{op}', Type: {type(op)}")
    #     return response


class UserSubscriptionListView(APIView):
    """
    View for listing a user's subscriptions
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscriptions = UserSubscription.objects.filter(
            user=request.user).order_by('-start_date')

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
            remaining_days = (
                sub.end_date - now).days if sub.end_date > now else 0

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
        subscription = get_object_or_404(
            UserSubscription, id=id, user=request.user)

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
        remaining_days = (subscription.end_date -
                          now).days if subscription.end_date > now else 0

        # Get related order if available
        order_data = None
        if hasattr(subscription.subscription_plan, 'orders'):
            order = subscription.subscription_plan.orders.filter(
                user=request.user, status='paid').first()
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


class ActiveUserSubscriptionView(APIView):
    """
    View for retrieving the active subscription for the current user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        active_subscription = UserSubscription.objects.filter(
            user=user,
            is_active=True,
            end_date__gt=timezone.now()
        ).order_by('-end_date').first()

        if not active_subscription:
            return Response({"message": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        remaining_days = (active_subscription.end_date -
                          now).days if active_subscription.end_date > now else 0

        total_duration_days = active_subscription.subscription_plan.duration_days
        progress_percentage = 0
        if active_subscription.is_valid() and total_duration_days > 0:
            # Calculate percentage based on days passed relative to total duration
            # Ensure start_date is not in the future for this calculation
            if active_subscription.start_date <= now:
                days_passed = (now - active_subscription.start_date).days
                # Ensure days_passed is not negative and not more than total_duration_days
                days_passed = max(0, min(days_passed, total_duration_days))
                # Percentage of time *used*
                # progress_percentage = int((days_passed / total_duration_days) * 100)
                # Percentage of time *remaining*
                progress_percentage = int(
                    (remaining_days / total_duration_days) * 100) if remaining_days > 0 else 0
            else:  # Subscription hasn't started yet
                progress_percentage = 100  # Full time remaining

        data = {
            'plan_name': active_subscription.subscription_plan.name,
            'remaining_days': remaining_days,
            'progress_percentage': progress_percentage,
        }
        return Response(data, status=status.HTTP_200_OK)


class SubscriptionPurchaseView(APIView):
    """
    View for directly purchasing a subscription (bypassing cart)
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        subscription_plan = get_object_or_404(
            SubscriptionPlan, slug=slug, is_active=True)
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
                raise Exception(
                    f"Payment initiation failed: {zarinpal_response['errors']}")

            # Store the payment URL and authority in the transaction
            transaction.extra_data = {
                'authority': zarinpal_response.get('data', {}).get('authority'),
                'payment_url': zarinpal_response.get('data', {}).get('payment_url')
            }
            transaction.payment_gateway_reference = zarinpal_response.get(
                'data', {}).get('authority')
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
        response = requests.post(
            request_url, data=json.dumps(request_data), headers=headers)

        return response.json()
