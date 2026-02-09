let cart = [];
let isStaff = true;
let tsPerson = null;

document.addEventListener('DOMContentLoaded', function() {
    
    // Riferimenti DOM
    const productsGrid = document.getElementById('products-grid');
    const warningMsg = document.getElementById('select-payer-warning');

    // --- FUNZIONI DI UTILITÀ ---

    // Aggiorna visivamente i prezzi sui badge
    function updateProductBadges() {
        const badges = document.querySelectorAll('.price-badge');
        badges.forEach(function(badge) {
            if (isStaff) {
                // Prezzo Staff
                badge.textContent = badge.getAttribute('data-staff') + '€';
                badge.classList.remove('bg-light', 'text-dark');
                badge.classList.add('bg-warning', 'text-dark'); 
            } else {
                // Prezzo Guest
                badge.textContent = badge.getAttribute('data-guest') + '€';
                badge.classList.remove('bg-warning');
                badge.classList.add('bg-light', 'text-dark');
            }
        });
    }

    // Mostra/Nascondi griglia prodotti
    function toggleGrid(show) {
        if (show) {
            productsGrid.classList.remove('d-none');
            warningMsg.classList.add('d-none');
        } else {
            productsGrid.classList.add('d-none');
            warningMsg.classList.remove('d-none');
        }
    }

    // Genera gli input nascosti per l'invio al server
    function generateHiddenInputs(container) {
        container.innerHTML = '';
        
        // 1. Iniezione Pagante
        const selectedPersonId = tsPerson.getValue();
        if (selectedPersonId) {
            const inputPerson = document.createElement('input');
            inputPerson.type = 'hidden'; 
            inputPerson.name = 'person'; 
            inputPerson.value = selectedPersonId;
            container.appendChild(inputPerson);
        }

        // 2. Iniezione Prodotti nel carrello
        cart.forEach(item => {
            // Nota: uso += per brevità, ma in loop intensivi meglio createElement
            container.innerHTML += `
                <input type="hidden" name="product" value="${item.id}">
                <input type="hidden" name="quantity" value="${item.qty}">
                <input type="hidden" name="offered_to" value="${item.offeredToId || ''}">
            `;
        });
    }

    // --- INIZIALIZZAZIONE TOMSELECT ---
    
    tsPerson = new TomSelect('#person-select', {
        valueField: 'id', labelField: 'text', searchField: 'text',
        placeholder: 'Chi paga?',
        options: PEOPLE_DATA,
        onChange: function(val) {
            if (val) {
                const opt = this.options[val];
                isStaff = opt ? opt.is_staff : false;
                updateProductBadges();
                toggleGrid(true);
            } else {
                toggleGrid(false);
                // Reset a staff default quando deselezionato per estetica
                isStaff = true; 
                updateProductBadges();
            }
            renderCart(); // Renderizza il carrello per aggiornare i totali col nuovo listino
        }
    });

    // --- SETUP INIZIALE ---
    toggleGrid(false);
    updateProductBadges();

    // --- GESTIONE SUBMIT FORM ---
    
    ['pos-form-desktop', 'pos-form-mobile'].forEach(formId => {
        const f = document.getElementById(formId);
        if(f) {
            f.addEventListener('submit', function(e) {
                // Controlli di validazione
                // if(cart.length === 0) { 
                //     e.preventDefault(); 
                //     alert("Carrello vuoto!"); 
                //     return; 
                // }
                // if(!tsPerson.getValue()) { 
                //     e.preventDefault(); 
                //     alert("Seleziona chi paga!"); 
                //     return; 
                // }
                
                // Generazione dati
                const containerId = formId === 'pos-form-desktop' ? 'hidden-inputs-desktop' : 'hidden-inputs-mobile';
                const container = document.getElementById(containerId);
                
                // Generiamo gli input. Poiché non c'è e.preventDefault() qui (se tutto è ok),
                // il browser invierà il form subito dopo questa funzione.
                generateHiddenInputs(container);
            });
        }
    });

    // --- QUICK PERSON AJAX (Se presente) ---
    const quickPersonForm = document.getElementById('form-quick-person');
    if(quickPersonForm) {
        quickPersonForm.addEventListener('submit', function(e){
            e.preventDefault();
            const formData = new FormData(this);
            fetch(API_URLS.personCreate, {
                method: 'POST', body: formData, headers: {'X-CSRFToken': formData.get('csrfmiddlewaretoken')}
            })
            .then(r => r.json()).then(data => {
                if(data.error) alert(data.error);
                else {
                    tsPerson.addOption({id: data.id, text: data.full_name, is_staff: data.is_staff === "1"});
                    tsPerson.setValue(data.id);
                    // Nascondi modale (Bootstrap 5)
                    const modalEl = document.getElementById('modalAddPerson');
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if(modal) modal.hide();
                    this.reset();
                }
            });
        });
    }
});

// --- FUNZIONI GLOBALI (Richiamate dall'HTML) ---

window.filterCategory = (catId, btn) => {
    document.querySelectorAll('.category-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.product-item').forEach(el => {
        el.style.display = (catId === 'all' || el.dataset.category === catId) ? 'block' : 'none';
    });
};

window.addToCart = (id, name, pGuest, pStaff, cardElement) => {
    // Effetto Flash
    if(cardElement) {
        cardElement.classList.remove('flash-active');
        void cardElement.offsetWidth; 
        cardElement.classList.add('flash-active');
        setTimeout(() => cardElement.classList.remove('flash-active'), 300);
    }
    
    // Logica carrello
    const existing = cart.find(i => i.id === id && !i.offeredToId);
    if(existing) {
        existing.qty++;
    } else {
        cart.push({
            id, 
            name, 
            priceGuest: parseFloat(pGuest), 
            priceStaff: parseFloat(pStaff), 
            qty: 1, 
            offeredToId: null
        });
    }
    renderCart();
};

window.changeQty = (i, d) => { 
    cart[i].qty += d; 
    if(cart[i].qty <= 0) cart.splice(i, 1); 
    renderCart(); 
};

window.removeItem = (i) => { 
    cart.splice(i, 1); 
    renderCart(); 
};

window.toggleOffer = (i, checked) => { 
    cart[i].offeredToId = checked ? '' : null; 
    renderCart(); 
};

window.setOfferDest = (i, val) => { 
    cart[i].offeredToId = val; 
};

window.toggleCart = (forceState) => {
    const panel = document.getElementById('mobileCartPanel');
    const overlay = document.getElementById('cartOverlay');
    const chev = document.getElementById('mobileChevron');
    
    // Se forceState è undefined, inverte lo stato attuale
    const isOpen = (typeof forceState !== 'undefined') ? forceState : !panel.classList.contains('open');
    
    panel.classList.toggle('open', isOpen);
    overlay.classList.toggle('show', isOpen);
    chev.className = isOpen ? 'bi bi-chevron-down' : 'bi bi-chevron-up';
};

// Funzione di rendering principale
function renderCart() {
    const isMobile = window.innerWidth < 992;
    const container = isMobile ? document.getElementById('cart-items-mobile') : document.getElementById('cart-items-desktop');
    const totalEl = isMobile ? document.getElementById('cart-total-mobile-header') : document.getElementById('cart-total-desktop');
    
    container.innerHTML = '';
    let total = 0, count = 0;

    cart.forEach((item, idx) => {
        const price = isStaff ? item.priceStaff : item.priceGuest;
        const subtotal = price * item.qty;
        total += subtotal;
        count += item.qty;

        const isOffered = item.offeredToId !== null;
        
        // Creazione opzioni per la select "Offri a..."
        // Nota: PEOPLE_DATA deve essere globale
        let offerOptions = PEOPLE_DATA.map(p => 
            `<option value="${p.id}" ${item.offeredToId == p.id ? 'selected' : ''}>${p.text}</option>`
        ).join('');

        const row = document.createElement('div');
        row.className = 'd-flex flex-column border-bottom py-2';
        row.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <span class="fw-bold text-truncate w-50">${item.name}</span>
                <span class="fw-bold">${subtotal.toFixed(2)}€</span>
            </div>
            <div class="d-flex justify-content-between align-items-center mt-2">
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-outline-secondary" onclick="changeQty(${idx}, -1)">-</button>
                    <button type="button" class="btn btn-light disabled text-dark border fw-bold" style="width:35px">${item.qty}</button>
                    <button type="button" class="btn btn-outline-secondary" onclick="changeQty(${idx}, 1)">+</button>
                </div>
                <div class="form-check form-switch ms-2">
                    <input class="form-check-input" type="checkbox" id="off-${idx}" ${isOffered?'checked':''} onchange="toggleOffer(${idx}, this.checked)">
                    <label class="form-check-label small" for="off-${idx}">Offri</label>
                </div>
                <button type="button" class="btn btn-sm text-danger ms-auto" onclick="removeItem(${idx})"><i class="bi bi-trash"></i></button>
            </div>
            ${isOffered ? `<div class="mt-2"><select class="form-select form-select-sm" onchange="setOfferDest(${idx}, this.value)"><option value="">-- A chi? --</option>${offerOptions}</select></div>` : ''}
        `;
        container.appendChild(row);
    });

    totalEl.textContent = total.toFixed(2) + ' €';
    if(isMobile) {
        const badge = document.getElementById('mobile-badge-count');
        if(badge) badge.textContent = count;
    }
}