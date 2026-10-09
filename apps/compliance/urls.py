from django.urls import path
from . import views, exports

app_name = 'compliance'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('export/pdf/', exports.export_pdf, name='export_pdf'),
    path('export/excel/', exports.export_excel, name='export_excel'),
]