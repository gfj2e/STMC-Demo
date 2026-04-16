from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("sales/", views.sales_view, name="sales"),
    path("manager/", views.manager_view, name="manager"),
    path("owner/", views.owner_view, name="owner"),
    path("api/pdf/ext-labor/", views.generate_ext_labor_pdf, name="ext_labor_pdf"),
]
