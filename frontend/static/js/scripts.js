// Navigation Bar Interactivity
document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".nav-links a");
    navLinks.forEach(link => {
        link.addEventListener("mouseenter", () => {
            link.style.color = "#a777e3";
        });
        link.addEventListener("mouseleave", () => {
            link.style.color = "#555";
        });
    });
});

// Form Validation
const forms = document.querySelectorAll("form");
forms.forEach(form => {
    form.addEventListener("submit", event => {
        const inputs = form.querySelectorAll("input");
        let valid = true;

        inputs.forEach(input => {
            if (!input.value.trim()) {
                valid = false;
                input.style.borderColor = "red";
                setTimeout(() => {
                    input.style.borderColor = "#ccc";
                }, 2000);
            }
        });

        if (!valid) {
            event.preventDefault();
            alert("Please fill out all fields!");
        }
    });
});

// Dashboard Interactivity
const dashboardCards = document.querySelectorAll(".dashboard-card");
dashboardCards.forEach(card => {
    card.addEventListener("mouseenter", () => {
        card.style.boxShadow = "0 4px 15px rgba(0, 0, 0, 0.2)";
        card.style.transform = "scale(1.02)";
    });
    card.addEventListener("mouseleave", () => {
        card.style.boxShadow = "0 2px 10px rgba(0, 0, 0, 0.1)";
        card.style.transform = "scale(1)";
    });
});

// Modal for Room Booking
const roomModals = document.querySelectorAll(".room-modal");
roomModals.forEach(modal => {
    const closeModalBtn = modal.querySelector(".close-modal");
    closeModalBtn.addEventListener("click", () => {
        modal.style.display = "none";
    });
});

// Smooth Scrolling for Navigation
const smoothScrollLinks = document.querySelectorAll("a[href^='#']");
smoothScrollLinks.forEach(link => {
    link.addEventListener("click", event => {
        event.preventDefault();
        const target = document.querySelector(link.getAttribute("href"));
        if (target) {
            target.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }
    });
});

// Toggle Theme
const themeToggleBtn = document.querySelector(".theme-toggle");
themeToggleBtn?.addEventListener("click", () => {
    document.body.classList.toggle("dark-theme");
});
