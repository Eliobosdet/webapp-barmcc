import os
import django
import csv
from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist

# 1. Configurazione ambiente Django
# IMPORTANTE: Sostituisci 'BARMCC' con il nome della cartella che contiene il tuo settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'barmcc.settings')
django.setup()

from django.contrib.auth.models import User
from app.models import Category, Product, Person, GlobalSettings

def run_setup():
    print("🚀 Inizio inizializzazione database...")

    # --- 1. RECUPERO PASSWORD DA .ENV ---
    # Lo script cercherà la variabile DEFAULT_USER_PASSWORD che hai già impostato
    default_password = os.getenv("DEFAULT_USER_PASSWORD", "PasswordDiEmergenza123!")

    # --- 2. CREAZIONE SUPERUSER E PROFILO CORRA ---
    username = "elioc"
    email = "eliobosdet@gmail.com"

    user, created = User.objects.get_or_create(username=username, defaults={
        'email': email,
        'is_staff': True,
        'is_superuser': True,
    })
    
    if created:
        user.set_password(default_password)
        user.save()
        print(f"✅ Superuser '{username}' creato con la password del tuo .env.")

    # Creazione profilo Person per te (Creatore)
    corra, p_created = Person.objects.get_or_create(
        nickname="Corra",
        defaults={
            'first_name': 'Elio',
            'last_name': 'Corradini',
            'email': email,
            'is_partner': True,
            'user': user,
            'must_change_password': False
        }
    )
    if p_created:
        print("✅ Profilo Person 'Corra' creato e collegato all'admin.")

    # --- 3. IMPOSTAZIONI GLOBALI ---
    GlobalSettings.objects.get_or_create(pk=1, defaults={'party_mode_active': False})
    print("✅ Impostazioni Globali inizializzate.")

    # --- 4. IMPORTAZIONE PRODOTTI DA CSV ---
    csv_file_path = 'prodotti.csv'
    
    if not os.path.exists(csv_file_path):
        print(f"❌ Errore: Il file '{csv_file_path}' non è stato trovato nella root.")
        return

    print("📦 Importazione prodotti in corso...")
    try:
        with open(csv_file_path, mode='r', encoding='utf-8') as file:
            # Assicurati che le intestazioni nel CSV siano esattamente queste
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                cat_name = row['Categoria'].strip()
                prod_name = row['Prodotto'].strip()
                
                # Pulizia prezzi (rimuove € e sistema virgole/punti)
                raw_guest = row['Prezzo Guest'].replace('€', '').replace(',', '.').strip()
                raw_staff = row['Prezzo Staff'].replace('€', '').replace(',', '.').strip()
                
                price_g = Decimal(raw_guest)
                price_s = Decimal(raw_staff)

                # Creazione Categoria
                category, _ = Category.objects.get_or_create(name=cat_name)

                # Creazione Prodotto
                product, prod_created = Product.objects.get_or_create(
                    name=prod_name,
                    defaults={
                        'category': category,
                        'price_guest': price_g,
                        'price_staff': price_s,
                        'is_active': True
                    }
                )
                if prod_created:
                    count += 1
            
            print(f"✅ Importazione completata: {count} nuovi prodotti aggiunti.")
    
    except KeyError as e:
        print(f"❌ Errore: Controlla che le intestazioni del CSV siano corrette (Manca: {e})")
    except Exception as e:
        print(f"❌ Errore imprevisto: {e}")

    print("✨ Processo terminato correttamente!")

if __name__ == '__main__':
    run_setup()