from django.shortcuts import redirect, render


def index(request):
    return redirect("login")


def login_view(request):
    return render(request, "login/index.html")


def sales_view(request):
    return render(request, "sales/index.html")


def manager_view(request):
    return render(request, "manager/index.html")


def owner_view(request):
    return render(request, "owner/index.html")