const loggedIn = window.__QUESTLOG__ && window.__QUESTLOG__.loggedIn === true;

let pendingGame = null;

function escapeHtml(text) {
    if (text == null) return "";
    const s = String(text);
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function igdbCoverUrl(g) {
    if (g && g.cover && g.cover.url) {
        return "https:" + g.cover.url.replace("t_thumb", "t_cover_big");
    }
    return "https://dummyimage.com/600x800/1a1d28/8b92a8&text=No+cover";
}

function placeholderCover() {
    return "https://dummyimage.com/600x800/1a1d28/8b92a8&text=No+cover";
}

function truncateSummary(text, max) {
    if (!text) return "";
    const t = text.replace(/\s+/g, " ").trim();
    if (t.length <= max) return t;
    return t.slice(0, max).trim() + "…";
}

function closeHomeDetail() {
    document.getElementById("home-detail-modal").classList.add("hidden");
}

function closeHomeAdd() {
    document.getElementById("home-add-modal").classList.add("hidden");
    pendingGame = null;
}

function renderCommunity(items) {
    const grid = document.getElementById("grid-community");
    if (!grid) return;
    grid.innerHTML = "";
    items.forEach((item) => {
        const card = document.createElement("div");
        card.className = "home-card";
        card.setAttribute("role", "listitem");
        card.tabIndex = 0;
        const img = item.image || placeholderCover();
        card.innerHTML = `
            <div class="home-card-media"><img src="${escapeHtml(img)}" alt=""></div>
            <div class="home-card-body">
                <strong>${escapeHtml(item.name)}</strong>
                <span class="home-card-badge">${escapeHtml(item.add_count)} saves</span>
            </div>`;
        const im = card.querySelector("img");
        if (im) im.alt = item.name || "";
        card.onclick = () => openDetailCommunity(item);
        card.onkeydown = (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openDetailCommunity(item);
            }
        };
        grid.appendChild(card);
    });
}

function renderPopular(games) {
    const grid = document.getElementById("grid-popular");
    if (!grid) return;
    grid.innerHTML = "";
    games.forEach((g) => {
        const card = document.createElement("div");
        card.className = "home-card";
        card.setAttribute("role", "listitem");
        card.tabIndex = 0;
        const url = igdbCoverUrl(g);
        const rating =
            g.total_rating != null
                ? `<span class="rating-pill">${escapeHtml(Math.round(g.total_rating))}/100</span>`
                : "";
        const genres = g.genres
            ? g.genres
                  .map((x) => x.name)
                  .slice(0, 2)
                  .join(", ")
            : "";
        card.innerHTML = `
            <div class="home-card-media"><img src="${escapeHtml(url)}" alt=""></div>
            <div class="home-card-body">
                <strong>${escapeHtml(g.name)}</strong>
                <span class="home-card-meta">${escapeHtml(genres)}</span>
                ${rating}
            </div>`;
        const im = card.querySelector("img");
        if (im) im.alt = g.name || "";
        card.onclick = () => openDetailPopular(g);
        card.onkeydown = (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openDetailPopular(g);
            }
        };
        grid.appendChild(card);
    });
}

function detailActionsGuest() {
    const actions = document.getElementById("home-detail-actions");
    actions.innerHTML = "";
    const login = document.createElement("a");
    login.className = "btn btn-primary";
    login.href = "/login?next=" + encodeURIComponent("/");
    login.textContent = "Sign in to add";
    const close = document.createElement("button");
    close.type = "button";
    close.className = "btn btn-ghost";
    close.textContent = "Close";
    close.onclick = closeHomeDetail;
    actions.appendChild(login);
    actions.appendChild(close);
}

function detailActionsLoggedIn(onAdd) {
    const actions = document.getElementById("home-detail-actions");
    actions.innerHTML = "";
    const add = document.createElement("button");
    add.type = "button";
    add.className = "btn btn-primary";
    add.textContent = "Add to library";
    add.onclick = () => {
        closeHomeDetail();
        onAdd();
    };
    const close = document.createElement("button");
    close.type = "button";
    close.className = "btn btn-ghost";
    close.textContent = "Close";
    close.onclick = closeHomeDetail;
    actions.appendChild(add);
    actions.appendChild(close);
}

function openDetailCommunity(item) {
    const imgEl = document.getElementById("home-detail-img");
    imgEl.src = item.image || placeholderCover();
    imgEl.alt = item.name || "";
    document.getElementById("home-detail-title").textContent = item.name || "";
    document.getElementById("home-detail-meta").textContent =
        (item.add_count || 0) + " members added this title";
    document.getElementById("home-detail-summary").textContent =
        "Saved by the QuestLog community. Sign in to add it to your shelf and track status, ratings, and notes.";
    if (loggedIn) {
        detailActionsLoggedIn(() => openAddModal(item.name, item.image || placeholderCover()));
    } else {
        detailActionsGuest();
    }
    document.getElementById("home-detail-modal").classList.remove("hidden");
}

function openDetailPopular(g) {
    const imgEl = document.getElementById("home-detail-img");
    imgEl.src = igdbCoverUrl(g);
    imgEl.alt = g.name || "";
    document.getElementById("home-detail-title").textContent = g.name || "";
    const parts = [];
    if (g.genres && g.genres.length) {
        parts.push(g.genres.map((x) => x.name).join(", "));
    }
    if (g.rating_count != null) {
        parts.push(g.rating_count + " IGDB ratings");
    }
    document.getElementById("home-detail-meta").textContent = parts.join(" · ");
    document.getElementById("home-detail-summary").textContent =
        truncateSummary(g.summary, 320) ||
        "No summary available. Add this title to your library to track how you play it.";
    if (loggedIn) {
        detailActionsLoggedIn(() =>
            openAddModal(g.name, igdbCoverUrl(g), { id: g.id })
        );
    } else {
        detailActionsGuest();
    }
    document.getElementById("home-detail-modal").classList.remove("hidden");
}

function openAddModal(name, image, extra) {
    pendingGame = {
        id: extra && extra.id,
        name,
        image,
    };
    document.getElementById("home-add-title").textContent = name;
    document.getElementById("home-add-status").selectedIndex = 0;
    document.getElementById("home-add-rating").value = "";
    document.getElementById("home-add-notes").value = "";
    document.getElementById("home-add-modal").classList.remove("hidden");
}

async function saveHomeAdd() {
    if (!pendingGame) return;
    const res = await fetch("/api/add_game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: pendingGame.name,
            image: pendingGame.image,
            status: document.getElementById("home-add-status").value,
            rating: document.getElementById("home-add-rating").value,
            notes: document.getElementById("home-add-notes").value,
        }),
    });
    if (res.status === 401) {
        window.location.href = "/login?next=" + encodeURIComponent("/");
        return;
    }
    closeHomeAdd();
    loadFeatured();
}

async function loadFeatured() {
    const loading = document.getElementById("home-loading");
    const empty = document.getElementById("popular-empty");
    const gridPopular = document.getElementById("grid-popular");

    if (loading) loading.classList.remove("hidden");
    if (empty) empty.classList.add("hidden");
    if (gridPopular) gridPopular.innerHTML = "";

    try {
        const res = await fetch("/api/featured");
        const data = await res.json();
        if (loading) loading.classList.add("hidden");

        const popular = data.popular || [];

        if (popular.length) {
            if (empty) empty.classList.add("hidden");
            renderPopular(popular);
        } else {
            if (empty) empty.classList.remove("hidden");
        }
    } catch (e) {
        if (loading) loading.classList.add("hidden");
        if (empty) empty.classList.remove("hidden");
    }
}

let searchDebounce = null;

function renderSearchResults(games) {
    const grid = document.getElementById("grid-search");
    if (!grid) return;
    grid.innerHTML = "";
    games.forEach((g) => {
        const card = document.createElement("div");
        card.className = "home-card";
        card.setAttribute("role", "listitem");
        card.tabIndex = 0;
        const url = igdbCoverUrl(g);
        const rating =
            g.total_rating != null
                ? `<span class="rating-pill">${escapeHtml(Math.round(g.total_rating))}/100</span>`
                : "";
        const genres = g.genres
            ? g.genres.map((x) => x.name).slice(0, 2).join(", ")
            : "";
        card.innerHTML = `
            <div class="home-card-media"><img src="${escapeHtml(url)}" alt=""></div>
            <div class="home-card-body">
                <strong>${escapeHtml(g.name)}</strong>
                <span class="home-card-meta">${escapeHtml(genres)}</span>
                ${rating}
            </div>`;
        const im = card.querySelector("img");
        if (im) im.alt = g.name || "";
        card.onclick = () => openDetailPopular(g);
        card.onkeydown = (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openDetailPopular(g);
            }
        };
        grid.appendChild(card);
    });
}

async function searchHome() {
    const inp = document.getElementById("home-search");
    const query = inp ? inp.value.trim() : "";
    const section = document.getElementById("section-search-results");
    const loading = document.getElementById("home-search-loading");
    const grid = document.getElementById("grid-search");
    const empty = document.getElementById("search-empty");
    const sub = document.getElementById("search-results-sub");

    if (!query) {
        if (section) section.classList.add("hidden");
        return;
    }

    if (section) section.classList.remove("hidden");
    if (loading) loading.classList.remove("hidden");
    if (grid) grid.innerHTML = "";
    if (empty) empty.classList.add("hidden");
    if (sub) sub.textContent = "";

    try {
        const res = await fetch("/api/games?q=" + encodeURIComponent(query));
        const games = await res.json();
        if (loading) loading.classList.add("hidden");

        if (games.length) {
            if (sub) sub.textContent = games.length + " result" + (games.length !== 1 ? "s" : "") + " for \u201c" + query + "\u201d";
            renderSearchResults(games);
        } else {
            if (sub) sub.textContent = "for \u201c" + query + "\u201d";
            if (empty) empty.classList.remove("hidden");
        }
    } catch (e) {
        if (loading) loading.classList.add("hidden");
        if (empty) empty.classList.remove("hidden");
        if (sub) sub.textContent = "Something went wrong. Try again.";
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadFeatured();

    const searchInput = document.getElementById("home-search");
    const searchBtn = document.getElementById("home-search-btn");

    if (searchBtn) searchBtn.addEventListener("click", searchHome);
    if (searchInput) {
        searchInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                searchHome();
            }
        });
    }

    const saveBtn = document.getElementById("home-add-save");
    if (saveBtn) saveBtn.addEventListener("click", saveHomeAdd);

    const cancelBtn = document.getElementById("home-add-cancel");
    if (cancelBtn) cancelBtn.addEventListener("click", closeHomeAdd);

    const detailModal = document.getElementById("home-detail-modal");
    if (detailModal) {
        detailModal.addEventListener("click", (e) => {
            if (e.target === detailModal) closeHomeDetail();
        });
    }
    const addModal = document.getElementById("home-add-modal");
    if (addModal) {
        addModal.addEventListener("click", (e) => {
            if (e.target === addModal) closeHomeAdd();
        });
    }
});
