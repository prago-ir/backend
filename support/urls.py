from django.urls import path
from . import views


urlpatterns = [
    path('tickets/', views.TicketListView.as_view(), name='ticket-list'),
    path('tickets/new/', views.TicketCreateView.as_view(), name='ticket-create'),
    path('tickets/<str:ticket_number>/',
         views.TicketDetailView.as_view(), name='ticket-detail'),
]
