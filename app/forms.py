from django import forms
from .models import Person
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm

User = get_user_model()


class CustomPasswordResetForm(PasswordResetForm):
    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip()
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError(
                "Nessun account trovato con questa email. "
                "Se non l'hai mai inserita nel profilo, contatta l'admin per il reset manuale."
            )
        return email

class OrderFilterForm(forms.Form):
    person = forms.ModelChoiceField(
        queryset=Person.objects.all(),
        required=False,
        label="Persona",
        empty_label="Qualsiasi persona",
        # Usiamo un ID specifico per agganciare TomSelect
        widget=forms.Select(
            attrs={"class": "form-select", "id": "person-filter-select"}
        ),
    )

    status = forms.ChoiceField(
        required=False,
        choices=[("", "Tutti gli stati"), ("PAID", "Pagato"), ("UNPAID", "Non Pagato")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    date = forms.DateField(
        required=False,
        label="Data esatta",
        # 'type': 'date' fa apparire il calendario su smartphone
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )


class PersonUpdateForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = ["first_name", "last_name", "nickname", "email"]
        # Aggiungiamo classi Bootstrap per lo stile
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "nickname": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }
