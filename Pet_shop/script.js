document.addEventListener("DOMContentLoaded", () => {
    const cartItems = document.getElementById("cart-items");
    const totalPrice = document.getElementById("total-price");
    let cart = [];

    document.querySelectorAll(".add-to-cart").forEach(button => {
        button.addEventListener("click", event => {
            const product = event.target.closest(".product");
            const id = product.dataset.id;
            const name = product.dataset.name;
            const price = parseFloat(product.dataset.price); // Исправлено parseInt → parseFloat

            const existingItem = cart.find(item => item.id === id);
            if (existingItem) {
                existingItem.quantity++;
            } else {
                cart.push({ id, name, price, quantity: 1 });
            }
            updateCart();
        });
    });

    function updateCart() {
        cartItems.innerHTML = "";
        let total = 0;
        cart.forEach(item => {
            total += item.price * item.quantity;
            const li = document.createElement("li");
            li.textContent = `${item.name} x${item.quantity} - ${item.price * item.quantity} тг.`; // Исправлена валюта
            cartItems.appendChild(li);
        });
        totalPrice.textContent = total;
    }

    //-------Карусель-------//
    let currentIndex = 0;
    const container = document.querySelector(".carousel-container");
    const totalSlides = document.querySelectorAll(".slide").length;
    let autoScroll = setInterval(nextSlide, 4000); // Автопрокрутка

    function showSlide(index) {
        if (index >= totalSlides) {
            currentIndex = 0;
        } else if (index < 0) {
            currentIndex = totalSlides - 1;
        } else {
            currentIndex = index;
        }

        container.style.transform = `translateX(-${currentIndex * 100}%)`;
    }

    function nextSlide() {
        showSlide(currentIndex + 1);
    }

    function prevSlide() {
        showSlide(currentIndex - 1);
    }

    function resetAutoScroll() {
        clearInterval(autoScroll);
        autoScroll = setInterval(nextSlide, 4000);
    }

    document.querySelector(".next").addEventListener("click", () => {
        nextSlide();
        resetAutoScroll();
    });

    document.querySelector(".prev").addEventListener("click", () => {
        prevSlide();
        resetAutoScroll();
    });

});
