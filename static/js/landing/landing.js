const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const topbar = document.getElementById("topbar");
const progress = document.getElementById("scrollProgress");
const deviceWrap = document.getElementById("deviceWrap");
const device = document.getElementById("device");
let ticking = false;

function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => {
        const y = window.scrollY;
        const max = document.documentElement.scrollHeight - window.innerHeight;
        topbar.classList.toggle("is-scrolled", y > 20);
        progress.style.transform = `scaleX(${max > 0 ? y / max : 0})`;

        if (deviceWrap && !reduceMotion) {
            const top = deviceWrap.getBoundingClientRect().top;
            const p = Math.min(1, Math.max(0, (window.innerHeight - top) / (window.innerHeight * 0.75)));
            device.style.setProperty("--p", p.toFixed(3));
        }
        ticking = false;
    });
}
window.addEventListener("scroll", onScroll, { passive: true });
window.addEventListener("resize", onScroll);
onScroll();

document.querySelectorAll("[data-stagger]").forEach((parent) => {
    [...parent.children].forEach((child, i) => child.style.setProperty("--i", i));
});

const revealTargets = document.querySelectorAll("[data-reveal], .bars, .steps");
const counters = document.querySelectorAll("[data-count]");

function countUp(el) {
    const end = Number(el.dataset.count);
    const prefix = el.dataset.prefix || "";
    const suffix = el.dataset.suffix || "";
    const start = performance.now();
    const duration = 1400;
    (function tick(now) {
        const k = Math.min(1, (now - start) / duration);
        const eased = 1 - Math.pow(1 - k, 3);
        el.innerHTML = prefix + Math.round(end * eased) + suffix;
        if (k < 1) requestAnimationFrame(tick);
    })(start);
}

if (reduceMotion || !("IntersectionObserver" in window)) {
    revealTargets.forEach((el) => el.classList.add("in"));
    counters.forEach((el) => { el.innerHTML = (el.dataset.prefix || "") + el.dataset.count + (el.dataset.suffix || ""); });
} else {
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("in");
                revealObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.15, rootMargin: "0px 0px -8% 0px" });
    revealTargets.forEach((el) => revealObserver.observe(el));

    const counterObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                countUp(entry.target);
                counterObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.6 });
    counters.forEach((el) => counterObserver.observe(el));
}

const navLinks = [...document.querySelectorAll(".topnav a")];
if ("IntersectionObserver" in window) {
    const sectionObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                navLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === "#" + entry.target.id));
            }
        });
    }, { rootMargin: "-45% 0px -50% 0px" });
    document.querySelectorAll("main section[id]").forEach((section) => sectionObserver.observe(section));
}

const featureTrack = document.getElementById("featureTrack");
if (featureTrack) {
    const prevBtn = document.querySelector(".slider-btn--prev");
    const nextBtn = document.querySelector(".slider-btn--next");

    const cardStep = () => {
        const card = featureTrack.querySelector(".feature");
        return card ? card.offsetWidth + 20 : 300;
    };
    const updateArrows = () => {
        prevBtn.disabled = featureTrack.scrollLeft <= 4;
        nextBtn.disabled = featureTrack.scrollLeft >= featureTrack.scrollWidth - featureTrack.clientWidth - 4;
    };

    prevBtn.addEventListener("click", () => featureTrack.scrollBy({ left: -cardStep(), behavior: "smooth" }));
    nextBtn.addEventListener("click", () => featureTrack.scrollBy({ left: cardStep(), behavior: "smooth" }));
    featureTrack.addEventListener("scroll", updateArrows, { passive: true });
    featureTrack.addEventListener("keydown", (e) => {
        if (e.key === "ArrowRight") featureTrack.scrollBy({ left: cardStep(), behavior: "smooth" });
        if (e.key === "ArrowLeft") featureTrack.scrollBy({ left: -cardStep(), behavior: "smooth" });
    });
    window.addEventListener("resize", updateArrows);
    updateArrows();
}

const PALETTES = {
    light: { color1: "#7DE2D1", color2: "#BEEEE6", color3: "#FFFAFB", brightness: 1.1 },
    dark: { color1: "#339989", color2: "#2B2C28", color3: "#131515", brightness: 1.0 },
};

async function mountShaderGradient() {
    const host = document.getElementById("bgGradient");
    if (!host) return;

    try {
        const [React, { createRoot }, { ShaderGradientCanvas, ShaderGradient }] = await Promise.all([
            import("react"),
            import("react-dom/client"),
            import("@shadergradient/react"),
        ]);
        const h = React.createElement;
        const root = createRoot(host);

        const draw = () => {
            const theme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
            root.render(
                h(
                    ShaderGradientCanvas,
                    {
                        key: theme,
                        style: { position: "absolute", top: 0, left: 0, width: "100%", height: "100%" },
                        pixelDensity: 1,
                        fov: 45,
                        pointerEvents: "none",
                        lazyLoad: false,
                    },
                    h(ShaderGradient, {
                        control: "props",
                        type: "waterPlane",
                        animate: reduceMotion ? "off" : "on",
                        uTime: 0,
                        uSpeed: 0.2,
                        uStrength: 3.4,
                        uDensity: 1.2,
                        uFrequency: 0,
                        uAmplitude: 0,
                        positionX: 0,
                        positionY: 0.9,
                        positionZ: -0.3,
                        rotationX: 45,
                        rotationY: 0,
                        rotationZ: 0,
                        reflection: 0.1,
                        cAzimuthAngle: 170,
                        cPolarAngle: 70,
                        cDistance: 4.4,
                        cameraZoom: 1,
                        lightType: "3d",
                        envPreset: "city",
                        grain: "off",
                        wireframe: false,
                        ...PALETTES[theme],
                    })
                )
            );
        };

        draw();
        window.addEventListener("themechange", draw);
    } catch (err) {
        console.warn("ShaderGradient could not load, using the CSS fallback.", err);
    }
}
mountShaderGradient();