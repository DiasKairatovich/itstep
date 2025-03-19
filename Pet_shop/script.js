document.addEventListener("DOMContentLoaded", () => {
    const cartItems = document.getElementById("cart-items");
    const totalPrice = document.getElementById("total-price");
    let cart = [];

    document.querySelectorAll(".add-to-cart").forEach(button => {
        button.addEventListener("click", event => {
            const product = event.target.closest(".product");
            const id = product.dataset.id;
            const name = product.dataset.name;
            const price = parseFloat(product.dataset.price);

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
    // ------- Карусель ------- //
    let currentIndex = 0;
    const container = document.querySelector(".carousel-container");
    const slides = document.querySelectorAll(".slide");
    const totalSlides = slides.length;
    const indicatorsContainer = document.querySelector(".carousel-indicators");
    let autoScroll = setInterval(nextSlide, 4000);

    // Создаем индикаторы (точки)
    slides.forEach((_, index) => {
        const dot = document.createElement("span");
        dot.classList.add("indicator");
        if (index === 0) dot.classList.add("active");
        dot.addEventListener("click", () => goToSlide(index));
        indicatorsContainer.appendChild(dot);
    });

    function updateIndicators() {
        document.querySelectorAll(".indicator").forEach((dot, index) => {
            dot.classList.toggle("active", index === currentIndex);
        });
    }

    function showSlide(index) {
        if (index >= totalSlides) {
            currentIndex = 0;
        } else if (index < 0) {
            currentIndex = totalSlides - 1;
        } else {
            currentIndex = index;
        }

        container.style.transform = `translateX(-${currentIndex * 100}%)`;
        updateIndicators();
    }

    function nextSlide() {
        showSlide(currentIndex + 1);
    }

    function prevSlide() {
        showSlide(currentIndex - 1);
    }

    function goToSlide(index) {
        showSlide(index);
        resetAutoScroll();
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

    // Остановка автопрокрутки при наведении
    document.querySelector(".carousel").addEventListener("mouseenter", () => {
        clearInterval(autoScroll);
    });

    document.querySelector(".carousel").addEventListener("mouseleave", () => {
        resetAutoScroll();
    });
});
