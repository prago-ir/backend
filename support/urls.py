from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    path('tickets/', views.TicketListView.as_view(), name='ticket_list'),
    path('tickets/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('tickets/<str:ticket_number>/',
         views.TicketDetailView.as_view(), name='ticket_detail'),
    path('statistics/my-active-count/', views.UserActiveTicketsCountView.as_view(),
         name='user_active_tickets_count'),
]
