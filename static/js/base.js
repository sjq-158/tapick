(function () {
    var theme = null;
    try {
        theme = localStorage.getItem("tapick-theme");
    } catch (e) {}
    if (!theme) {
        theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    document.documentElement.setAttribute("data-theme", theme);
})();

(function () {
    var root = document.documentElement;
    var btn = document.getElementById("themeToggle");

    if (btn) {
        btn.addEventListener("click", function () {
            var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
            root.setAttribute("data-theme", next);
            try { localStorage.setItem("tapick-theme", next); } catch (e) {}
            window.dispatchEvent(new CustomEvent("themechange", { detail: next }));
            if (btn.dataset.url) {
                fetch(btn.dataset.url, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "X-CSRFToken": btn.dataset.csrf, "Content-Type": "application/x-www-form-urlencoded" },
                    body: "theme=" + next
                });
            }
        });
    }

    document.addEventListener("click", function (e) {
        var toggle = e.target.closest(".toggle-password");
        if (!toggle) return;
        var wrapper = toggle.closest(".auth-input-wrapper, .input-wrapper");
        var input = wrapper ? wrapper.querySelector("input") : (toggle.dataset.target ? document.getElementById(toggle.dataset.target) : null);
        if (!input) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        toggle.classList.toggle("is-on", show);
        toggle.classList.toggle("is-visible", show);
        toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });

    var stack = document.getElementById("toastStack");
    if (stack) {
        setTimeout(function () { stack.classList.add("is-hiding"); }, 4500);
    }
})();
