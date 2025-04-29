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
from .models import Order, OrderItem, Transaction, Coupon

import uuid
import json
import requests
from decimal import Decimal

