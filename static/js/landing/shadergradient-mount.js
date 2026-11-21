/**
 * Shared ShaderGradient (React-based) mount script.
 * Used by landing, login, and register pages.
 * Mounts the @shadergradient/react waterPlane onto #bgGradient.
 */
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
