"""
URL configuration for hospital_management_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.bill_list, name='bill_list'),
    path('create/<int:appointment_id>/', views.bill_create, name='bill_create'),
    path('<int:pk>/', views.bill_detail, name='bill_detail'),
    path('<int:pk>/sent/', views.bill_mark_sent, name='bill_mark_sent'),
    path('<int:pk>/paid/', views.bill_mark_paid, name='bill_mark_paid'),
    path('<int:pk>/add-item/', views.bill_add_item, name='bill_add_item'),
    path('item/<int:item_id>/delete/', views.bill_delete_item, name='bill_delete_item'),
    path('<int:pk>/print/', views.bill_print, name='bill_print'),
    # path('<int:pk>/payment/', views.bill_record_payment, name='bill_record_payment'),
    path('<int:pk>/pay-now/', views.bill_pay_now, name='bill_pay_now'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),
]

