/**
 * ShaderGradient Background Engine for Tapick
 * Based on the mathematical formulation of ruucm/shadergradient:
 * Dynamic multi-wave simplex 3D WebGL shader mesh with organic fluid dynamics.
 * Automatically synchronizes with Tapick's Light / Dark theme palette and mouse movements.
 */
(function () {
    const canvas = document.getElementById("shaderGradientCanvas");
    if (!canvas) return;

    let gl = null;
    try {
        gl = canvas.getContext("webgl", { alpha: true, antialias: true, depth: false, powerPreference: "low-power" })
             || canvas.getContext("experimental-webgl");
    } catch (e) {
        gl = null;
    }

    // Palette Colors matching Tapick branding
    const PALETTES = {
        light: {
            c1: [0.133, 0.435, 0.416], // #226f6a (Deep Teal)
            c2: [0.200, 0.600, 0.537], // #339989 (Emerald Aqua)
            c3: [0.651, 0.906, 0.820], // #A6E7D1 (Soft Mint)
            c4: [0.985, 0.992, 0.988], // #FBFCFA (Luminous Pearl)
            grain: 0.04,
            speed: 0.28,
            intensity: 0.48,
        },
        dark: {
            c1: [0.039, 0.129, 0.118], // Deep Midnight Pine
            c2: [0.082, 0.298, 0.267], // #154c44 (Bioluminescent Teal)
            c3: [0.169, 0.490, 0.447], // #2b7d72 (Emerald Cyan)
            c4: [0.075, 0.082, 0.082], // #131515 (Charcoal Base)
            grain: 0.06,
            speed: 0.22,
            intensity: 0.65,
        }
    };

    // Current interpolated colors for smooth theme transitions
    let currentTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
    let targetPalette = PALETTES[currentTheme];
    let curC1 = [...targetPalette.c1];
    let curC2 = [...targetPalette.c2];
    let curC3 = [...targetPalette.c3];
    let curC4 = [...targetPalette.c4];
    let curIntensity = targetPalette.intensity;

    window.addEventListener("themechange", (e) => {
        const theme = e.detail === "dark" ? "dark" : "light";
        targetPalette = PALETTES[theme];
    });

    // Observer for direct attribute changes on <html>
    const themeObserver = new MutationObserver(() => {
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        targetPalette = isDark ? PALETTES.dark : PALETTES.light;
    });
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

    // Smooth lerp helper
    function lerp(start, end, factor) {
        return start + (end - start) * factor;
    }
    function lerpColor(c, target, factor) {
        c[0] = lerp(c[0], target[0], factor);
        c[1] = lerp(c[1], target[1], factor);
        c[2] = lerp(c[2], target[2], factor);
    }

    if (!gl) {
        // Fallback: 2D Canvas gradient mesh animation
        run2DFallback(canvas);
        return;
    }

    // ── WebGL Shader Sources ──────────────────────────────────────────────────
    const vertSource = `
        attribute vec2 a_position;
        varying vec2 v_uv;
        void main() {
            v_uv = (a_position + 1.0) * 0.5;
            gl_Position = vec4(a_position, 0.0, 1.0);
        }
    `;

    const fragSource = `
        precision highp float;
        varying vec2 v_uv;

        uniform vec2 u_resolution;
        uniform vec2 u_mouse;
        uniform float u_time;
        uniform vec3 u_c1;
        uniform vec3 u_c2;
        uniform vec3 u_c3;
        uniform vec3 u_c4;
        uniform float u_intensity;
        uniform float u_grain;

        // 3D Simplex-style noise approximation
        vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec2 mod289(vec2 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
        vec3 permute(vec3 x) { return mod289(((x * 34.0) + 1.0) * x); }

        float snoise(vec2 v) {
            const vec4 C = vec4(0.211324865405187,  // (3.0-sqrt(3.0))/6.0
                                0.366025403784439,  // 0.5*(sqrt(3.0)-1.0)
                               -0.577350269189626,  // -1.0 + 2.0 * C.x
                                0.024390243902439); // 1.0 / 41.0
            vec2 i  = floor(v + dot(v, C.yy));
            vec2 x0 = v -   i + dot(i, C.xx);
            vec2 i1 = (x0.x > x0.y) ? vec2(1.0, 0.0) : vec2(0.0, 1.0);
            vec4 x12 = x0.xyxy + C.xxzz;
            x12.xy -= i1;
            i = mod289(i);
            vec3 p = permute(permute(i.y + vec3(0.0, i1.y, 1.0)) + i.x + vec3(0.0, i1.x, 1.0));
            vec3 m = max(0.5 - vec3(dot(x0, x0), dot(x12.xy, x12.xy), dot(x12.zw, x12.zw)), 0.0);
            m = m * m;
            m = m * m;
            vec3 x = 2.0 * fract(p * C.www) - 1.0;
            vec3 h = abs(x) - 0.5;
            vec3 ox = floor(x + 0.5);
            vec3 a0 = x - ox;
            m *= 1.79284291400159 - 0.85373472095314 * (a0 * a0 + h * h);
            vec3 g;
            g.x  = a0.x  * x0.x  + h.x  * x0.y;
            g.yz = a0.yz * x12.xz + h.yz * x12.yw;
            return 130.0 * dot(m, g);
        }

        // Domain warping function inspired by Inigo Quilez & ShaderGradient
        float fbm(vec2 p) {
            float v = 0.0;
            float a = 0.5;
            vec2 shift = vec2(100.0);
            mat2 rot = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.50));
            for (int i = 0; i < 3; ++i) {
                v += a * snoise(p);
                p = rot * p * 2.0 + shift;
                a *= 0.5;
            }
            return v;
        }

        // Subtle film grain
        float rand(vec2 co) {
            return fract(sin(dot(co.xy, vec2(12.9898, 78.233))) * 43758.5453);
        }

        void main() {
            vec2 uv = gl_FragCoord.xy / u_resolution.xy;
            float aspect = u_resolution.x / u_resolution.y;
            vec2 p = (uv - 0.5) * vec2(aspect, 1.0);

            // Subtle mouse parallax
            vec2 mouseOffset = (u_mouse - 0.5) * 0.18;
            p += mouseOffset * 0.25;

            float t = u_time * 0.18;

            // Multi-layered organic wave distortion
            vec2 q = vec2(fbm(p + vec2(0.0, 0.0) + t * 0.4),
                          fbm(p + vec2(5.2, 1.3) + t * 0.3));

            vec2 r = vec2(fbm(p + 3.0 * q + vec2(1.7, 9.2) + t * 0.25),
                          fbm(p + 3.0 * q + vec2(8.3, 2.8) + t * 0.35));

            float f = fbm(p + 3.5 * r + t * 0.15);

            // Multi-stop color mesh blend
            vec3 col = mix(u_c4, u_c1, clamp(f * f * 3.5, 0.0, 1.0));
            col = mix(col, u_c2, clamp(length(q) * 0.9, 0.0, 1.0));
            col = mix(col, u_c3, clamp(length(r.x) * 1.2, 0.0, 1.0));

            // Soft radial ambient vignette
            float dist = length(uv - 0.5);
            col *= 1.0 - dist * 0.25;

            // Micro-grain texture
            float grain = (rand(uv + fract(u_time)) - 0.5) * u_grain;
            col += grain;

            gl_FragColor = vec4(col, u_intensity);
        }
    `;

    // Shader Compiler Helper
    function createShader(gl, type, source) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            gl.deleteShader(shader);
            return null;
        }
        return shader;
    }

    const vertShader = createShader(gl, gl.VERTEX_SHADER, vertSource);
    const fragShader = createShader(gl, gl.FRAGMENT_SHADER, fragSource);
    if (!vertShader || !fragShader) {
        run2DFallback(canvas);
        return;
    }

    const program = gl.createProgram();
    gl.attachShader(program, vertShader);
    gl.attachShader(program, fragShader);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        run2DFallback(canvas);
        return;
    }

    // Geometry: Fullscreen Quad
    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
        -1.0, -1.0,
         1.0, -1.0,
        -1.0,  1.0,
        -1.0,  1.0,
         1.0, -1.0,
         1.0,  1.0,
    ]), gl.STATIC_DRAW);

    const positionLocation = gl.getAttribLocation(program, "a_position");
    const uResolution = gl.getUniformLocation(program, "u_resolution");
    const uMouse = gl.getUniformLocation(program, "u_mouse");
    const uTime = gl.getUniformLocation(program, "u_time");
    const uC1 = gl.getUniformLocation(program, "u_c1");
    const uC2 = gl.getUniformLocation(program, "u_c2");
    const uC3 = gl.getUniformLocation(program, "u_c3");
    const uC4 = gl.getUniformLocation(program, "u_c4");
    const uIntensity = gl.getUniformLocation(program, "u_intensity");
    const uGrain = gl.getUniformLocation(program, "u_grain");

    // Mouse tracking with smooth spring damping
    let targetMouseX = 0.5, targetMouseY = 0.5;
    let curMouseX = 0.5, curMouseY = 0.5;

    window.addEventListener("pointermove", (e) => {
        targetMouseX = e.clientX / window.innerWidth;
        targetMouseY = 1.0 - (e.clientY / window.innerHeight);
    }, { passive: true });

    // Handle Window Resize (clamped pixel ratio for max performance)
    function resize() {
        const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        const w = Math.floor(window.innerWidth * dpr);
        const h = Math.floor(window.innerHeight * dpr);
        if (canvas.width !== w || canvas.height !== h) {
            canvas.width = w;
            canvas.height = h;
            gl.viewport(0, 0, w, h);
        }
    }
    window.addEventListener("resize", resize, { passive: true });
    resize();

    // Main WebGL Render Loop
    let startTime = performance.now();
    let animFrame = null;

    function render(now) {
        if (!document.hidden) {
            const time = (now - startTime) * 0.001 * targetPalette.speed;

            // Interpolate colors towards current target palette (light/dark transition)
            lerpColor(curC1, targetPalette.c1, 0.05);
            lerpColor(curC2, targetPalette.c2, 0.05);
            lerpColor(curC3, targetPalette.c3, 0.05);
            lerpColor(curC4, targetPalette.c4, 0.05);
            curIntensity = lerp(curIntensity, targetPalette.intensity, 0.05);

            curMouseX = lerp(curMouseX, targetMouseX, 0.04);
            curMouseY = lerp(curMouseY, targetMouseY, 0.04);

            gl.useProgram(program);

            gl.enableVertexAttribArray(positionLocation);
            gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
            gl.vertexAttribPointer(positionLocation, 2, gl.FLOAT, false, 0, 0);

            gl.uniform2f(uResolution, canvas.width, canvas.height);
            gl.uniform2f(uMouse, curMouseX, curMouseY);
            gl.uniform1f(uTime, time);
            gl.uniform3fv(uC1, curC1);
            gl.uniform3fv(uC2, curC2);
            gl.uniform3fv(uC3, curC3);
            gl.uniform3fv(uC4, curC4);
            gl.uniform1f(uIntensity, curIntensity);
            gl.uniform1f(uGrain, targetPalette.grain);

            gl.drawArrays(gl.TRIANGLES, 0, 6);
        }
        animFrame = requestAnimationFrame(render);
    }

    animFrame = requestAnimationFrame(render);

    document.addEventListener("visibilitychange", () => {
        if (!document.hidden && !animFrame) {
            startTime = performance.now();
            animFrame = requestAnimationFrame(render);
        }
    });

    // ── 2D Canvas Fallback ────────────────────────────────────────────────────
    function run2DFallback(canvasEl) {
        const ctx = canvasEl.getContext("2d");
        if (!ctx) return;

        function draw2D(t) {
            if (document.hidden) return requestAnimationFrame(draw2D);
            const w = canvasEl.width = window.innerWidth;
            const h = canvasEl.height = window.innerHeight;
            const isDark = document.documentElement.getAttribute("data-theme") === "dark";

            const grad = ctx.createRadialGradient(
                w * (0.5 + Math.sin(t * 0.0005) * 0.25),
                h * (0.4 + Math.cos(t * 0.0004) * 0.25),
                w * 0.1,
                w * 0.5,
                h * 0.5,
                w * 0.9
            );

            if (isDark) {
                grad.addColorStop(0, "rgba(51, 153, 137, 0.35)");
                grad.addColorStop(0.5, "rgba(34, 111, 106, 0.25)");
                grad.addColorStop(1, "rgba(19, 21, 21, 0.95)");
            } else {
                grad.addColorStop(0, "rgba(166, 231, 209, 0.45)");
                grad.addColorStop(0.5, "rgba(51, 153, 137, 0.25)");
                grad.addColorStop(1, "rgba(255, 250, 251, 0.9)");
            }

            ctx.fillStyle = grad;
            ctx.fillRect(0, 0, w, h);
            requestAnimationFrame(draw2D);
        }
        requestAnimationFrame(draw2D);
    }
})();
