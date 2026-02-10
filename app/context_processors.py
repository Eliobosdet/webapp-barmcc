# context_processors.py
from .models import GlobalSettings, Person
from django.conf import settings


def party_mode_status(request):
    return {"PARTY_MODE_ACTIVE": GlobalSettings.is_party_active()}

def debug_status(request):
    return {"DEBUG_MODE": settings.DEBUG}


def creator_info(request):
    # Cerchiamo la persona con il tuo nickname o email specifica
    corra = Person.objects.filter(nickname="Corra").first()
    return {"creator_profile_id": corra.id if corra else None}
