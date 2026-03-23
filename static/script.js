let selectedGame = null;
let libraryGames = [];

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
    if (g.cover && g.cover.url) {
        return "https:" + g.cover.url.replace("t_thumb", "t_cover_big");
    }
    return "https://dummyimage.com/600x800/1a1d28/8b92a8&text=No+cover";
}

function updateLibraryCount() {
    const n = libraryGames.length;
    const el = document.getElementById("library-count");
    if (el) {
        el.textContent = n === 0 ? "No games yet" : n === 1 ? "1 game" : `${n} games`;
    }
    const profileCount = document.getElementById("profile-library-count");
    if (profileCount) profileCount.textContent = String(n);
}

function updateEmptyStates(filtered) {
    const empty = document.getElementById("library-empty");
    const noResults = document.getElementById("library-no-results");
    const grid = document.getElementById("results");
    if (!empty || !noResults || !grid) return;

    const total = libraryGames.length;
    const hasFilter = document.getElementById("search").value.trim().length > 0;

    if (total === 0) {
        empty.classList.remove("hidden");
        noResults.classList.add("hidden");
        grid.classList.add("hidden");
        return;
    }

    empty.classList.add("hidden");
    grid.classList.remove("hidden");

    if (filtered.length === 0 && hasFilter) {
        noResults.classList.remove("hidden");
        grid.classList.add("hidden");
    } else {
        noResults.classList.add("hidden");
        grid.classList.remove("hidden");
    }
}

function renderLibraryGrid(games) {
    const results = document.getElementById("results");
    if (!results) return;
    results.innerHTML = "";

    games.forEach((g) => {
        const card = document.createElement("div");
        card.className = "game-card";
        card.setAttribute("role", "listitem");
        card.tabIndex = 0;
        const img = g.image || "https://dummyimage.com/600x800/1a1d28/8b92a8&text=No+cover";
        const rating =
            g.rating != null && g.rating !== ""
                ? `<span class="rating-pill">${escapeHtml(g.rating)}/10</span>`
                : "";
        card.innerHTML = `
            <div class="game-card-media">
                <img src="${escapeHtml(img)}" class="game-cover" alt="">
            </div>
            <div class="game-info">
                <strong>${escapeHtml(g.name)}</strong>
                <div class="game-meta">${escapeHtml(g.status || "")}</div>
                ${rating}
            </div>
        `;
        const coverImg = card.querySelector(".game-cover");
        if (coverImg) coverImg.alt = g.name || "Game cover";

        card.onclick = () => openGameDetail(g);
        card.onkeydown = (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                openGameDetail(g);
            }
        };
        results.appendChild(card);
    });
}

function applyLibraryFilter() {
    const q = document.getElementById("search").value.trim().toLowerCase();
    let filtered = libraryGames;
    if (q) {
        filtered = libraryGames.filter((g) => {
            const name = (g.name || "").toLowerCase();
            const status = (g.status || "").toLowerCase();
            return name.includes(q) || status.includes(q);
        });
    }
    renderLibraryGrid(filtered);
    updateEmptyStates(filtered);
}

function clearLibrarySearch() {
    document.getElementById("search").value = "";
    applyLibraryFilter();
}

async function fetchLibrary() {
    const res = await fetch("/api/my_games");
    const data = await res.json();
    if (data.error) {
        libraryGames = [];
    } else {
        libraryGames = Array.isArray(data) ? data : [];
    }
    updateLibraryCount();
    applyLibraryFilter();
}

const DISCOVER_SUGGEST_MIN = 2;
const DISCOVER_SUGGEST_DEBOUNCE_MS = 280;

let discoverSuggestTimer = null;
let discoverSuggestController = null;
let discoverSuggestIndex = -1;
let discoverSuggestItems = [];

function hideDiscoverSuggestions() {
    const wrap = document.getElementById("discover-suggestions");
    const inp = document.getElementById("discover-search");
    if (wrap) {
        wrap.classList.add("hidden");
        wrap.innerHTML = "";
    }
    discoverSuggestIndex = -1;
    discoverSuggestItems = [];
    if (inp) inp.setAttribute("aria-expanded", "false");
}

function setDiscoverSuggestActive(i) {
    const wrap = document.getElementById("discover-suggestions");
    if (!wrap) return;
    const buttons = wrap.querySelectorAll(".discover-suggest-item");
    buttons.forEach((b, j) => {
        b.classList.toggle("discover-suggest-item-active", j === i);
    });
    discoverSuggestIndex = i;
}

function selectDiscoverSuggestionGame(g) {
    hideDiscoverSuggestions();
    closeDiscoverModal();
    openModal(g);
}

function renderDiscoverSuggestionsLoading() {
    const wrap = document.getElementById("discover-suggestions");
    const inp = document.getElementById("discover-search");
    if (!wrap) return;
    wrap.innerHTML =
        "<div class=\"discover-suggest-loading\" role=\"status\">Searching…</div>";
    wrap.classList.remove("hidden");
    if (inp) inp.setAttribute("aria-expanded", "true");
    discoverSuggestIndex = -1;
    discoverSuggestItems = [];
}

function renderDiscoverSuggestions(games) {
    const wrap = document.getElementById("discover-suggestions");
    const inp = document.getElementById("discover-search");
    if (!wrap) return;
    wrap.innerHTML = "";
    discoverSuggestItems = Array.isArray(games) ? games.slice(0, 10) : [];

    if (discoverSuggestItems.length === 0) {
        wrap.innerHTML =
            "<div class=\"discover-suggest-empty\">No matches — try another spelling</div>";
        wrap.classList.remove("hidden");
        if (inp) inp.setAttribute("aria-expanded", "true");
        return;
    }

    discoverSuggestItems.forEach((g, i) => {
        const url = igdbCoverUrl(g);
        const genre =
            g.genres && g.genres.length ? g.genres[0].name : "";
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "discover-suggest-item";
        btn.setAttribute("role", "option");
        btn.dataset.index = String(i);
        btn.innerHTML = `
            <img src="${escapeHtml(url)}" alt="" class="discover-suggest-thumb" width="40" height="52">
            <span class="discover-suggest-text">
                <span class="discover-suggest-name">${escapeHtml(g.name)}</span>
                ${genre ? `<span class="discover-suggest-meta">${escapeHtml(genre)}</span>` : ""}
            </span>`;
        btn.addEventListener("mousedown", (e) => e.preventDefault());
        btn.addEventListener("mouseenter", () => setDiscoverSuggestActive(i));
        btn.addEventListener("click", () => selectDiscoverSuggestionGame(g));
        wrap.appendChild(btn);
    });
    wrap.classList.remove("hidden");
    if (inp) inp.setAttribute("aria-expanded", "true");
    discoverSuggestIndex = -1;
}

async function fetchDiscoverSuggestions(query) {
    if (discoverSuggestController) discoverSuggestController.abort();
    discoverSuggestController = new AbortController();
    try {
        const res = await fetch(
            `/api/games?q=${encodeURIComponent(query)}`,
            { signal: discoverSuggestController.signal }
        );
        const games = await res.json();
        return Array.isArray(games) ? games : [];
    } catch (e) {
        if (e.name === "AbortError") return null;
        return [];
    }
}

function scheduleDiscoverSuggestions() {
    const inp = document.getElementById("discover-search");
    if (!inp) return;
    const q = inp.value.trim();
    clearTimeout(discoverSuggestTimer);

    if (q.length < DISCOVER_SUGGEST_MIN) {
        hideDiscoverSuggestions();
        return;
    }

    discoverSuggestTimer = setTimeout(async () => {
        const current = document.getElementById("discover-search")?.value.trim();
        if (current !== q) return;
        renderDiscoverSuggestionsLoading();
        const games = await fetchDiscoverSuggestions(q);
        if (games === null) return;
        const still = document.getElementById("discover-search")?.value.trim();
        if (still !== q) return;
        renderDiscoverSuggestions(games);
    }, DISCOVER_SUGGEST_DEBOUNCE_MS);
}

function openDiscoverModal() {
    document.getElementById("discover-modal").classList.remove("hidden");
    document.getElementById("discover-search").value = "";
    document.getElementById("discover-results").innerHTML = "";
    hideDiscoverSuggestions();
    document.getElementById("discover-search")?.focus();
}

function closeDiscoverModal() {
    document.getElementById("discover-modal").classList.add("hidden");
    hideDiscoverSuggestions();
    clearTimeout(discoverSuggestTimer);
    if (discoverSuggestController) discoverSuggestController.abort();
}

async function searchDiscover() {
    const query = document.getElementById("discover-search").value.trim();
    const container = document.getElementById("discover-results");
    hideDiscoverSuggestions();
    container.innerHTML = "";

    if (!query) {
        container.innerHTML =
            "<p class=\"text-muted discover-results-empty\">Enter a search term.</p>";
        return;
    }

    const res = await fetch(`/api/games?q=${encodeURIComponent(query)}`);
    const games = await res.json();

    if (!Array.isArray(games) || games.length === 0) {
        container.innerHTML =
            "<p class=\"text-muted discover-results-empty\">No results from IGDB.</p>";
        return;
    }

    games.forEach((g) => {
        const url = igdbCoverUrl(g);
        const div = document.createElement("div");
        div.className = "discover-card";
        div.innerHTML = `
            <img src="${escapeHtml(url)}" alt="">
            <span>${escapeHtml(g.name)}</span>
        `;
        div.onclick = () => {
            closeDiscoverModal();
            openModal(g);
        };
        container.appendChild(div);
    });
}

function openModal(g) {
    const imageUrl = igdbCoverUrl(g);

    selectedGame = {
        id: g.id,
        name: g.name,
        image: imageUrl,
    };

    document.getElementById("modal-title").innerText = g.name;
    document.getElementById("status").selectedIndex = 0;
    document.getElementById("rating").value = "";
    document.getElementById("notes").value = "";

    document.getElementById("modal").classList.remove("hidden");
}

function closeModal() {
    document.getElementById("modal").classList.add("hidden");
}

async function saveGame() {
    const status = document.getElementById("status").value;
    const rating = document.getElementById("rating").value;
    const notes = document.getElementById("notes").value;

    await fetch("/api/add_game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: selectedGame.name,
            image: selectedGame.image,
            status: status,
            rating: rating,
            notes: notes,
        }),
    });

    closeModal();
    await fetchLibrary();
}

async function saveGameChanges() {
    await fetch("/api/update_game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: selectedGame.name,
            status: document.getElementById("edit-status").value,
            rating: document.getElementById("edit-rating").value,
            notes: document.getElementById("edit-notes").value,
        }),
    });

    closeGameDetail();
    await fetchLibrary();
}

async function removeGame() {
    await fetch("/api/remove_game", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            name: selectedGame.name,
        }),
    });

    closeGameDetail();
    await fetchLibrary();
}

function closeGameDetail() {
    document.getElementById("game-detail-modal").classList.add("hidden");
}

function showProfile() {
    document.getElementById("library-view").classList.add("hidden");
    document.getElementById("profile-page").classList.remove("hidden");
    loadProfile();
}

function showLibrary() {
    document.getElementById("profile-page").classList.add("hidden");
    document.getElementById("library-view").classList.remove("hidden");
}

async function loadProfile() {
    const res = await fetch("/api/profile");
    const user = await res.json();

    if (user.error) return;

    document.getElementById("display-name").innerText =
        user.display_name || user.username;

    document.getElementById("username").innerText = "@" + user.username;

    document.getElementById("bio").innerText =
        user.bio || "No bio yet";

    const avatarEl = document.getElementById("avatar");
    avatarEl.src =
        user.avatar || "https://dummyimage.com/200x200/1a1d28/8b92a8&text=Avatar";
    avatarEl.alt = user.display_name || user.username || "Profile";

    updateLibraryCount();
}

function openGameDetail(g) {
    selectedGame = g;

    const img = document.getElementById("detail-image");
    img.src = g.image || "";
    img.alt = g.name || "";

    document.getElementById("detail-name").innerText = g.name;

    document.getElementById("view-status").innerText = g.status || "—";
    document.getElementById("view-rating").innerText =
        g.rating != null && g.rating !== "" ? g.rating : "—";
    document.getElementById("view-notes").innerText = g.notes || "—";

    document.getElementById("view-mode").classList.remove("hidden");
    document.getElementById("game-edit-mode").classList.add("hidden");

    document.getElementById("game-detail-modal").classList.remove("hidden");
}

function enableEdit() {
    document.getElementById("edit-status").value = selectedGame.status || "Played";
    document.getElementById("edit-rating").value = selectedGame.rating ?? "";
    document.getElementById("edit-notes").value = selectedGame.notes || "";

    document.getElementById("view-mode").classList.add("hidden");
    document.getElementById("game-edit-mode").classList.remove("hidden");
}

function cancelEdit() {
    document.getElementById("view-mode").classList.remove("hidden");
    document.getElementById("game-edit-mode").classList.add("hidden");
}

async function editProfile() {
    const res = await fetch("/api/profile");
    const user = await res.json();
    if (!user.error) {
        document.getElementById("edit-display-name").value =
            user.display_name || user.username || "";
        document.getElementById("edit-avatar").value = user.avatar || "";
        document.getElementById("edit-bio").value = user.bio || "";
    }
    document.getElementById("profile-modal").classList.remove("hidden");
}

function closeProfileModal() {
    document.getElementById("profile-modal").classList.add("hidden");
}

async function saveProfile() {
    const display_name = document.getElementById("edit-display-name").value;
    const bio = document.getElementById("edit-bio").value;
    const avatar = document.getElementById("edit-avatar").value;

    await fetch("/api/update_profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            display_name,
            bio,
            avatar,
        }),
    });

    closeProfileModal();
    await loadProfile();
}

function logout() {
    window.location.href = "/";
}

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("search");
    if (searchInput) {
        searchInput.addEventListener("input", () => applyLibraryFilter());
    }

    const discoverInput = document.getElementById("discover-search");
    if (discoverInput) {
        discoverInput.addEventListener("input", () => scheduleDiscoverSuggestions());

        discoverInput.addEventListener("keydown", (e) => {
            const wrap = document.getElementById("discover-suggestions");
            const open = wrap && !wrap.classList.contains("hidden");
            const n = discoverSuggestItems.length;

            if (e.key === "ArrowDown" && open && n) {
                e.preventDefault();
                const next =
                    discoverSuggestIndex < n - 1 ? discoverSuggestIndex + 1 : 0;
                setDiscoverSuggestActive(next);
                wrap.querySelectorAll(".discover-suggest-item")[next]?.focus();
                return;
            }
            if (e.key === "ArrowUp" && open && n) {
                e.preventDefault();
                const prev =
                    discoverSuggestIndex > 0 ? discoverSuggestIndex - 1 : n - 1;
                setDiscoverSuggestActive(prev);
                wrap.querySelectorAll(".discover-suggest-item")[prev]?.focus();
                return;
            }
            if (e.key === "Escape" && open) {
                e.preventDefault();
                hideDiscoverSuggestions();
                return;
            }
            if (e.key === "Enter") {
                const active = wrap?.querySelector(".discover-suggest-item-active");
                if (open && active && discoverSuggestIndex >= 0) {
                    e.preventDefault();
                    const g = discoverSuggestItems[discoverSuggestIndex];
                    if (g) selectDiscoverSuggestionGame(g);
                    return;
                }
                e.preventDefault();
                searchDiscover();
            }
        });
    }

    const discoverModal = document.getElementById("discover-modal");
    if (discoverModal) {
        discoverModal.addEventListener("click", (e) => {
            const wrap = document.querySelector(".discover-suggest-wrap");
            if (wrap && !wrap.contains(e.target)) {
                hideDiscoverSuggestions();
            }
        });
    }

    fetchLibrary();
});
