
from typing import Any
from django.shortcuts import redirect
from django.urls import reverse


class RedirectAuthenticatedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        if request.path.startswith("/accounts/"):
            return redirect(reverse("index"))

        return self.get_response(request)