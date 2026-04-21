from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("login/panel/", views.login_panel_view, name="login_panel"),
    path("sales/", views.sales_view, name="sales"),
    path("sales/shell/", views.sales_shell_view, name="sales_shell"),
    path("sales/turnkey/", views.sales_turnkey_view, name="sales_turnkey"),
    path("sales/overview/", views.sales_overview_view, name="sales_overview"),
    path("sales/overview/projects-panel/", views.sales_projects_panel_view, name="sales_projects_panel"),
    path("sales/overview/models-panel/", views.sales_models_panel_view, name="sales_models_panel"),
    path("sales/overview/rates-panel/", views.sales_rates_panel_view, name="sales_rates_panel"),
    path("sales/contracts/seed-data/", views.sales_contract_seed_data_view, name="sales_contract_seed_data"),
    path("app/seed-data/", views.app_seed_data_view, name="app_seed_data"),
    path("app/draw/complete/", views.mark_draw_complete_view, name="mark_draw_complete"),
    path("app/save-contract/", views.save_contract_view, name="save_contract"),
    path("manager/", views.manager_view, name="manager"),
    path("manager/builds-panel/", views.manager_builds_panel_view, name="manager_builds_panel"),
    path("manager/budgets-panel/", views.manager_budgets_panel_view, name="manager_budgets_panel"),
    path("manager/draws-panel/", views.manager_draws_panel_view, name="manager_draws_panel"),
    path("manager/panel/complete/", views.manager_panel_mark_complete_view, name="manager_panel_complete"),
    path("owner/", views.owner_view, name="owner"),
    path("owner/dashboard-panel/", views.owner_dashboard_panel_view, name="owner_dashboard_panel"),
    path("owner/all-projects-panel/", views.owner_all_projects_panel_view, name="owner_all_projects_panel"),
    path("owner/payments-panel/", views.owner_payments_panel_view, name="owner_payments_panel"),
    path("owner/panel/complete/", views.owner_panel_mark_complete_view, name="owner_panel_complete"),
]
