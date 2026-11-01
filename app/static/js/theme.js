function updateThemeLabel() {
    var button = document.getElementById("theme-toggle");
    if (button) {
        button.textContent = document.documentElement.dataset.theme === "light" ? "🌙 Dark" : "☀️ Light";
    }
}

function toggleTheme() {
    var next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    try {
        localStorage.setItem("theme", next);
    } catch (e) {}
    updateThemeLabel();
}

updateThemeLabel();