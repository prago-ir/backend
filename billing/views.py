from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.urls import reverse
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from courses.models import Course
from subscriptions.models import SubscriptionPlan
from .models import Cart, CartItem, Order, OrderItem, Transaction, Coupon

import uuid
import json
import requests
from decimal import Decimal

# ==================== Cart Views ====================

class CartView(APIView):
    """
    View for retrieving and updating the user's shopping cart
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get the current user's cart contents"""
        cart, created = Cart.objects.get_or_create(user=request.user)

        # Calculate cart totals
        items = []
        for item in cart.items.all():
            content_object = item.content_object
            item_data = {
                'id': item.id,
                'type': item.content_type.model,
                'object_id': item.object_id,
                'quantity': item.quantity,
                'unit_price': float(item.get_unit_price()),
                'total_price': float(item.get_price()),
                'name': content_object.name if hasattr(content_object, 'name') else content_object.title,
            }

            # Add image URL if available
            if hasattr(content_object, 'thumbnail') and content_object.thumbnail:
                item_data['image'] = content_object.thumbnail.url

            items.append(item_data)

        # Coupon data if applied
        coupon_data = None
        if cart.coupon:
            coupon_data = {
                'code': cart.coupon.code,
                'discount_type': cart.coupon.discount_type,
                'discount_value': float(cart.coupon.discount_value),
                'discount_amount': float(cart.discount_amount)
            }

        data = {
            'items': items,
            'subtotal': float(cart.subtotal),
            'discount_amount': float(cart.discount_amount),
            'total': float(cart.total),
            'coupon': coupon_data,
            'item_count': cart.total_items
        }

        return Response(data)

class AddToCartView(APIView):
    """
    View for adding items to the cart
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_type = request.data.get('type')
        item_id = request.data.get('id')
        quantity = int(request.data.get('quantity', 1))

        if quantity <= 0:
            return Response(
                {"error": "Quantity must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Block subscription items from cart - they should use direct purchase
        if item_type == 'subscription':
            return Response(
                {"error": "Subscriptions cannot be added to the cart. Please use direct purchase option."},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart, created = Cart.objects.get_or_create(user=request.user)

        try:
            # Handle different item types - now only courses can be added to cart
            if item_type == 'course':
                course = get_object_or_404(Course, id=item_id)
                cart_item = cart.add_course(course, quantity)
            else:
                return Response(
                    {"error": "Invalid item type"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response({
                "message": "Item added to cart successfully",
                "cart_total": float(cart.total),
                "item_count": cart.total_items
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class RemoveFromCartView(APIView):
    """
    View for removing items from the cart
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        item_id = request.data.get('item_id')

        if not item_id:
            return Response(
                {"error": "Item ID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = get_object_or_404(Cart, user=request.user)

        try:
            success = cart.remove_item(item_id)
            if success:
                return Response({
                    "message": "Item removed from cart successfully",
                    "cart_total": float(cart.total),
                    "item_count": cart.total_items
                })
            else:
                return Response(
                    {"error": "Item not found in cart"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ApplyCouponView(APIView):
    """
    View for applying a coupon to the cart
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        coupon_code = request.data.get('code')

        if not coupon_code:
            return Response(
                {"error": "Coupon code is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart = get_object_or_404(Cart, user=request.user)

        try:
            coupon = get_object_or_404(Coupon, code=coupon_code, is_active=True)

            if not coupon.is_valid:
                return Response(
                    {"error": "This coupon is no longer valid"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            cart.coupon = coupon
            cart.save()

            return Response({
                "message": "Coupon applied successfully",
                "discount_amount": float(cart.discount_amount),
                "total": float(cart.total)
            })
        except Http404:
            return Response(
                {"error": "Invalid coupon code"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class RemoveCouponView(APIView):
    """
    View for removing a coupon from the cart
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)

        if not cart.coupon:
            return Response(
                {"error": "No coupon is applied to the cart"},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart.coupon = None
        cart.save()

        return Response({
            "message": "Coupon removed successfully",
            "total": float(cart.total)
        })

class CartCheckoutView(APIView):
    """
    View for checking out the cart and creating an order
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)

        if cart.total_items == 0:
            return Response(
                {"error": "Cannot checkout an empty cart"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                order = cart.checkout()

                # Create a new transaction for payment
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
                    description=f"Payment for Order #{order.order_number}",
                    email=request.user.email,
                    mobile=request.user.phone,
                    order_id=order.order_number,
                    transaction_id=transaction_id
                )

                if 'errors' in zarinpal_response:
                    # Handle payment initiation errors
                    raise Exception(f"Payment initiation failed: {zarinpal_response['errors']}")

                # Store the payment URL and authority in the transaction
                transaction.extra_data = {
                    'authority': zarinpal_response.get('data', {}).get('authority'),
                    'payment_url': zarinpal_response.get('data', {}).get('payment_url')
                }
                transaction.payment_gateway_reference = zarinpal_response.get('data', {}).get('authority')
                transaction.save()

                return Response({
                    "message": "Order created successfully",
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

# ==================== Payment Views ====================

class ZarinpalVerifyView(APIView):
    """
    View for verifying Zarinpal payment callback
    """
    def get(self, request):
        authority = request.GET.get('Authority')
        status = request.GET.get('Status')
        order_id = request.GET.get('order_id')
        transaction_id = request.GET.get('transaction_id')

        if not authority or not status:
            return Response(
                {"error": "Invalid payment callback"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find the transaction
        try:
            if transaction_id:
                transaction = Transaction.objects.get(transaction_id=transaction_id)
            else:
                transaction = Transaction.objects.get(payment_gateway_reference=authority)
            order = transaction.order

        except Transaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check payment status
        if status == 'OK':
            # Verify payment with Zarinpal
            verification_result = self.verify_zarinpal_payment(
                authority=authority,
                amount=int(transaction.amount)
            )

            if verification_result.get('data', {}).get('code') == 100:
                # Payment successful
                transaction.mark_as_successful()

                # Store the reference ID (ref_id) from Zarinpal
                ref_id = verification_result.get('data', {}).get('ref_id')
                if transaction.extra_data is None:
                    transaction.extra_data = {}
                transaction.extra_data['ref_id'] = ref_id
                transaction.save()

                # Redirect to success page with order details
                frontend_success_url = f"{settings.FRONTEND_URL}/payment/success?order_id={order.order_number}"
                return redirect(frontend_success_url)
            else:
                # Payment verification failed
                error_code = verification_result.get('errors', {}).get('code')
                error_message = verification_result.get('errors', {}).get('message', 'Payment verification failed')

                transaction.mark_as_failed(reason=f"Verification failed: {error_message} (Code: {error_code})")

                # Redirect to failure page
                frontend_failure_url = f"{settings.FRONTEND_URL}/payment/failure?order_id={order.order_number}&error={error_message}"
                return redirect(frontend_failure_url)
        else:
            # User canceled the payment
            transaction.mark_as_failed(reason="Payment canceled by user")

            # Redirect to canceled page
            frontend_canceled_url = f"{settings.FRONTEND_URL}/payment/canceled?order_id={order.order_number}"
            return redirect(frontend_canceled_url)

    def verify_zarinpal_payment(self, authority, amount):
        """
        Verify a Zarinpal payment with the authority and amount
        """
        zarinpal_merchant_id = settings.ZARINPAL_MERCHANT_ID

        # Zarinpal API endpoint for verification
        verify_url = 'https://api.zarinpal.com/pg/v4/payment/verify.json'

        # Prepare the verification payload
        verify_data = {
            'merchant_id': zarinpal_merchant_id,
            'authority': authority,
            'amount': amount
        }

        # Make the verification request
        headers = {'Content-Type': 'application/json'}
        response = requests.post(verify_url, data=json.dumps(verify_data), headers=headers)

        return response.json()

# ==================== Order History Views ====================

class OrderListView(generics.ListAPIView):
    """
    View for listing a user's orders
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(user=request.user).order_by('-created_at')

        order_list = []
        for order in orders:
            # Get main order items
            item_details = []
            if order.order_type == 'course' and order.course:
                item_details.append({
                    'type': 'course',
                    'id': order.course.id,
                    'name': order.course.title,
                    'image': order.course.thumbnail.url if hasattr(order.course, 'thumbnail') and order.course.thumbnail else None
                })
            elif order.order_type == 'subscription' and order.subscription_plan:
                item_details.append({
                    'type': 'subscription',
                    'id': order.subscription_plan.id,
                    'name': order.subscription_plan.name,
                    'duration': order.subscription_plan.duration_days
                })
            elif order.order_type == 'multi':
                # Get items for multi-item orders
                for item in order.items.all():
                    content_object = item.content_object
                    item_data = {
                        'type': item.content_type.model,
                        'id': content_object.id,
                        'name': content_object.title if hasattr(content_object, 'title') else content_object.name,
                        'quantity': item.quantity,
                        'price': float(item.total_price)
                    }

                    # Add image if available
                    if hasattr(content_object, 'thumbnail') and content_object.thumbnail:
                        item_data['image'] = content_object.thumbnail.url

                    item_details.append(item_data)

            # Get transaction info for this order
            transaction = order.transactions.last()
            transaction_info = None
            if transaction:
                transaction_info = {
                    'transaction_id': transaction.transaction_id,
                    'status': transaction.status,
                    'payment_method': transaction.payment_method,
                    'amount': float(transaction.amount),
                    'created_at': transaction.created_at.isoformat()
                }

            order_data = {
                'id': order.id,
                'order_number': order.order_number,
                'status': order.status,
                'order_type': order.order_type,
                'total_amount': float(order.total_amount),
                'discount_amount': float(order.discount_amount),
                'final_amount': float(order.final_amount),
                'created_at': order.created_at.isoformat(),
                'paid_at': order.paid_at.isoformat() if order.paid_at else None,
                'items': item_details,
                'transaction': transaction_info
            }

            order_list.append(order_data)

        return Response(order_list)

class OrderDetailView(generics.RetrieveAPIView):
    """
    View for retrieving details of a specific order
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)

        # Get detailed order items
        items = []
        if order.order_type == 'course' and order.course:
            items.append({
                'type': 'course',
                'id': order.course.id,
                'name': order.course.title,
                'price': float(order.course.price),
                'image': order.course.thumbnail.url if hasattr(order.course, 'thumbnail') and order.course.thumbnail else None
            })
        elif order.order_type == 'subscription' and order.subscription_plan:
            items.append({
                'type': 'subscription',
                'id': order.subscription_plan.id,
                'name': order.subscription_plan.name,
                'price': float(order.subscription_plan.price),
                'duration': order.subscription_plan.duration_days
            })
        elif order.order_type == 'multi':
            for item in order.items.all():
                content_object = item.content_object
                item_data = {
                    'type': item.content_type.model,
                    'id': content_object.id,
                    'name': content_object.title if hasattr(content_object, 'title') else content_object.name,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price)
                }

                if hasattr(content_object, 'thumbnail') and content_object.thumbnail:
                    item_data['image'] = content_object.thumbnail.url

                items.append(item_data)

        # Get all transactions for this order
        transaction_list = []
        for transaction in order.transactions.all():
            transaction_data = {
                'transaction_id': transaction.transaction_id,
                'status': transaction.status,
                'payment_method': transaction.payment_method,
                'payment_gateway_reference': transaction.payment_gateway_reference,
                'amount': float(transaction.amount),
                'created_at': transaction.created_at.isoformat(),
                'description': transaction.description,
            }

            if transaction.extra_data:
                transaction_data['ref_id'] = transaction.extra_data.get('ref_id')

            transaction_list.append(transaction_data)

        # Coupon information if used
        coupon_data = None
        if order.coupon:
            coupon_data = {
                'code': order.coupon.code,
                'discount_type': order.coupon.discount_type,
                'discount_value': float(order.coupon.discount_value),
                'discount_amount': float(order.discount_amount)
            }

        order_data = {
            'id': order.id,
            'order_number': order.order_number,
            'status': order.status,
            'order_type': order.order_type,
            'user': {
                'id': order.user.id,
                'username': order.user.username,
                'email': order.user.email,
                'phone': order.user.phone
            },
            'total_amount': float(order.total_amount),
            'discount_amount': float(order.discount_amount),
            'final_amount': float(order.final_amount),
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat(),
            'paid_at': order.paid_at.isoformat() if order.paid_at else None,
            'items': items,
            'transactions': transaction_list,
            'coupon': coupon_data
        }

        return Response(order_data)
