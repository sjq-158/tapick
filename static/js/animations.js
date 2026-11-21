/**
 * Anime.js Global Motion & Screen Transition Engine for Tapick
 * Powered by Anime.js (https://animejs.com/)
 * Orchestrates screen transitions, kinetic typography, counter animations,
 * and tactile button micro-interactions across all screens.
 */
document.addEventListener("DOMContentLoaded", () => {
    // Respect accessibility settings
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    // Check if anime.js is loaded
    if (typeof anime === "undefined") {
        console.warn("Anime.js not loaded. Falling back to native CSS transitions.");
        return;
    }

    // Do not interfere with landing page's dedicated animation & positioning system
    if (document.getElementById("bgGradient") || document.querySelector(".topbar")) {
        return;
    }

    // ── 1. Screen & Page Transition Animations ─────────────────────────────────
    // Animate Header & Navigation
    anime({
        targets: ".app-header",
        translateY: [-14, 0],
        opacity: [0, 1],
        duration: 750,
        easing: "easeOutCubic",
    });

    // Animate Kickers and Status Pills
    anime({
        targets: ".kicker, .hero-kicker, .live-pill, .brand-logo",
        scale: [0.85, 1],
        opacity: [0, 1],
        duration: 650,
        delay: 80,
        easing: "easeOutBack",
    });

    // ── 2. Kinetic Typography / Text Animations ───────────────────────────────
    // Animate Main Page Headings with smooth upward slide & reveal
    const headings = document.querySelectorAll(".page-head h1, .auth-head h1, .hero h1, .section-head h2");
    if (headings.length > 0) {
        anime({
            targets: headings,
            translateY: [20, 0],
            opacity: [0, 1],
            duration: 850,
            delay: 120,
            easing: "easeOutExpo",
        });
    }

    // Animate Subtitles / Descriptions
    anime({
        targets: ".page-head p.muted, .auth-head p.muted, .hero p, .section-head p.muted",
        translateY: [12, 0],
        opacity: [0, 1],
        duration: 800,
        delay: 200,
        easing: "easeOutCubic",
    });

    // ── 3. Content Cards & Staggered Section Cascade ──────────────────────────
    const cardTargets = document.querySelectorAll(
        ".page > section, .page > .card, .page > .grid-main > *, .page > .grid-aside > *, .stat-grid > article, .auth-card, .feature-card, .table-wrap"
    );
    if (cardTargets.length > 0) {
        anime({
            targets: cardTargets,
            translateY: [24, 0],
            opacity: [0, 1],
            duration: 850,
            delay: anime.stagger(90, { start: 220 }),
            easing: "easeOutCubic",
        });
    }

    // ── 4. Numeric Stat Counter Animation ─────────────────────────────────────
    document.querySelectorAll(".stat-value, .locator-stock-count strong").forEach((el) => {
        const rawText = el.textContent.trim().replace(/,/g, "");
        const num = parseFloat(rawText);
        if (!isNaN(num) && num > 0) {
            const hasDecimals = rawText.includes(".");
            const obj = { value: 0 };
            anime({
                targets: obj,
                value: num,
                round: hasDecimals ? 100 : 1,
                duration: 1200,
                delay: 350,
                easing: "easeOutExpo",
                update: () => {
                    el.textContent = hasDecimals ? obj.value.toFixed(2) : Math.round(obj.value);
                },
            });
        }
    });

    // ── 5. Tactile Button Elastic Micro-Interactions ──────────────────────────
    document.querySelectorAll(".btn, .icon-btn, .user-chip, .nav-link, .theme-toggle-btn").forEach((btn) => {
        btn.addEventListener("mousedown", () => {
            anime({
                targets: btn,
                scale: 0.94,
                duration: 150,
                easing: "easeOutQuad",
            });
        });

        const resetBtn = () => {
            anime({
                targets: btn,
                scale: 1,
                duration: 380,
                easing: "easeOutElastic(1, .5)",
            });
        };
        btn.addEventListener("mouseup", resetBtn);
        btn.addEventListener("mouseleave", resetBtn);
    });

    // ── 6. Modal Dialog Spring Pop Entrance ───────────────────────────────────
    const originalShowModal = HTMLDialogElement.prototype.showModal;
    HTMLDialogElement.prototype.showModal = function () {
        originalShowModal.apply(this, arguments);
        const modalContent = this.querySelector(".modal-card") || this;
        anime({
            targets: modalContent,
            scale: [0.92, 1],
            opacity: [0, 1],
            translateY: [16, 0],
            duration: 420,
            easing: "easeOutBack",
        });
    };

    // ── 7. Smooth Outgoing Screen Transition ──────────────────────────────────
    document.querySelectorAll("a[href]").forEach((link) => {
        const href = link.getAttribute("href");
        // Only target internal full-page navigation links (exclude hashes, downloads, external, mailto, tel, javascript)
        if (
            href &&
            !href.startsWith("#") &&
            !href.startsWith("javascript:") &&
            !href.startsWith("tel:") &&
            !href.startsWith("mailto:") &&
            !link.hasAttribute("download") &&
            link.getAttribute("target") !== "_blank" &&
            !link.hasAttribute("data-open") &&
            !link.hasAttribute("data-close") &&
            !link.classList.contains("theme-fab")
        ) {
            link.addEventListener("click", (e) => {
                // If special modifier key (Ctrl, Cmd, Shift, Alt), allow default browser tab behavior
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                const pageEl = document.querySelector(".page, .landing-page, .auth-shell");
                if (pageEl) {
                    e.preventDefault();
                    anime({
                        targets: pageEl,
                        opacity: [1, 0.3],
                        translateY: [0, -10],
                        duration: 220,
                        easing: "easeInQuad",
                        complete: () => {
                            window.location.href = href;
                        },
                    });
                }
            });
        }
    });
});
