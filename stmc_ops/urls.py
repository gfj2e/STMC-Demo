from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("sales/", views.sales_view, name="sales"),
    path("sales/shell/", views.sales_shell_view, name="sales_shell"),
    path("sales/turnkey/", views.sales_turnkey_view, name="sales_turnkey"),
    path("sales/contracts/seed-data/", views.sales_contract_seed_data_view, name="sales_contract_seed_data"),
    path("app/seed-data/", views.app_seed_data_view, name="app_seed_data"),
    path("manager/", views.manager_view, name="manager"),
    path("owner/", views.owner_view, name="owner"),
]
