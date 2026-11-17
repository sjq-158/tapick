document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-open]").forEach((button) => {
        button.addEventListener("click", () => document.getElementById(button.dataset.open).showModal());
    });

    document.querySelectorAll("dialog.modal").forEach((dialog) => {
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog || event.target.closest("[data-close]")) dialog.close();
        });
    });

    const adjust = document.getElementById("adjustDialog");
    document.querySelectorAll("[data-adjust]").forEach((button) => {
        button.addEventListener("click", () => {
            const form = adjust.querySelector("form");
            form.action = button.dataset.url;
            form.reset();
            document.getElementById("adjustName").textContent =
                button.dataset.name + (button.dataset.branch ? " \u00b7 " + button.dataset.branch : "");
            document.getElementById("adjustOnHand").textContent = button.dataset.qty + " " + button.dataset.unit;
            document.getElementById("adjust_threshold").value = button.dataset.threshold;
            adjust.showModal();
            document.getElementById("adjust_amount").focus();
        });
    });
});