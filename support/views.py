from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.utils import timezone
import uuid

from .models import Ticket, TicketMessage, TicketMessageAttachment
from .serializers import TicketSerializer, TicketMessageSerializer, TicketDetailSerializer


class TicketListView(APIView):
    """View for listing user's tickets and creating new ones"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return list of all tickets for the authenticated user"""
        queryset = Ticket.objects.filter(
            user=request.user).order_by('-created_at')
        serializer = TicketSerializer(queryset, many=True)
        return Response(serializer.data)


class TicketDetailView(APIView):
    """View for retrieving, updating and adding messages to a ticket"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, ticket_number):
        """Get detailed information about a specific ticket"""
        ticket = get_object_or_404(
            Ticket, ticket_number=ticket_number, user=request.user)
        serializer = TicketDetailSerializer(ticket)
        return Response(serializer.data)

    def post(self, request, ticket_number):
        """Add a new message to an existing ticket"""
        ticket = get_object_or_404(
            Ticket, ticket_number=ticket_number, user=request.user)

        # Don't allow messages on closed tickets
        if ticket.status in ['closed', 'resolved']:
            return Response(
                {"detail": "Cannot add messages to a closed or resolved ticket."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create message
        message_data = {
            'ticket': ticket.id,
            'sender': request.user.id,
            'message': request.data.get('message', '')
        }

        message_serializer = TicketMessageSerializer(data=message_data)
        if message_serializer.is_valid():
            message = message_serializer.save()

            # Process attachments if any
            files = request.FILES.getlist('attachments')
            for file in files:
                TicketMessageAttachment.objects.create(
                    message=message,
                    file=file,
                    content_type=file.content_type
                )

            # Update ticket
            ticket.updated_at = timezone.now()
            ticket.save()

            # Return updated ticket details
            serializer = TicketDetailSerializer(ticket)
            return Response(serializer.data)

        return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, ticket_number):
        """Update ticket status"""
        ticket = get_object_or_404(
            Ticket, ticket_number=ticket_number, user=request.user)

        # Only allow updating status
        if 'status' in request.data:
            ticket.status = request.data['status']
            ticket.save()

        serializer = TicketDetailSerializer(ticket)
        return Response(serializer.data)


class TicketCreateView(APIView):
    """View for creating a new support ticket"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Create a new support ticket with optional initial message and attachments"""
        # Generate unique ticket number
        ticket_number = f"TCK-{uuid.uuid4().hex[:8].upper()}"

        # Prepare data for the serializer from the request and generated values.
        # Do not include 'user' here; it will be passed to save().
        ticket_data_for_serializer = {
            'ticket_number': ticket_number,
            'subject': request.data.get('subject', ''),
            'department': request.data.get('department', 'support'),
            # 'status' will use the model's default if not specified by the serializer or model
        }

        ticket_serializer = TicketSerializer(data=ticket_data_for_serializer)
        if ticket_serializer.is_valid():
            # Pass the user instance directly to the save method.
            # This ensures the 'user' field of the Ticket model is populated.
            ticket = ticket_serializer.save(user=request.user)

            # Create initial message if provided
            initial_message = request.data.get('message', '')
            if initial_message:
                message = TicketMessage.objects.create(
                    ticket=ticket,
                    sender=request.user,
                    message=initial_message
                )

                # Process attachments if any
                files = request.FILES.getlist('attachments')
                for file_obj in files:  # Renamed 'file' to 'file_obj' for clarity
                    TicketMessageAttachment.objects.create(
                        message=message,
                        file=file_obj,
                        content_type=file_obj.content_type
                    )

            # Return created ticket with details
            detail_serializer = TicketDetailSerializer(ticket)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

        return Response(ticket_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
