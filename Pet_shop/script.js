document.addEventListener("DOMContentLoaded", () => {
    const products = [
        { id: 1, name: "Собачий корм", category: "Корм", price: 16893, img: "images/dog_food.jpg" },
        { id: 2, name: "Кошачий корм", category: "Корм", price: 3977, img: "images/cat_food.jpg" },
        { id: 3, name: "Игрушка для собаки", category: "Игрушки", price: 2970, img: "images/dog_toy.jpg" },
        { id: 4, name: "Игрушка для кошки", category: "Игрушки", price: 2900, img: "images/cat_toy.jpg" }
    ];

    const cart = JSON.parse(localStorage.getItem("cart")) || [];

    function renderProducts(filter = "Все") {
        const productContainer = document.getElementById("products");
        productContainer.innerHTML = ""; // Очистка перед рендером

        products.forEach(product => {
            if (filter === "Все" || product.category === filter) {
                const productElement = document.createElement("div");
                productElement.classList.add("product");
                productElement.innerHTML = `

                    <img src="${product.img}" alt="${product.name}">
                    <h3>${product.name}</h3>
                    <p>Цена: ${product.price} ₸.</p>
                    <button onclick="addToCart(${product.id})">Добавить в корзину</button>
                `;
                productContainer.appendChild(productElement);
            }
        });
    }

    function addToCart(id) {
        const product = products.find(p => p.id === id);
        const cartItem = cart.find(item => item.id === id);

        if (cartItem){
            cartItem.quantity++;
        }else{
            cart.push({ ...product, quantity: 1});
        }

        localStorage.setItem("cart", JSON.stringify(cart));
        renderCart();
    }

    function renderCart() {
        const cartContainer = document.getElementById("cart-items");
        cartContainer.innerHTML = ""; // Очистка перед рендером

        cart.forEach(item => {
            const cartItem = document.createElement("li");
            cartItem.innerHTML = `
                ${item.name} - ${item.price}₽ x ${item.quantity}
                <button onclick="removeFromCart(${item.id})">❌</button>
            `;
            cartContainer.appendChild(cartItem);
        });

        const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
        document.getElementById("cart-total").textContent = `Итого: ${total}₸`;
    }

    function removeFromCart(id) {
        const index = cart.findIndex(item => item.id === id);
        if (index !== -1) {
            if (cart[index].quantity > 1) {
                cart[index].quantity--;
            } else {
                cart.splice(index, 1);
            }
        }
        localStorage.setItem("cart", JSON.stringify(cart));
        renderCart();
    }

    function clearCart() {
        localStorage.removeItem("cart");
        cart.length = 0;
        renderCart();
    }

    document.getElementById("clear-cart").addEventListener("click", clearCart);
    document.getElementById("category-filter").addEventListener("change", (e) => renderProducts(e.target.value));

    renderProducts(); // Вызываем функцию, чтобы товары появились на странице
    renderCart(); // Вызывается при каждом изменении корзины
});
