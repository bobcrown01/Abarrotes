let cart = [];
let totalItems = cart.reduce((sum, item) => sum + item.qty, 0);

function addToCart(product) {

    // Buscar si ya existe en el carrito
    const existing = cart.find(item => item.barcode === product.barcode);

    if (existing) {
        existing.qty += 1;  // aumentar cantidad
    } else {
        cart.push({
            name: product.name,
            price: product.price,
            barcode: product.barcode,
            qty: 1
        });
    }

    renderCart();
}

function changeQty(barcode, delta) {
    const item = cart.find(i => i.barcode === barcode);
    if (!item) return;

    item.qty += delta;

    if (item.qty <= 0) {
        cart = cart.filter(i => i.barcode !== barcode);
    }

    renderCart();
}

function renderCart() {
    const cartArea = document.getElementById("cart-area");

    if (cart.length === 0) {
        cartArea.innerHTML = `
            <h4 class="mb-3"><i class="fa-solid fa-cart-shopping"></i> Venta</h4>
            <p class="text-secondary">Carrito vacío</p>
        `;
        return;
    }

    let html = `
        <h4 class="mb-3"><i class="fa-solid fa-cart-shopping"></i> Venta</h4>
        <ul class="list-group mb-3">
    `;

    let total = 0;
    let totalItems = 0;

    cart.forEach(item => {
        const subtotal = item.qty * item.price;
        total += subtotal;
        totalItems += item.qty;

        html += `
            <li class="list-group-item cart-item d-flex justify-content-between align-items-center">
                
                <div class="d-flex align-items-center gap-2">

                    <div class="qty-box">
                        <button class="qty-btn" onclick="changeQty('${item.barcode}', -1)">−</button>
                        <span class="qty-number">${item.qty}</span>
                        <button class="qty-btn" onclick="changeQty('${item.barcode}', 1)">+</button>
                    </div>

                    <div>
                        <strong>${item.name}</strong><br>
                        <small>$${item.price.toFixed(2)} c/u</small>
                    </div>

                </div>

                <span>$${subtotal.toFixed(2)}</span>
            </li>
        `;

    });

    html += `
        </ul>

        <div class="mt-2">
            <strong>Subtotal – ${totalItems} ítems</strong>
            <p class="text-light">$${total.toFixed(2)}</p>
        </div>

        <div class="mt-3">
            <button class="btn btn-primary w-100 py-2" onclick="chargeSale()">
                Cobrar: $${total.toFixed(2)}
            </button>
        </div>
    `;

    cartArea.innerHTML = html;
}

function createPaymentModal(total) {

    // Si ya existe un modal previo, eliminarlo
    const oldModal = document.getElementById("payment-modal");
    if (oldModal) oldModal.remove();

    // Crear contenedor principal
    const modal = document.createElement("div");
    modal.id = "payment-modal";
    modal.className = "payment-overlay";

    // Contenido del modal
    modal.innerHTML = `
        <div class="payment-window">

            <h3 class="payment-title">Pago</h3>

            <div class="payment-total">
                <span>Total a pagar</span>
                <strong>$${total.toFixed(2)}</strong>
            </div>

            <button class="btn-tip">Agregar propina</button>

            <div class="payment-cash">
                <label>Recibido en efectivo</label>
                <input type="text" id="cash-input" value="$0.00">

                <div class="cash-buttons">
                    <button onclick="setCash(60)">$60.00</button>
                    <button onclick="setCash(100)">$100.00</button>
                    <button onclick="setCash(150)">$150.00</button>
                </div>
            </div>

            <h4 class="payment-subtitle">Agregar método de pago</h4>

            <div class="payment-methods">
                <button class="method">Venta a crédito</button>
                <button class="method">Débito</button>
                <button class="method">Crédito</button>
                <button class="method">Transferencia</button>
                <button class="method">Saldo monedero</button>
                <button class="method">Link de pago</button>
            </div>

            <button class="btn-close" onclick="closePaymentModal()">Cerrar</button>

        </div>
    `;

    // Insertar modal en el DOM
    document.body.appendChild(modal);
}

function closePaymentModal() {
    const modal = document.getElementById("payment-modal");
    if (modal) modal.remove();
}

function chargeSale() {
    let total = cart.reduce((sum, item) => sum + item.qty * item.price, 0);

    createPaymentModal(total);
}

function setCash(amount) {
    document.getElementById("cash-input").value = "$" + amount.toFixed(2);
}


document.addEventListener("DOMContentLoaded", () => {

    const COLS = 5;      // ← 5 columnas
    const TOTAL = 25;    // ← 5 filas × 5 columnas

    fetch("static/data/products.json")
        .then(response => response.json())
        .then(products => {

            const tableBody = document.querySelector("#productTable tbody");
            if (!tableBody) return;

            let row = null;

            // Crear filas con productos reales
            products.forEach((product, index) => {

                // Crear nueva fila cada 5 productos
                if (index % COLS === 0) {
                    row = document.createElement("tr");
                    tableBody.appendChild(row);
                }

                const cell = document.createElement("td");
                cell.className = "product-cell";

                cell.innerHTML = `
                    <img src="${product.image}" class="product-img">
                    <div class="product-name">${product.name}</div>
                    <div class="product-price">$${product.price.toFixed(2)}</div>
                    <div class="product-barcode">${product.barcode}</div>
                `;

                row.appendChild(cell);

                cell.addEventListener("click", () => {
                        addToCart(product);
                    });
            });

            // Rellenar con vacíos hasta completar 25 celdas
            const missing = TOTAL - products.length;

            for (let i = 0; i < missing; i++) {

                // Si la última fila está llena, crear una nueva
                if ((products.length + i) % COLS === 0) {
                    row = document.createElement("tr");
                    tableBody.appendChild(row);
                }

                const emptyCell = document.createElement("td");
                emptyCell.className = "product-cell empty";
                emptyCell.innerHTML = `<div class="product-name">Vacío</div>`;
                row.appendChild(emptyCell);
            }

        });

});
