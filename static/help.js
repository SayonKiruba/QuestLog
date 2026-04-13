document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("help-modal");
    const openBtn = document.getElementById("help-open");
    const closeBtn = document.getElementById("help-close");
    if (!modal || !openBtn) return;

    function open() {
        modal.classList.remove("hidden");
        openBtn.setAttribute("aria-expanded", "true");
    }

    function close() {
        modal.classList.add("hidden");
        openBtn.setAttribute("aria-expanded", "false");
    }

    openBtn.addEventListener("click", open);
    if (closeBtn) closeBtn.addEventListener("click", close);

    modal.addEventListener("click", (e) => {
        if (e.target === modal) close();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !modal.classList.contains("hidden")) close();
    });
});
