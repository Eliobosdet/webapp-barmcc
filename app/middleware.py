from django.shortcuts import redirect
from django.urls import reverse


class PasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # 1. Se è superuser, non disturbarlo mai
            if request.user.is_superuser:
                return self.get_response(request)

            # 2. Se è un utente normale, controlliamo il profilo Person
            person = getattr(request.user, "person_profile", None)

            # Se la persona esiste e deve cambiare password
            if person and person.must_change_password:
                allowed_urls = [
                    reverse("app:force_password_change"),
                    reverse("app:logout"),
                ]

                # Evita il redirect infinito se è già sulla pagina giusta o su file statici
                if request.path not in allowed_urls and not request.path.startswith(
                    "/static/"
                ):
                    return redirect("app:force_password_change")

        return self.get_response(request)
