from django.urls import path
from . import views

app_name = 'organization'

urlpatterns = [
    path('companies/', views.CompanyListView.as_view(), name='company_list'),
    path('companies/<int:pk>/', views.CompanyDetailView.as_view(), name='company_detail'),
    path('sites/', views.SiteListView.as_view(), name='site_list'),
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),

    # Workforce Snapshot URLs
    path('workforce/', views.WorkforceSnapshotListView.as_view(), name='workforce_snapshot_list'),
    path('workforce/new/', views.WorkforceSnapshotCreateView.as_view(), name='workforce_snapshot_create'),
    path('workforce/<int:pk>/edit/', views.WorkforceSnapshotUpdateView.as_view(), name='workforce_snapshot_update'),
    path('workforce/<int:pk>/delete/', views.WorkforceSnapshotDeleteView.as_view(), name='workforce_snapshot_delete'),
]