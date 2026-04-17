from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("sales/", views.sales_view, name="sales"),
    path("sales/turnkey/", views.turnkey_view, name="turnkey"),
    path("sales/shell/", views.shell_view, name="shell_wizard"),
    path("manager/", views.manager_view, name="manager"),
    path("owner/", views.owner_view, name="owner"),
]
