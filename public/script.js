/* =========================================
   Coffee Point — JavaScript
   ========================================= */

// === NAVBAR: scroll effect & burger ===
const navbar = document.getElementById('navbar');
const burger = document.getElementById('burger');
const navLinks = document.getElementById('nav-links');

window.addEventListener('scroll', () => {
  if (window.scrollY > 60) {
    navbar.classList.add('scrolled');
  } else {
    navbar.classList.remove('scrolled');
  }
});

burger.addEventListener('click', () => {
  navLinks.classList.toggle('open');
});

// Close menu on link click
navLinks.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => navLinks.classList.remove('open'));
});

// === MENU TABS ===
const tabs = document.querySelectorAll('.tab');
const menuCards = document.querySelectorAll('.menu-card');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    // Remove active from all tabs
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    const category = tab.dataset.tab;

    menuCards.forEach((card, i) => {
      if (card.dataset.category === category) {
        card.style.display = 'flex';
        // Stagger animation
        card.style.animationDelay = `${i * 0.05}s`;
        card.style.animation = 'none';
        card.offsetHeight; // reflow
        card.style.animation = 'fadeInUp 0.5s ease both';
      } else {
        card.style.display = 'none';
      }
    });
  });
});

// === SCROLL REVEAL ===
const revealElements = document.querySelectorAll(
  '.about-grid, .menu-grid, .prices-grid, .contacts-grid, ' +
  '.chat-widget-container, .section-title, .section-tag, .section-subtitle'
);

revealElements.forEach(el => el.classList.add('reveal'));

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.12 }
);

revealElements.forEach(el => observer.observe(el));

// === SMOOTH SCROLL for anchors ===
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', (e) => {
    const target = document.querySelector(anchor.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// === MENU CARDS: hover ripple ===
document.querySelectorAll('.menu-card').forEach(card => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    card.style.setProperty('--x', `${x}%`);
    card.style.setProperty('--y', `${y}%`);
  });
});

console.log('☕ Coffee Point — сайт загружен.');
