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
        # Pass context to serializer
        serializer = TicketSerializer(
            queryset, many=True, context={'request': request})
        return Response(serializer.data)


class TicketDetailView(APIView):
    """View for retrieving, updating and adding messages to a ticket"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, ticket_number):
        """Get detailed information about a specific ticket"""
        ticket = get_object_or_404(
            Ticket, ticket_number=ticket_number, user=request.user)
        # Pass context to serializer
        serializer = TicketDetailSerializer(
            ticket, context={'request': request})
        return Response(serializer.data)

    def post(self, request, ticket_number):
        """Add a new message to an existing ticket"""
        ticket = get_object_or_404(
            Ticket, ticket_number=ticket_number, user=request.user)

        if ticket.status in ['closed', 'resolved']:
            return Response(
                {"detail": "Cannot add messages to a closed or resolved ticket."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prepare data for the message serializer
        # Note: 'sender' here should be the user instance, not just ID,
        # if TicketMessageSerializer expects an instance for its create method
        # or if you rely on the serializer to handle the User instance.
        # However, since we marked 'sender' as write_only: True and it's a ForeignKey,
        # passing the ID is typical. The serializer's 'save' method will handle it.
        # For clarity, we can pass the instance directly if the serializer is set up for it.
        # Let's assume the serializer's 'sender' field (FK) will correctly handle request.user.id

        message_data_for_serializer = {
            'ticket': ticket.id,
            'sender': request.user.id,  # Pass the user ID for creation
            'message': request.data.get('message', '')
        }

        # Pass context to serializer
        message_serializer = TicketMessageSerializer(
            data=message_data_for_serializer, context={'request': request})
        if message_serializer.is_valid():
            # When saving, the serializer's 'sender' field (ForeignKey) will use the provided ID.
            # If you needed to pass the actual user instance to the serializer's create method,
            # you could do: message_serializer.save(sender=request.user)
            # But with 'sender': {'write_only': True} and it being a FK, validated_data['sender'] will be the ID.
            message = message_serializer.save()  # sender ID is already in validated_data

            files = request.FILES.getlist('attachments')
            for file_obj in files:  # Changed 'file' to 'file_obj'
                TicketMessageAttachment.objects.create(
                    message=message,
                    file=file_obj,
                    content_type=file_obj.content_type
                )

            ticket.updated_at = timezone.now()
            # If the ticket status should change to 'customer_reply' or similar on new message
            # ticket.status = 'customer_reply' # Example
            ticket.save()

            # Pass context to serializer for the response
            serializer = TicketDetailSerializer(
                ticket, context={'request': request})
            return Response(serializer.data)

        return Response(message_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, ticket_number):
        """Update ticket status"""
        ticket = get_object_or_404(
            Ticket, ticket_number=ticket_number, user=request.user)

        if 'status' in request.data:
            ticket.status = request.data['status']
            ticket.save()

        # Pass context to serializer
        serializer = TicketDetailSerializer(
            ticket, context={'request': request})
        return Response(serializer.data)


class TicketCreateView(APIView):
    """View for creating a new support ticket"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        """Create a new support ticket with optional initial message and attachments"""
        ticket_number = f"TCK-{uuid.uuid4().hex[:8].upper()}"
        ticket_data_for_serializer = {
            'ticket_number': ticket_number,
            'subject': request.data.get('subject', ''),
            'department': request.data.get('department', 'support'),
        }

        # Pass context to serializer
        ticket_serializer = TicketSerializer(
            data=ticket_data_for_serializer, context={'request': request})
        if ticket_serializer.is_valid():
            ticket = ticket_serializer.save(user=request.user)

            initial_message_content = request.data.get('message', '')
            if initial_message_content:
                # For creating the initial message, we can directly create the object
                # or use the serializer. Using the serializer ensures consistency.
                message_data = {
                    'ticket': ticket.id,
                    'sender': request.user.id,  # User ID
                    'message': initial_message_content
                }
                # Pass context to message serializer
                initial_message_serializer = TicketMessageSerializer(
                    data=message_data, context={'request': request})
                if initial_message_serializer.is_valid():
                    initial_message_instance = initial_message_serializer.save()

                    files = request.FILES.getlist('attachments')
                    for file_obj in files:  # Changed 'file' to 'file_obj'
                        TicketMessageAttachment.objects.create(
                            message=initial_message_instance,
                            file=file_obj,
                            content_type=file_obj.content_type
                        )
                else:
                    # If initial message fails validation, we might want to roll back ticket creation
                    # or return errors. For now, let's log and proceed with ticket creation response.
                    print(
                        f"Error creating initial message: {initial_message_serializer.errors}")

            # Pass context to serializer for the response
            detail_serializer = TicketDetailSerializer(
                ticket, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)

        return Response(ticket_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserActiveTicketsCountView(APIView):
    """
    View for retrieving the count of active tickets for the current user.
    Active tickets are those with status 'open', 'in_progress', or 'answered'.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        active_statuses = ['open', 'in_progress', 'answered']

        active_tickets_count = Ticket.objects.filter(
            user=user,
            status__in=active_statuses
        ).count()

        return Response({"active_tickets_count": active_tickets_count}, status=status.HTTP_200_OK)
