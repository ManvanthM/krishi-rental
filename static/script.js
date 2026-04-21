document.addEventListener("DOMContentLoaded", () => {
    setupThemeToggle();
    setupValidation();
    setupRentalCalculator();
    setupScrollReveal();
    setupLandingMotion();
});

function setupThemeToggle() {
    const root = document.documentElement;
    const toggle = document.querySelector("[data-theme-toggle]");

    if (!toggle) {
        return;
    }

    const label = toggle.querySelector(".theme-toggle__label");
    const icon = toggle.querySelector(".theme-toggle__icon");

    function applyTheme(theme) {
        root.setAttribute("data-theme", theme);
        localStorage.setItem("krishi-theme", theme);

        const isDark = theme === "dark";
        toggle.setAttribute("aria-pressed", String(isDark));
        toggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");

        const sun = toggle.querySelector(".icon-sun");
        const moon = toggle.querySelector(".icon-moon");
        if (sun && moon) {
            sun.style.display = isDark ? "none" : "block";
            moon.style.display = isDark ? "block" : "none";
        }

        if (label) {
            label.textContent = "Theme"; // Keep label static or change to "Light/Dark"
        }
    }

    const currentTheme = root.getAttribute("data-theme") || "light";
    applyTheme(currentTheme);

    toggle.addEventListener("click", () => {
        const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(nextTheme);
    });
}

function setupValidation() {
    const forms = document.querySelectorAll(".validated-form");

    forms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            const aadhaar = form.querySelector('input[name="aadhaar"]');
            const phone = form.querySelector('input[name="phone"]');
            const password = form.querySelector('input[name="password"]');

            if (aadhaar && !/^\d{12}$/.test(aadhaar.value.trim())) {
                event.preventDefault();
                alert("Aadhaar number must contain exactly 12 digits.");
                aadhaar.focus();
                return;
            }

            if (phone && !/^\d{10}$/.test(phone.value.trim())) {
                event.preventDefault();
                alert("Phone number must contain exactly 10 digits.");
                phone.focus();
                return;
            }

            if (password && password.value.length < 6) {
                event.preventDefault();
                alert("Password must be at least 6 characters long.");
                password.focus();
                return;
            }

            const paymentInput = form.querySelector('input[name="payment_method"]');
            if (paymentInput && paymentInput.type === "hidden" && !paymentInput.value) {
                event.preventDefault();
                alert("Please select a payment method (UPI or Card).");
            }
        });
    });
}

function setupRentalCalculator() {
    const form = document.getElementById("rentalForm");
    if (!form) {
        return;
    }

    const fromDate = document.getElementById("from_date");
    const toDate = document.getElementById("to_date");
    const totalDays = document.getElementById("totalDays");
    const totalRent = document.getElementById("totalRent");
    const depositDisplay = document.getElementById("depositDisplay");

    const rentPerDay = parseFloat(form.dataset.rentPerDay || "0");
    const deposit = parseFloat(form.dataset.deposit || "0");
    const maxDays = parseInt(form.dataset.maxDays || "5", 10);

    function addDays(dateStr, days) {
        const dateValue = new Date(dateStr);
        dateValue.setDate(dateValue.getDate() + days);
        const yyyy = dateValue.getFullYear();
        const mm = String(dateValue.getMonth() + 1).padStart(2, "0");
        const dd = String(dateValue.getDate()).padStart(2, "0");
        return `${yyyy}-${mm}-${dd}`;
    }

    fromDate.addEventListener("change", () => {
        if (fromDate.value) {
            toDate.min = fromDate.value;
            toDate.max = addDays(fromDate.value, maxDays - 1);

            if (toDate.value && (toDate.value < fromDate.value || toDate.value > toDate.max)) {
                toDate.value = "";
            }
        }
        updateSummary();
    });

    toDate.addEventListener("change", updateSummary);
    updateSummary();

    function updateSummary() {
        if (!fromDate.value || !toDate.value) {
            totalDays.textContent = "0";
            totalRent.textContent = "Rs. 0.00";
            depositDisplay.textContent = `Rs. ${deposit.toFixed(2)}`;
            return;
        }

        const start = new Date(fromDate.value);
        const end = new Date(toDate.value);
        const dayDiff = Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;

        if (dayDiff <= 0) {
            totalDays.textContent = "0";
            totalRent.textContent = "Rs. 0.00";
            return;
        }

        if (dayDiff > maxDays) {
            alert(`Maximum rental period is ${maxDays} days. Please pick a shorter range.`);
            toDate.value = "";
            totalDays.textContent = "0";
            totalRent.textContent = "Rs. 0.00";
            return;
        }

        totalDays.textContent = String(dayDiff);
        totalRent.textContent = `Rs. ${(dayDiff * rentPerDay).toFixed(2)}`;
        depositDisplay.textContent = `Rs. ${deposit.toFixed(2)}`;
    }
}

function setupScrollReveal() {
    const targets = document.querySelectorAll(
        ".page-intro, .panel, .stat-card, .equipment-card, .simple-card, .mini-card, .table-wrap, .lp-hero__text, .lp-hero__visual, .lp-feature, .lp-role, .lp-step, .lp-cta, .login-aside, .login-panel"
    );

    if (!targets.length) {
        return;
    }

    targets.forEach((element, index) => {
        element.classList.add("reveal-ready");
        element.style.transitionDelay = `${Math.min(index * 50, 240)}ms`;
    });

    if (!("IntersectionObserver" in window)) {
        targets.forEach((element) => element.classList.add("is-visible"));
        return;
    }

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.12,
            rootMargin: "0px 0px -48px 0px",
        }
    );

    targets.forEach((element) => observer.observe(element));
}

function setupLandingMotion() {
    const stage = document.querySelector(".lp-visual-stage");
    if (!stage) {
        return;
    }

    stage.addEventListener("pointermove", (event) => {
        const rect = stage.getBoundingClientRect();
        const offsetX = (event.clientX - rect.left) / rect.width - 0.5;
        const offsetY = (event.clientY - rect.top) / rect.height - 0.5;
        stage.style.setProperty("--tilt-x", `${offsetX * 8}deg`);
        stage.style.setProperty("--tilt-y", `${offsetY * -8}deg`);
    });

    stage.addEventListener("pointerleave", () => {
        stage.style.setProperty("--tilt-x", "0deg");
        stage.style.setProperty("--tilt-y", "0deg");
    });
}

function selectPayment(method) {
    const paymentInput = document.getElementById("payment_method");
    const upiCard = document.getElementById("pay-upi");
    const cardCard = document.getElementById("pay-card");
    const upiDetails = document.getElementById("upi-details");
    const cardDetails = document.getElementById("card-details");

    if (!paymentInput || !upiCard || !cardCard || !upiDetails || !cardDetails) {
        return;
    }

    paymentInput.value = method;
    upiCard.classList.toggle("is-active", method === "UPI");
    cardCard.classList.toggle("is-active", method === "Card");
    upiDetails.hidden = method !== "UPI";
    cardDetails.hidden = method !== "Card";
}

function confirmReturn(rentalId) {
    if (confirm("Submit this equipment for QC return?")) {
        document.getElementById(`returnForm${rentalId}`).submit();
    }
}
