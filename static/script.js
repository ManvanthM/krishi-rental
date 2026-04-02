document.addEventListener("DOMContentLoaded", () => {
    setupValidation();
    setupRentalCalculator();
});

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

            // Validate payment method is selected on rental form
            const paymentInput = form.querySelector('input[name="payment_method"]');
            if (paymentInput && paymentInput.type === "hidden" && !paymentInput.value) {
                event.preventDefault();
                alert("Please select a payment method (UPI or Card).");
                return;
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

    // Helper: add days to a date string (YYYY-MM-DD) and return YYYY-MM-DD
    function addDays(dateStr, days) {
        const d = new Date(dateStr);
        d.setDate(d.getDate() + days);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, "0");
        const dd = String(d.getDate()).padStart(2, "0");
        return `${yyyy}-${mm}-${dd}`;
    }

    // When from_date changes, constrain to_date
    fromDate.addEventListener("change", () => {
        if (fromDate.value) {
            // to_date must be >= from_date and <= from_date + (maxDays - 1)
            toDate.min = fromDate.value;
            toDate.max = addDays(fromDate.value, maxDays - 1);

            // Clear to_date if it's now out of range
            if (toDate.value && (toDate.value < fromDate.value || toDate.value > toDate.max)) {
                toDate.value = "";
            }
        }
        updateSummary();
    });

    toDate.addEventListener("change", updateSummary);

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

function selectPayment(method) {
    // Set hidden input value
    document.getElementById("payment_method").value = method;

    // Highlight selected card
    const upiCard = document.getElementById("pay-upi");
    const cardCard = document.getElementById("pay-card");
    const upiDetails = document.getElementById("upi-details");
    const cardDetails = document.getElementById("card-details");

    if (method === "UPI") {
        upiCard.style.borderColor = "#2e7d32";
        upiCard.style.background = "#e8f5e9";
        cardCard.style.borderColor = "";
        cardCard.style.background = "";
        upiDetails.style.display = "block";
        cardDetails.style.display = "none";
    } else {
        cardCard.style.borderColor = "#2e7d32";
        cardCard.style.background = "#e8f5e9";
        upiCard.style.borderColor = "";
        upiCard.style.background = "";
        cardDetails.style.display = "block";
        upiDetails.style.display = "none";
    }
}

function confirmReturn(rentalId) {
    if (confirm("Submit this equipment for QC return?")) {
        document.getElementById("returnForm" + rentalId).submit();
    }
}
