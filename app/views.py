from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, UpdateView
from django.utils import timezone
import os, json
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.conf import settings as django_settings # Per accedere a DEBUG



# Import locali
from .models import Order, Person, Product, OrderItem, Category, GlobalSettings
from .forms import OrderFilterForm, PersonUpdateForm
from .decorators import partner_required


def category_list(request):
    # Recuperiamo solo le categorie che contengono prodotti attivi
    categories = Category.objects.filter(product__is_active=True).distinct()
    return render(request, "app/category_list.html", {"categories": categories})


def products_menu(request):
    category_id = request.GET.get("category")
    if category_id:
        products = Product.objects.filter(category_id=category_id, is_active=True)
        current_category = Category.objects.get(id=category_id)
    else:
        products = Product.objects.filter(is_active=True)
        current_category = None

    return render(
        request,
        "app/products_menu.html",
        {"products": products, "current_category": current_category},
    )


# class PersonListView(ListView):
#     """
#     Mostra la lista delle persone (solo per staff/partner)
#     """

#     model = Person
#     template_name = "app/person_list.html"
#     context_object_name = "people"
#     paginate_by = 20  # opzionale

#     def dispatch(self, request, *args, **kwargs):
#         # Solo utenti loggati e partner possono accedere
#         if not request.user.is_authenticated or not (
#             hasattr(request.user, "person_profile")
#             and request.user.person_profile.is_partner
#         ):
#             return redirect("app:home")
#         return super().dispatch(request, *args, **kwargs)

class PersonListView(ListView):
    model = Person               # <-- AGGIUNGI QUESTA RIGA FONDAMENTALE
    template_name = 'app/person_list.html'
    context_object_name = 'people'

    def get_queryset(self):
        # Recuperiamo la lista di base
        queryset = super().get_queryset()
        
        # Leggiamo il termine di ricerca dall'URL (?q=...)
        query = self.request.GET.get('q')
        
        # Se c'è una query, applichiamo il filtro su nome e cognome
        if query:
            queryset = queryset.filter(
                Q(first_name__icontains=query) | Q(last_name__icontains=query)
            )
            
        return queryset

class PersonUpdateView(UpdateView):
    model = Person
    form_class = PersonUpdateForm
    # Specifica il template (anche se lo useremo nel modale, Django ne ha bisogno)
    template_name = "app/person_form.html"

    def get_success_url(self):
        # Torna alla pagina del profilo (sostituisci con il nome del tuo url)
        return reverse_lazy("app:profile", kwargs={"person_id": self.object.id})


def home(request):
    """
    Home page intelligente:
    - Se loggato E partner → mostra dashboard partner
    """
    if not request.user.is_authenticated:
        return redirect("app:login")

    has_person = hasattr(request.user, "person_profile")
    is_partner = has_person and request.user.person_profile.is_partner

    results = Category.get_all_top_consumers()

    total_orders = Order.objects.count()
    unpaid_orders = Order.objects.filter(payment_status="UNPAID").count()

    return render(
        request,
        "app/home.html",
        {
            "total_orders": total_orders,
            "unpaid_orders": unpaid_orders,
            "results": results,
            "is_partner": is_partner,
        },
    )


@partner_required
@login_required
def order_list(request):
    # AGGIUNTO select_related: recupera Person e User con una JOIN SQL
    orders = (
        Order.objects.select_related("person", "created_by")
        .all()
        .order_by("-created_at")
    )

    form = OrderFilterForm(request.GET)


    if form.is_valid():
        if form.cleaned_data["person"]:
            orders = orders.filter(person=form.cleaned_data["person"])

        if form.cleaned_data["status"]:
            orders = orders.filter(payment_status=form.cleaned_data["status"])

        if form.cleaned_data["date"]:
            orders = orders.filter(created_at__date=form.cleaned_data["date"])

    # PAGINAZIONE: Fondamentale per la velocità
    paginator = Paginator(orders, 25)  # 25 ordini per pagina
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "app/order_list.html",
        {
            "orders": page_obj,  # Passiamo l'oggetto paginato
            "filter_form": form,
            "people": Person.objects.all(),
        },
    )


@partner_required
@login_required
def order_create(request):
    people = Person.objects.all()
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.all()

    if request.method == "POST":
        person_id = request.POST.get("person")
        # Recuperiamo le liste dai campi ripetuti nell'HTML
        product_ids = request.POST.getlist("product")
        quantities = request.POST.getlist("quantity")
        offered_to_ids = request.POST.getlist("offered_to")
        notes = request.POST.get("notes", "")

        print(
            "Dati ricevuti: ", person_id, product_ids, quantities, offered_to_ids, notes
        )

        valid_products = [pid for pid in product_ids if pid and pid.strip() != ""]

        print(f"Prodotti validi filtrati: {valid_products}")  # Debug

        if not person_id:
            messages.error(request, "Devi selezionare una persona per l'ordine!")
            return render(
                request,
                "app/order_create.html",
                {"people": people, "products": products},
            )
        
        # Se dopo il filtro la lista è veramente vuota
        if not valid_products:
            messages.error(request, "Non hai selezionato nessun prodotto!")
            return render(
                request,
                "app/order_create.html",
                {
                    "people": Person.objects.all(),
                    "products": Product.objects.filter(is_active=True),
                },
            )


        try:
            with transaction.atomic():
                payer = Person.objects.get(pk=person_id)

                # Creiamo l'ordine (Metodo di default CASH come definito nei tuoi CHOICES)
                order = Order.objects.create(
                    person=payer,
                    created_by=request.user,
                    payment_status="UNPAID",
                    payment_method="NESSUNO",
                    notes=notes,
                )

                # Iteriamo sulle liste parallele
                for pid, qty, oto_id in zip(product_ids, quantities, offered_to_ids):
                    if not pid or not qty:
                        continue  # Salta righe vuote (come il template nascosto)

                    product = Product.objects.get(pk=pid)

                    # Gestione destinatario dell'offerta
                    destinatario = None
                    if oto_id:
                        destinatario = Person.objects.filter(pk=oto_id).first()

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=int(qty),
                        # Usiamo la logica del modello per il prezzo corretto (staff vs guest)
                        price_at_order=product.get_price_for_person(payer),
                        offered_to=destinatario,
                    )

            return redirect("app:order_detail", order_id=order.id)

        except Exception as e:
            return render(
                request,
                "app/order_create.html",
                {
                    "people": people,
                    "products": products,
                    "categories": categories,
                    "error": f"Errore: {e}",
                },
            )

    return render(
        request,
        "app/order_create.html",
        {"people": people, "products": products, "categories": categories},
    )


@login_required
def order_detail(request, order_id):
    """
    Dettaglio ordine
    """
    order = (
        Order.objects.select_related("person", "created_by")
        .prefetch_related("items__product")
        .get(pk=order_id)
    )

    return render(
        request,
        "app/order_detail.html",
        {
            "order": order,
        },
    )


@partner_required
@login_required
def order_delete(request, order_id):
    """
    Elimina un ordine
    """
    order = Order.objects.get(pk=order_id)
    order.delete()
    return redirect("app:order_list")


@partner_required
@login_required
@require_POST
def order_mark_paid(request, order_id=None):
    """
    Gestisce sia il pagamento singolo (Toggle) che quello multiplo (Bulk Set).
    """

    # 1. LOGICA MULTIPLA (BULK)
    # Controlliamo se nel POST c'è una lista di ID (dai checkbox)
    order_ids = request.POST.getlist('order_ids')
    metodo = request.POST.get("metodo_pagamento", "Contanti") # Default Contanti se manca
    next_url = request.POST.get('next') or request.GET.get('next')

    if order_ids:
        # Aggiornamento massivo: Impostiamo tutto a PAID
        # Usiamo .update() che è molto efficiente (una sola query SQL)
        updated_count = Order.objects.filter(id__in=order_ids, payment_status='UNPAID').update(
            payment_status='PAID',
            payment_method=metodo.capitalize()
        )
        
        if updated_count > 0:
            messages.success(request, f"Segnati come PAGATI {updated_count} ordini.")
        else:
            messages.warning(request, "Nessun ordine aggiornato (forse erano già pagati).")
            
        if next_url:
            return redirect(next_url)
        return redirect("app:order_list")        # Nel caso multiplo, torniamo sempre alla lista (preservando i filtri se possibile, ma qui semplifichiamo)

    # 2. LOGICA SINGOLA (TOGGLE)
    # Se non c'è una lista, deve esserci l'order_id passato dall'URL
    elif order_id:
        order = get_object_or_404(Order, pk=order_id)
        
        # Qui manteniamo la logica "Toggle" originale
        order.payment_method = metodo.capitalize()
        
        if order.payment_status == "PAID":
            order.payment_status = "UNPAID"
            order.payment_method = "NESSUNO"
        else:
            order.payment_status = "PAID"
        
        order.save()
        return redirect("app:order_detail", order_id=order_id)

    # 3. FALLBACK (Niente ID e niente Lista)
    else:
        messages.error(request, "Nessun ordine specificato.")
        if next_url:
            return redirect(next_url)
        return redirect("app:order_list")        # Nel caso multiplo, torniamo sempre alla lista (preservando i filtri se possibile, ma qui semplifichiamo)



@login_required
def profile(request, person_id):
    person = get_object_or_404(Person, pk=person_id)  # Più sicuro di .get()

    all_orders = person.orders.all()  # Usa il related_name se definito
    paginator = Paginator(all_orders, 5)
    page_number = request.GET.get("page")
    orders = paginator.get_page(page_number)

    return render(
        request,
        "app/person_profile.html",
        {
            "person": person,
            "orders": orders,
            "form": PersonUpdateForm(instance=person),
            "total_spent_month": person.get_spent_this_month(),
            "consumption_stats": person.get_consumption_breakdown(),
        },
    )


@login_required
def logout_view(request):
    """
    Effettua il logout dell'utente e reindirizza alla home
    """
    logout(request)
    return redirect("app:home")


def login_view(request):
    """
    Effettua il login dell'utente
    """

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("app:home")
        else:
            messages.error(request, "Credenziali non valide. Riprova.")
    else:
        form = AuthenticationForm()

    return render(request, "app/login.html", {"form": form})

@login_required
def upload_profile_picture(request):
    if request.method == "POST" and request.FILES.get("profile_pic"):
        person = request.user.person_profile
        person.profile_picture = request.FILES["profile_pic"]
        person.save()
    return redirect("app:profile", person_id=request.user.person_profile.id)


@login_required
def delete_profile_picture(request):
    if request.method == "POST":
        person = request.user.person_profile
        if person.profile_picture:
            person.profile_picture.delete(
                save=True
            )  # Elimina il file fisico e svuota il campo

    return redirect("app:profile", person_id=request.user.person_profile.id)


@login_required
@partner_required
@require_POST
def person_create_api(request):
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    nickname = request.POST.get("nickname", "").strip()
    email = request.POST.get("email", "").strip()
    is_partner = request.POST.get("is_partner") == "on"

    if not first_name or not last_name:
        return JsonResponse({"error": "Nome e cognome sono obbligatori."}, status=400)

    try:
        with transaction.atomic():
            # 1. Generazione username
            base_username = f"{first_name.lower()}{last_name.lower()}".replace(" ", "")
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # 2. Recupero password dal .env
            default_pwd = os.getenv("DEFAULT_USER_PASSWORD", "password_di_emergenza123")

            # 3. Creazione Utente (passiamo la password direttamente qui)
            new_user = User.objects.create_user(
                username=username,
                first_name=first_name.capitalize(),
                last_name=last_name.capitalize(),
                email=email,
                password=default_pwd,
            )

            # 4. Creazione Persona
            person = Person.objects.create(
                first_name=first_name,
                last_name=last_name,
                nickname=nickname,
                email=email,
                is_partner=is_partner,
                user=new_user,
                must_change_password=True,  # Forziamo il cambio password al primo accesso
            )

        return JsonResponse(
            {
                "id": person.id,
                "full_name": str(person),
                "username": new_user.username,
                "is_staff": "1" if person.is_partner else "0",
            }
        )

    except Exception as e:
        # È buona norma loggare l'errore per il debug
        print(f"Errore API: {e}")
        return JsonResponse(
            {"error": "Errore interno durante la creazione."}, status=500
        )


@login_required
def force_password_change(request):
    person = request.user.person_profile
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            print("Password cambiata per utente:", user.username)
            # Importante: mantiene la sessione attiva dopo il cambio password
            update_session_auth_hash(request, user)

            # Aggiorniamo il flag della persona
            person.must_change_password = False
            print("Aggiornamento flag must_change_password per:", person)
            person.save()

            messages.success(
                request, "Password aggiornata con successo! Ora puoi usare l'app."
            )
            return redirect("app:home")
        else:
            messages.error(request, "Controlla dove stai inserendo i dati. Riprova.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "app/force_password_change.html", {"form": form})


def sezione_view(request):
    return render(request, "app/sezione.html")


@partner_required
def export_orders_api(request):
    """
    Esporta gli ordini in formato excel (.xlsx)
    """
    import openpyxl
    from io import BytesIO
    from django.http import HttpResponse  # Import necessario per la risposta file

    # 1. Recupero dati
    orders = (
        Order.objects.select_related("person", "created_by")
        .prefetch_related("items__product")
        .all()
        .order_by("-created_at")
    )

    # 2. Setup Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ordini"

    # 3. Intestazioni
    headers = [
        "ID Ordine",
        "Data Creazione",
        "Persona",
        "Creato Da",
        "Stato Pagamento",
        "Metodo Pagamento",
        "Totale Ordine",
        "Prodotti (Nome x Quantità @ Prezzo)",
        "Note",
    ]
    ws.append(headers)

    # 4. Dati ordini
    for order in orders:
        # Recuperiamo gli items una volta sola per efficienza
        items = order.items.all()

        # Generiamo la stringa dei prodotti
        products_str = "; ".join(
            [
                f"{item.product.name} x {item.quantity} @ {item.price_at_order}"
                for item in items
            ]
        )

        # --- CORREZIONE ERRORE QUI ---
        # Invece di chiamare order.get_total_amount(), calcoliamo il totale qui
        # Oppure potresti usare order.total se è una property nel modello
        total_amount = sum(item.quantity * item.price_at_order for item in items)

        row = [
            order.id,
            order.created_at.strftime("%Y-%m-%d %H:%M"),
            str(order.person),
            order.created_by.username if order.created_by else "Sistema",
            order.get_payment_status_display(),  # Usa get_..._display() per avere il testo leggibile (es. "Pagato") invece di "PAID"
            order.payment_method,
            f"{total_amount:.2f} €",  # Usiamo la variabile calcolata sopra
            products_str,
            order.notes,
        ]
        ws.append(row)

    # 5. Regola larghezza colonne (Estetica)
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        adjusted_width = max_length + 2
        # Un piccolo limite per evitare colonne giganti
        if adjusted_width > 50:
            adjusted_width = 50
        ws.column_dimensions[column].width = adjusted_width

    # 6. Salvataggio e Response
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # NOTA: Per scaricare un file si usa HttpResponse, non JsonResponse
    response = HttpResponse(
        output.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = "attachment; filename=ordini_export.xlsx"

    return response


# ------------------------


def check_party_mode(request):
    settings, _ = GlobalSettings.objects.get_or_create(pk=1)
    remaining = settings.get_remaining_lock_time()

    return JsonResponse(
        {
            "active": settings.party_mode_active,
            "locked": remaining > 0,  # True se non si può ancora spegnere
            "remaining_seconds": int(remaining),
        }
    )


@partner_required
@require_POST
def toggle_party_mode(request):
    settings, _ = GlobalSettings.objects.get_or_create(pk=1)

    data = json.loads(request.body)
    wants_active = data.get("active")
    error_msg = None

    if wants_active:
        if not settings.party_mode_active:
            settings.party_mode_active = True
            settings.last_party_start = timezone.now()
            settings.save()
    else:
        # --- DISATTIVAZIONE ---
        remaining = settings.get_remaining_lock_time()
        if remaining <= 0:
            settings.party_mode_active = False
            settings.save()
        else:
            # Calcoliamo il tempo in base al DEBUG di Django
            tempo = "60 secondi" if django_settings.DEBUG else "60 minuti"
            error_msg = f"⚠️ Il college party deve durare almeno {tempo}! Non fare il guastafeste."
            messages.error(request, error_msg)

    # Restituiamo lo stato aggiornato
    remaining_now = settings.get_remaining_lock_time()
    return JsonResponse(
        {
            "status": "ok" if not error_msg else "error",
            "active": settings.party_mode_active,
            "locked": remaining_now > 0,
            "remaining_seconds": int(remaining_now),
            "error_message": error_msg  # Passiamo il messaggio al JS
        }
    )