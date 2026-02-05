import os
import uuid
from django.conf import settings
from django.db import models
from django.db.models import Sum, F, Q
from django.db.models.functions import Coalesce
from django.utils import timezone


def profile_pic_path(instance, filename):
    # Genera un nome file univoco usando un UUID (es: 550e8400-e29b...)
    ext = filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    # Organizza i file in sottocartelle per anno/mese/giorno (opzionale ma consigliato)
    return os.path.join("profile_pics", filename)


class Person(models.Model):
    """
    Rappresenta una persona reale (ospite del bar)
    Può essere collegata o meno ad un account utente Django.
    """

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    is_partner = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=True)

    profile_picture = models.ImageField(
        upload_to=profile_pic_path, null=True, blank=True, verbose_name="Foto profilo"
    )

    # account utente opzionale
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="person_profile",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Persona"
        verbose_name_plural = "Persone"
        ordering = ["first_name", "last_name"]

    def __str__(self):
        # if self.nickname:
        #     return f"{self.first_name} ({self.nickname})"
        return f"{self.first_name} {self.last_name}"

    # save capitalized
    def save(self, *args, **kwargs):
        # 1. Capitalizzazione nomi (il tuo codice esistente)
        if self.first_name:
            self.first_name = " ".join(p.capitalize() for p in self.first_name.split())
        if self.last_name:
            self.last_name = " ".join(p.capitalize() for p in self.last_name.split())
        
        # 2. Salviamo prima il file originale
        super().save(*args, **kwargs)

        # 3. Ora lo riapriamo e lo ridimensioniamo se esiste
        if self.profile_picture:
            try:
                img_path = self.profile_picture.path
                
                # Controllo se il file esiste davvero su disco
                if os.path.exists(img_path):
                    with Image.open(img_path) as img:
                        # Se l'immagine è più grande di 400x400, ridimensionala
                        if img.height > 400 or img.width > 400:
                            output_size = (400, 400)
                            img.thumbnail(output_size)
                            
                            # Salva sovrascrivendo l'originale (ottimizzando)
                            img.save(img_path, quality=70, optimize=True)
            except Exception as e:
                # Se qualcosa va storto col resize, non bloccare tutto, stampa solo l'errore
                print(f"Errore resize immagine: {e}")

    @property
    def total_spent(self):
        """Totale storico pagato"""
        return (
            self.orders.filter(payment_status="PAID").aggregate(
                total=Sum(F("items__quantity") * F("items__price_at_order"))
            )["total"]
            or 0
        )

    @property
    def total_unpaid(self):
        """Totale debito attuale"""
        return (
            self.orders.filter(payment_status="UNPAID").aggregate(
                total=Sum(F("items__quantity") * F("items__price_at_order"))
            )["total"]
            or 0
        )

    @property
    def total_spent_percentage(self):
        """Percentuale di spesa rispetto al totale storico (usato per classifiche)"""
        total_all = (
            Order.objects.filter(payment_status="PAID").aggregate(
                total=Sum(F("items__quantity") * F("items__price_at_order"))
            )["total"]
            or 0
        )

        if total_all == 0:
            return 0

        return (self.total_spent / total_all) * 100

    def get_spent_this_month(self):
        """Totale pagato nel mese corrente"""
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (
            self.orders.filter(
                payment_status="PAID", created_at__gte=start_of_month
            ).aggregate(total=Sum(F("items__quantity") * F("items__price_at_order")))[
                "total"
            ]
            or 0
        )

    def get_consumption_breakdown(self):
        """
        Restituisce i prodotti consumati dalla persona con le relative quantità.
        Include acquisti personali e regali ricevuti.
        """
        return (
            Product.objects.annotate(
                consumed_quantity=Coalesce(
                    Sum(
                        "orderitem__quantity",
                        filter=(
                            # Caso A: L'utente ha comprato il prodotto per sé
                            (
                                Q(orderitem__order__person=self)
                                & Q(orderitem__offered_to__isnull=True)
                            )
                            |
                            # Caso B: Qualcun altro ha comprato il prodotto per questo utente
                            Q(orderitem__offered_to=self)
                        ),
                    ),
                    0,
                )
            )
            .filter(consumed_quantity__gt=0)
            .order_by("-consumed_quantity")
        )


class Category(models.Model):
    """
    Categoria di prodotti (es. Drink, Cibo, Gadget, ...)
    """

    name = models.CharField(max_length=100)

    @staticmethod
    def get_all_top_consumers():

        results = {}
        categories = Category.objects.all()

        for cat in categories:
            # Per ogni categoria, cerchiamo i consumatori
            top_person = (
                Person.objects.annotate(
                    # Somma oggetti RICEVUTI in questa categoria
                    qty_ricevuta=Coalesce(
                        Sum(
                            "items_received__quantity",
                            filter=Q(
                                items_received__product__category=cat,
                                items_received__order__payment_status="PAID",
                            ),
                        ),
                        0,
                    ),
                    # Somma oggetti COMPRATI (e non regalati ad altri) in questa categoria
                    qty_comprata=Coalesce(
                        Sum(
                            "orders__items__quantity",
                            filter=Q(
                                orders__items__product__category=cat,
                                orders__items__offered_to__isnull=True,
                                orders__items__order__payment_status="PAID",
                            ),
                        ),
                        0,
                    ),
                )
                .annotate(total_cat=F("qty_ricevuta") + F("qty_comprata"))
                .filter(total_cat__gt=0)
                .order_by("-total_cat")
                .first()
            )

            if top_person:
                results[cat] = top_person

        return results

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorie"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Prodotti venduti al bar
    """

    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, null=True, blank=True
    )
    # capacity_liters = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    price_guest = models.DecimalField(max_digits=7, decimal_places=2)
    price_staff = models.DecimalField(max_digits=7, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}"

    def get_price_for_person(self, person: Person):
        # se la persona ha un account staff, applica il prezzo staff
        if person and person.is_partner:
            return self.price_staff
        return self.price_guest

    # order by name by default
    class Meta:
        ordering = ["name"]

    # save capitalized
    def save(self, *args, **kwargs):
        if self.name:
            self.name = " ".join(p.capitalize() for p in self.name.split())
        super().save(*args, **kwargs)


class OrderQuerySet(models.QuerySet):
    def unpaid(self):
        return self.filter(payment_status="UNPAID")

    def by_person(self, person):
        return self.filter(person=person)


class OrderManager(models.Manager):
    def get_queryset(self):
        return OrderQuerySet(self.model, using=self._db)

    def unpaid_count(self):
        return self.get_queryset().unpaid().count()


class Order(models.Model):
    """
    Ordine effettuato al bancone, inserito dallo staff.
    È sempre associato a una Persona (registrata o meno).
    """

    PAYMENT_STATUS_CHOICES = [
        ("UNPAID", "Non pagato"),
        ("PAID", "Pagato"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("CASH", "Contanti"),
        ("PAYPAL", "PayPal"),
        ("NESSUNO", "Nessuno"),
    ]

    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="orders")

    # utente staff che ha registrato l'ordine
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders_created",
    )

    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS_CHOICES, default="UNPAID"
    )

    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrderManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Ordine #{self.pk} - {self.person} - {self.get_payment_status_display()}"
        )

    @property
    def total(self):
        # somma delle righe
        return sum(item.subtotal for item in self.items.all())


class OrderItem(models.Model):
    """
    Riga di un ordine: prodotto + quantità + prezzo all'atto dell'ordine
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")

    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    quantity = models.PositiveIntegerField(default=1)

    # prezzo fissato al momento dell’ordine
    price_at_order = models.DecimalField(max_digits=7, decimal_places=2)

    offered_to = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="items_received",
    )

    # Modifica lo __str__ per chiarezza
    def __str__(self):
        res = f"{self.quantity} x {self.product.name}"
        if self.offered_to:
            res += f" (Offerto a {self.offered_to})"
        return res

    @property
    def subtotal(self):
        return self.quantity * self.price_at_order


class GlobalSettings(models.Model):
    party_mode_active = models.BooleanField(default=False)
    # Aggiungi questo campo
    last_party_start = models.DateTimeField(null=True, blank=True)

    @classmethod
    def is_party_active(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings.party_mode_active

    # Metodo helper per sapere se è bloccato
    def get_remaining_lock_time(self):
        if not self.party_mode_active or not self.last_party_start:
            return 0

        # DURATA DEL BLOCCO IN SECONDI (es. 60 secondi)
        LOCK_DURATION = 60 if os.getenv("DEBUG") == "True" else 3600

        elapsed = (timezone.now() - self.last_party_start).total_seconds()
        remaining = LOCK_DURATION - elapsed
        return max(0, remaining)
