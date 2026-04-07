let adminGames = [];
let editingAdminGameId = null;

function adminEscapeHtml(text) {
    if (text == null) return "";
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function resetAdminForm() {
    editingAdminGameId = null;
    document.getElementById("admin-form-title").innerText = "Add game";
    document.getElementById("admin-name").value = "";
    document.getElementById("admin-image").value = "";
    document.getElementById("admin-summary").value = "";
    document.getElementById("admin-igdb-id").value = "";
    document.getElementById("admin-blacklisted").checked = false;
}

function fillAdminForm(game) {
    editingAdminGameId = game.id;
    document.getElementById("admin-form-title").innerText = "Edit game";
    document.getElementById("admin-name").value = game.name || "";
    document.getElementById("admin-image").value = game.image || "";
    document.getElementById("admin-summary").value = game.summary || "";
    document.getElementById("admin-igdb-id").value = game.igdb_id || "";
    document.getElementById("admin-blacklisted").checked = !!game.is_blacklisted;
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderAdminGames() {
    const container = document.getElementById("admin-games");
    const count = document.getElementById("admin-count");
    if (!container || !count) return;

    container.innerHTML = "";
    count.innerText =
        adminGames.length === 0 ? "No managed games yet" : `${adminGames.length} managed games`;

    adminGames.forEach((game) => {
        const card = document.createElement("article");
        card.className = "game-card";
        card.setAttribute("role", "listitem");
        const image =
            game.image || "https://dummyimage.com/600x800/1a1d28/8b92a8&text=No+cover";
        card.innerHTML = `
            <div class="game-card-media">
                <img src="${adminEscapeHtml(image)}" class="game-cover" alt="${adminEscapeHtml(game.name)}">
            </div>
            <div class="game-info">
                <strong>${adminEscapeHtml(game.name)}</strong>
                <div class="game-meta">${game.is_blacklisted ? "Blacklisted" : "Visible"}</div>
                <p class="text-muted">${adminEscapeHtml(game.summary || "No summary")}</p>
                <div class="modal-actions">
                    <button type="button" class="btn btn-primary btn-sm admin-edit">Edit</button>
                    <button type="button" class="btn btn-danger btn-sm admin-delete">Delete</button>
                    ${!game.is_blacklisted ? '<button type="button" class="btn btn-ghost btn-sm admin-blacklist">Blacklist</button>' : ""}
                </div>
            </div>
        `;

        card.querySelector(".admin-edit").addEventListener("click", () => fillAdminForm(game));
        card.querySelector(".admin-delete").addEventListener("click", () => deleteAdminGame(game.id));
        const blacklistButton = card.querySelector(".admin-blacklist");
        if (blacklistButton) {
            blacklistButton.addEventListener("click", () => blacklistAdminGame(game));
        }
        container.appendChild(card);
    });
}

async function loadAdminGames() {
    const res = await fetch("/api/admin/games");
    const data = await res.json();
    adminGames = Array.isArray(data) ? data : [];
    renderAdminGames();
}

async function saveAdminGame() {
    const name = document.getElementById("admin-name").value.trim();
    if (!name) {
        alert("Game name is required.");
        return;
    }

    const payload = {
        name,
        image: document.getElementById("admin-image").value.trim(),
        summary: document.getElementById("admin-summary").value.trim(),
        is_blacklisted: document.getElementById("admin-blacklisted").checked,
    };

    const igdbIdValue = document.getElementById("admin-igdb-id").value.trim();
    if (igdbIdValue) {
        payload.igdb_id = Number(igdbIdValue);
    }

    const url = editingAdminGameId
        ? `/api/admin/games/${editingAdminGameId}`
        : "/api/admin/games";

    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    resetAdminForm();
    await loadAdminGames();
}

async function deleteAdminGame(gameId) {
    const res = await fetch(`/api/admin/games/${gameId}`, {
        method: "DELETE",
    });
    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    if (editingAdminGameId === gameId) {
        resetAdminForm();
    }
    await loadAdminGames();
}

async function blacklistAdminGame(game) {
    const res = await fetch("/api/admin/blacklist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: game.name,
            image: game.image,
            summary: game.summary,
            igdb_id: game.igdb_id,
        }),
    });
    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    await loadAdminGames();
}

document.addEventListener("DOMContentLoaded", () => {
    resetAdminForm();
    loadAdminGames();
});
