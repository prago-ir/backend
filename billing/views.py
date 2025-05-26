from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Order, Transaction, Coupon  # Add Coupon
from .serializers import UserOrderListSerializer  # Import the new serializer

from subscriptions.models import SubscriptionPlan

import uuid
import json
import requests
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def get_zarinpal_payment_url(authority):
    """Get the proper Zarinpal payment URL based on current settings"""
    return f"{settings.ZARINPAL_API_BASE.rstrip('/')}/pg/StartPay/{authority}"


class ZarinpalPaymentView(APIView):
    """
    Initiate a payment through Zarinpal for an order
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = request.data.get('order_id')
        frontend_callback_url = request.data.get('callback_url')

        if not order_id:
            return Response({"error": "Order ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not frontend_callback_url:
            return Response({"error": "Frontend callback URL is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Get the order
            order = get_object_or_404(Order, id=order_id, user=request.user)

            # Check if order is already paid
            if order.status == 'paid':
                return Response({
                    "error": "This order has already been paid"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create a transaction for payment
            transaction_id = f"TRX-{uuid.uuid4().hex[:12].upper()}"
            transaction = Transaction.objects.create(
                order=order,
                transaction_id=transaction_id,
                amount=order.final_amount,
                payment_method='zarinpal',
                status='pending'
            )

            # Store the frontend callback URL in the transaction's extra_data for later use
            transaction.extra_data = {
                'frontend_callback_url': frontend_callback_url
            }
            transaction.save()

            # Prepare description based on order type
            if order.order_type == 'course':
                description = f"Payment for Course: {order.course.title if order.course else 'Unknown Course'}"
            elif order.order_type == 'subscription':
                description = f"Payment for Subscription: {order.subscription_plan.name if order.subscription_plan else 'Unknown Plan'}"
            else:
                description = f"Payment for Order #{order.order_number}"

            # Initiate Zarinpal payment
            zarinpal_response = self.initiate_zarinpal_payment(
                amount=int(order.final_amount),
                description=description,
                email=request.user.email,
                mobile=request.user.phone,
                order_id=order.order_number,
                transaction_id=transaction_id
            )

            if 'errors' in zarinpal_response and zarinpal_response['errors']:
                logger.error(
                    f"Zarinpal payment initiation failed: {zarinpal_response['errors']}")
                return Response({
                    "error": "Payment gateway error",
                    "details": zarinpal_response['errors']
                }, status=status.HTTP_400_BAD_REQUEST)

            # Update transaction with payment details
            authority = zarinpal_response.get('data', {}).get('authority')
            if not authority:
                return Response({
                    "error": "No authority received from payment gateway"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Store payment details in transaction
            transaction.payment_gateway_reference = authority
            transaction.extra_data.update({
                'authority': authority,
            })
            transaction.save()

            # Generate payment URL
            payment_url = get_zarinpal_payment_url(authority)

            return Response({
                "message": "Payment initiated successfully",
                "order_number": order.order_number,
                "transaction_id": transaction.transaction_id,
                "payment_url": payment_url,
                "authority": authority
            })

        except Exception as e:
            logger.exception("Error initiating payment")
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def initiate_zarinpal_payment(self, amount, description, email=None, mobile=None, order_id=None, transaction_id=None):
        """
        Initiate a payment through Zarinpal
        """
        zarinpal_merchant_id = settings.ZARINPAL_MERCHANT_ID

        # Get the base URL for API calls (sandbox vs production)
        api_base = settings.ZARINPAL_API_BASE
        if not api_base.endswith('/'):
            api_base += '/'

        # Build callback URL that will be used when user returns from Zarinpal
        callback_url = f"{self.request.build_absolute_uri('/')[:-1]}{reverse('billing:zarinpal_verify')}"

        # Add order_id and transaction_id as query parameters to callback URL
        if order_id and transaction_id:
            callback_url += f"?order_id={order_id}&transaction_id={transaction_id}"

        # Zarinpal API endpoint
        request_url = f"{api_base}pg/v4/payment/request.json"

        # Prepare the request payload
        request_data = {
            'merchant_id': zarinpal_merchant_id,
            'amount': amount,
            'description': description,
            'callback_url': callback_url
        }

        # Add metadata if available
        metadata = {}
        if email:
            metadata['email'] = email
        if mobile:
            metadata['mobile'] = mobile

        if metadata:
            request_data['metadata'] = metadata

        # Make the request to Zarinpal
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                request_url, data=json.dumps(request_data), headers=headers)
            return response.json()
        except Exception as e:
            logger.exception("Error communicating with Zarinpal")
            return {'errors': [str(e)]}


class ZarinpalVerifyView(APIView):
    """
    Verify a payment through Zarinpal and process the order
    """
    permission_classes = []  # No authentication required as ZarinPal redirects here

    def get(self, request, *args, **kwargs):
        # Extract parameters from the request
        authority = request.GET.get('Authority')
        status = request.GET.get('Status')
        order_id = request.GET.get('order_id')
        transaction_id = request.GET.get('transaction_id')

        # Log the request for debugging
        logger.info(
            f"ZarinPal callback received: Authority={authority}, Status={status}, order_id={order_id}, transaction_id={transaction_id}")

        if not authority or not status:
            logger.error("Missing required parameters in ZarinPal callback")
            return self.redirect_to_frontend_with_error("Invalid payment verification request")

        # Find the transaction
        if transaction_id:
            try:
                transaction = Transaction.objects.get(
                    transaction_id=transaction_id)
            except Transaction.DoesNotExist:
                logger.error(f"Transaction not found: {transaction_id}")
                return self.redirect_to_frontend_with_error("Transaction not found")
        elif order_id:
            try:
                # Try to find by order number
                order = Order.objects.get(order_number=order_id)
                transaction = order.transactions.filter(
                    payment_method='zarinpal').order_by('-created_at').first()
                if not transaction:
                    raise Transaction.DoesNotExist
            except (Order.DoesNotExist, Transaction.DoesNotExist):
                logger.error(
                    f"Order or transaction not found for order: {order_id}")
                return self.redirect_to_frontend_with_error("Order not found")
        else:
            # Try to find by ZarinPal authority
            try:
                transaction = Transaction.objects.get(
                    payment_gateway_reference=authority)
            except Transaction.DoesNotExist:
                logger.error(
                    f"Transaction not found for authority: {authority}")
                return self.redirect_to_frontend_with_error("Transaction not found")

        # Get the frontend callback URL from the transaction
        frontend_callback_url = transaction.extra_data.get(
            'frontend_callback_url') if transaction.extra_data else None
        if not frontend_callback_url:
            frontend_callback_url = settings.FRONTEND_URL

        # Check if the payment was canceled by the user
        if status != 'OK':
            transaction.mark_as_failed("Payment canceled by user")
            return redirect(f"{frontend_callback_url}?status=canceled&transaction_id={transaction.transaction_id}")

        # Verify the payment with ZarinPal
        verify_response = self.verify_zarinpal_payment(
            authority, int(transaction.amount))

        if 'errors' in verify_response and verify_response['errors']:
            error_message = str(verify_response['errors'])
            logger.error(f"Payment verification failed: {error_message}")
            transaction.mark_as_failed(error_message)
            return redirect(f"{frontend_callback_url}?status=failed&transaction_id={transaction.transaction_id}&message={error_message}")

        # Check verification response
        data = verify_response.get('data', {})
        code = data.get('code')

        if code == 100 or code == 101:  # 100: Success, 101: Already verified
            # Get the reference ID (ref_id) from the verification response
            ref_id = data.get('ref_id')

            if ref_id:
                # Update transaction with reference ID and mark as successful
                transaction.extra_data = transaction.extra_data or {}
                transaction.extra_data.update({
                    'ref_id': ref_id,
                    'card_pan': data.get('card_pan', ''),
                    'card_hash': data.get('card_hash', '')
                })
                transaction.mark_as_successful()

                # Mark the order as paid (which will handle subscription creation)
                transaction.order.mark_as_paid()

                # Redirect to frontend success page with transaction details
                return redirect(f"{frontend_callback_url}?status=success&transaction_id={transaction.transaction_id}&ref_id={ref_id}")
            else:
                logger.error(
                    "Payment verification succeeded but no reference ID was received")
                transaction.mark_as_failed("No reference ID was received")
                return redirect(f"{frontend_callback_url}?status=failed&transaction_id={transaction.transaction_id}&message=No reference ID")
        else:
            # Payment verification failed
            error_message = data.get('message', 'Payment verification failed')
            logger.error(
                f"Payment verification failed with code {code}: {error_message}")
            transaction.mark_as_failed(error_message)
            return redirect(f"{frontend_callback_url}?status=failed&transaction_id={transaction.transaction_id}&message={error_message}")

    def verify_zarinpal_payment(self, authority, amount):
        """Verify a payment with ZarinPal"""
        zarinpal_merchant_id = settings.ZARINPAL_MERCHANT_ID

        # Get the base URL for API calls
        api_base = settings.ZARINPAL_API_BASE
        if not api_base.endswith('/'):
            api_base += '/'

        # Zarinpal API endpoint for verification
        request_url = f"{api_base}pg/v4/payment/verify.json"

        # Prepare the request payload
        request_data = {
            'merchant_id': zarinpal_merchant_id,
            'amount': amount,
            'authority': authority
        }

        # Make the request to Zarinpal
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        try:
            response = requests.post(
                request_url, data=json.dumps(request_data), headers=headers)
            return response.json()
        except Exception as e:
            logger.exception("Error verifying payment with Zarinpal")
            return {'errors': [str(e)]}

    def redirect_to_frontend_with_error(self, error_message):
        """Helper to redirect to frontend with error message"""
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost')
        return redirect(f"{frontend_url}?status=error&message={error_message}")


class SubscriptionPurchaseView(APIView):
    """
    View for directly purchasing a subscription plan, potentially with a coupon.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        plan_id = request.data.get('plan_id')
        frontend_callback_url = request.data.get('callback_url')
        coupon_code = request.data.get('coupon_code')  # New: Get coupon code

        if not plan_id:
            return Response({"error": "Subscription plan ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        if not frontend_callback_url:
            return Response({"error": "Frontend callback URL is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            subscription_plan = get_object_or_404(
                SubscriptionPlan, id=plan_id, is_active=True)
            user = request.user
            logger.info(
                f"Processing subscription purchase for user {user.id}, plan: {plan_id}, coupon: {coupon_code}")

            # Check for existing active subscription (your existing logic)
            from subscriptions.models import UserSubscription
            existing_subscription = UserSubscription.objects.filter(
                user=user,
                subscription_plan=subscription_plan,
                is_active=True,
                end_date__gt=timezone.now()
            ).first()
            if existing_subscription:
                return Response({"error": "You already have an active subscription to this plan"}, status=status.HTTP_400_BAD_REQUEST)

            order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

            current_plan_price = subscription_plan.get_current_price()
            discount_amount = Decimal(0)
            applied_coupon = None

            if coupon_code:
                try:
                    coupon = Coupon.objects.get(
                        code__iexact=coupon_code, is_active=True)
                    if coupon.is_valid:  # Use the @property
                        # Calculate discount based on the current plan price
                        original_amount_for_discount = current_plan_price
                        actual_discount = original_amount_for_discount - \
                            coupon.apply_discount(original_amount_for_discount)
                        discount_amount = actual_discount
                        applied_coupon = coupon
                        logger.info(
                            f"Coupon '{coupon_code}' applied. Discount: {discount_amount}")
                    else:
                        logger.warning(
                            f"Coupon '{coupon_code}' is invalid or expired.")
                        # Optionally, return an error if coupon is invalid, or just ignore it
                        # return Response({"error": "کد تخفیف نامعتبر یا منقضی شده است."}, status=status.HTTP_400_BAD_REQUEST)
                except Coupon.DoesNotExist:
                    logger.warning(f"Coupon '{coupon_code}' not found.")
                    # Optionally, return an error if coupon not found, or just ignore it
                    # return Response({"error": "کد تخفیف یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)

            final_amount_after_discount = current_plan_price - discount_amount

            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    order_number=order_number,
                    order_type='subscription',
                    subscription_plan=subscription_plan,
                    # Original price for this transaction (could be special offer)
                    total_amount=current_plan_price,
                    discount_amount=discount_amount,
                    final_amount=final_amount_after_discount,
                    coupon=applied_coupon,  # Link the coupon to the order
                    status='pending'
                )

                if applied_coupon:
                    applied_coupon.record_usage()  # Record coupon usage

                transaction_id = f"TRX-{uuid.uuid4().hex[:12].upper()}"
                Transaction.objects.create(
                    order=order,
                    transaction_id=transaction_id,
                    amount=order.final_amount,
                    payment_method='zarinpal',
                    status='pending',
                    extra_data={'frontend_callback_url': frontend_callback_url}
                )

                description = f"Purchase of subscription plan: {subscription_plan.name}"
                if applied_coupon:
                    description += f" (Coupon: {applied_coupon.code})"

                zarinpal_view = ZarinpalPaymentView()
                # Pass the original request for context if needed by ZarinpalPaymentView
                zarinpal_view.request = request

                zarinpal_response = zarinpal_view.initiate_zarinpal_payment(
                    # Ensure this is integer for Zarinpal
                    amount=int(order.final_amount),
                    description=description,
                    email=user.email,
                    mobile=user.phone,  # Make sure user.phone exists and is valid
                    order_id=order.order_number,
                    transaction_id=transaction_id
                )

                if 'errors' in zarinpal_response and zarinpal_response['errors']:
                    # Log the detailed error from Zarinpal
                    logger.error(
                        f"Zarinpal payment initiation failed for order {order.order_number}. Errors: {zarinpal_response['errors']}")
                    # Provide a more generic error to the user
                    raise Exception(
                        "Payment initiation failed with the payment gateway.")

                authority = zarinpal_response.get('data', {}).get('authority')
                if not authority:
                    logger.error(
                        f"No authority received from Zarinpal for order {order.order_number}. Response: {zarinpal_response}")
                    raise Exception(
                        "Failed to get payment authority from Zarinpal.")

                payment_url = get_zarinpal_payment_url(authority)
                return Response({'payment_url': payment_url, 'order_id': order.order_number})

        except SubscriptionPlan.DoesNotExist:
            logger.error(f"Subscription plan with ID {plan_id} not found.")
            return Response({"error": "Subscription plan not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(
                f"Error during subscription purchase for plan {plan_id}: {str(e)}")
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserOrderListView(APIView):
    """
    View for listing orders for the current authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        orders = Order.objects.filter(user=user).order_by('-created_at')
        serializer = UserOrderListSerializer(
            orders, many=True, context={'request': request})
        return Response(serializer.data)


class ValidateCouponView(APIView):
    """
    Validates a coupon code and returns its discount details.
    """
    permission_classes = [AllowAny]  # Optional

    def post(self, request, *args, **kwargs):
        coupon_code = request.data.get('coupon_code')

        if not coupon_code:
            return Response({"valid": False, "error": "کد تخفیف ارائه نشده است."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Using __iexact for case-insensitive matching
            coupon = Coupon.objects.get(code__iexact=coupon_code.strip())

            if not coupon.is_valid:  # This uses the @property in your Coupon model
                logger.warn(
                    f"Validation attempt for invalid/expired coupon: {coupon_code}")
                return Response({"valid": False, "error": "کد تخفیف نامعتبر یا منقضی شده است."}, status=status.HTTP_400_BAD_REQUEST)

            logger.info(f"Coupon '{coupon_code}' validated successfully.")
            return Response({
                "valid": True,
                "message": "کد تخفیف معتبر است.",
                "coupon": {
                    "code": coupon.code,
                    "discount_type": coupon.discount_type,
                    # Ensure Decimal is serialized as string
                    "discount_value": str(coupon.discount_value),
                    "description": coupon.description or "",
                }
            }, status=status.HTTP_200_OK)

        except Coupon.DoesNotExist:
            logger.warn(
                f"Validation attempt for non-existent coupon: {coupon_code}")
            return Response({"valid": False, "error": "کد تخفیف یافت نشد."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error validating coupon {coupon_code}: {str(e)}")
            return Response({"valid": False, "error": "خطا در اعتبارسنجی کد تخفیف."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
