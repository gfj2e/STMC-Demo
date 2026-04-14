from django.shortcuts import redirect, render


def index(request):
    return redirect("login")


def login_view(request):
    return render(request, "login.html")


def sales_view(request):
    return render(request, "sales.html")


def manager_view(request):
    return render(request, "manager.html")


def owner_view(request):
    return render(request, "owner.html")