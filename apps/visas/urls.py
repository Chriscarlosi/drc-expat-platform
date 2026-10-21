from django.urls import path
from . import views

app_name = 'visas'

urlpatterns = [
    path('prolongation/new/', views.VisaProlongationCreateView.as_view(), name='prolongation_create'),
    path('prolongation/success/', views.ProlongationSuccessView.as_view(), name='prolongation_success'),
    path('expiring/', views.ExpiringVisaListView.as_view(), name='expiring_visas'),
    path('api/get-parent-visas/', views.GetParentVisasAPIView.as_view(), name='get_parent_visas_api'),
]