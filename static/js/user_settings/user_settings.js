document.addEventListener("DOMContentLoaded", () => {
    const darkBox = document.getElementById("dark_mode");
    if (!darkBox) return;

    darkBox.addEventListener("change", () => {
        const theme = darkBox.checked ? "dark" : "light";
        document.documentElement.setAttribute("data-theme", theme);
        try { localStorage.setItem("tapick-theme", theme); } catch (e) {}
    });

    window.addEventListener("themechange", (event) => {
        darkBox.checked = event.detail === "dark";
    });
});