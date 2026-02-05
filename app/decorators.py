from functools import wraps
from django.core.exceptions import PermissionDenied


def partner_required(view_func):
    """
    Decoratore personalizzato per limitare l'accesso alle viste
    solo agli utenti che hanno un profilo Person associato e sono 'partner'.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verifica se l'utente è loggato, ha un profilo e il flag is_partner
        if (
            request.user.is_authenticated
            and hasattr(request.user, "person_profile")
            and request.user.person_profile.is_partner
        ):
            return view_func(request, *args, **kwargs)

        # Se non soddisfa i requisiti, restituisce Errore 403
        raise PermissionDenied

    return _wrapped_view
