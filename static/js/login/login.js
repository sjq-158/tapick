document.addEventListener("DOMContentLoaded", () => {
    // ── Toggle Password Visibility ─────────────────────────────────────────
    document.querySelectorAll(".toggle-password").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            // Look for sibling input within wrapper first to avoid duplicate ID issues
            const wrapper = btn.closest(".auth-input-wrapper, .input-wrapper");
            const targetId = btn.getAttribute("data-target");
            const input = wrapper ? wrapper.querySelector("input") : (targetId ? document.getElementById(targetId) : null);

            if (input) {
                const isPassword = input.type === "password";
                input.type = isPassword ? "text" : "password";
                btn.classList.toggle("is-visible", isPassword);
                btn.classList.toggle("is-on", isPassword);
                btn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");
            }
        });
    });

    // ── Auth Slider (Switch between Login and Register) ───────────────────
    const card = document.getElementById("authSliderCard");
    const topbarSignIn = document.getElementById("topbarSignIn");
    const topbarGetStarted = document.getElementById("topbarGetStarted");

    function setAuthMode(mode, pushState = true) {
        if (!card) return;

        if (mode === "register") {
            card.classList.remove("mode-login");
            card.classList.add("mode-register");
            document.title = "Register — Tapick";
            if (topbarSignIn) topbarSignIn.classList.remove("active");
            if (topbarGetStarted) topbarGetStarted.classList.add("active");
            if (pushState) {
                history.pushState({ mode: "register" }, "", "/register/");
            }
        } else {
            card.classList.remove("mode-register");
            card.classList.add("mode-login");
            document.title = "Sign In — Tapick";
            if (topbarSignIn) topbarSignIn.classList.add("active");
            if (topbarGetStarted) topbarGetStarted.classList.remove("active");
            if (pushState) {
                history.pushState({ mode: "login" }, "", "/login/");
            }
        }

        if (typeof anime !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            const targetSelector = mode === "register" ? "#registerFormPane .auth-form-inner > *" : "#loginFormPane .auth-form-inner > *";
            anime({
                targets: targetSelector,
                opacity: [0, 1],
                translateY: [16, 0],
                delay: anime.stagger(40, { start: 220 }),
                duration: 650,
                easing: "easeOutCubic"
            });
        }
    }

    document.getElementById("switchRegisterBtn")?.addEventListener("click", () => setAuthMode("register"));
    document.getElementById("overlayBtnRegister")?.addEventListener("click", () => setAuthMode("register"));
    document.getElementById("switchLoginBtn")?.addEventListener("click", () => setAuthMode("login"));
    document.getElementById("overlayBtnLogin")?.addEventListener("click", () => setAuthMode("login"));

    topbarSignIn?.addEventListener("click", (e) => {
        e.preventDefault();
        setAuthMode("login");
    });

    topbarGetStarted?.addEventListener("click", (e) => {
        e.preventDefault();
        setAuthMode("register");
    });

    window.addEventListener("popstate", (e) => {
        if (e.state && e.state.mode) {
            setAuthMode(e.state.mode, false);
        } else if (window.location.pathname.includes("register")) {
            setAuthMode("register", false);
        } else {
            setAuthMode("login", false);
        }
    });

    if (typeof anime !== "undefined" && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        anime({
            targets: "#authSliderCard",
            opacity: [0, 1],
            translateY: [24, 0],
            scale: [0.97, 1],
            duration: 800,
            easing: "easeOutCubic"
        });
        anime({
            targets: ".auth-avatar-badge",
            scale: [0.6, 1],
            opacity: [0, 1],
            duration: 650,
            delay: 150,
            easing: "easeOutBack"
        });
    }
});
