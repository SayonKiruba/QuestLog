const loggedIn = window.__QUESTLOG__ && window.__QUESTLOG__.loggedIn === true;

function escapeHtml(text) {
    if (text == null) return "";
    const s = String(text);
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function placeholderAvatar() {
    return "https://dummyimage.com/128x128/1a1d28/8b92a8&text=No+avatar";
}

function closeProfileDetail() {
    document.getElementById("profile-detail-modal").classList.add("hidden");
}

function renderProfileCard(profile) {
    const card = document.createElement("div");
    card.className = "home-card";
    card.setAttribute("role", "listitem");
    card.tabIndex = 0;

    const avatar = profile.avatar && profile.avatar.trim() ? profile.avatar : placeholderAvatar();
    const displayName = (profile.display_name && profile.display_name.trim()) ? profile.display_name : profile.username;
    const gameCount = profile.games_count || 0;

    card.innerHTML = `
        <div class="profile-card-media"><img src="${escapeHtml(avatar)}" alt="${escapeHtml(displayName)}"></div>
        <div class="home-card-body">
            <strong>${escapeHtml(displayName)}</strong>
            <span class="home-card-meta">@${escapeHtml(profile.username)}</span>
            <span class="home-card-badge">${gameCount} game${gameCount !== 1 ? 's' : ''}</span>
        </div>
    `;

    const im = card.querySelector("img");
    if (im) im.alt = displayName || "";

    card.onclick = () => viewProfileDetail(profile.username);
    card.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            viewProfileDetail(profile.username);
        }
    };

    return card;
}

async function viewProfileDetail(username) {
    try {
        const response = await fetch(`/api/profiles/${encodeURIComponent(username)}`);
        if (!response.ok) {
            alert("Profile not found");
            return;
        }

        const profile = await response.json();

        document.getElementById("profile-detail-display-name").textContent = 
            (profile.display_name && profile.display_name.trim()) ? profile.display_name : profile.username;
        document.getElementById("profile-detail-username").textContent = `@${profile.username}`;
        document.getElementById("profile-detail-bio").textContent = profile.bio || "(No bio)";
        document.getElementById("profile-detail-count").textContent = profile.games ? profile.games.length : 0;

        const avatar = profile.avatar && profile.avatar.trim() ? profile.avatar : placeholderAvatar();
        document.getElementById("profile-detail-avatar").src = avatar;
        document.getElementById("profile-detail-avatar").alt = profile.username;

        renderProfileGames(profile.games || []);

        document.getElementById("profile-detail-modal").classList.remove("hidden");
    } catch (error) {
        console.error("Error loading profile:", error);
        alert("Failed to load profile");
    }
}

function renderProfileGames(games) {
    const list = document.getElementById("profile-detail-games-list");
    list.innerHTML = "";

    if (!games || games.length === 0) {
        list.innerHTML = "<p class=\"text-muted\">No games in library</p>";
        return;
    }

    const table = document.createElement("table");
    table.className = "profile-games-table";

    games.forEach((game) => {
        const row = document.createElement("tr");
        row.innerHTML = `
            <td class="profile-game-name">${escapeHtml(game.name)}</td>
            <td class="profile-game-status">${escapeHtml(game.status || "—")}</td>
            <td class="profile-game-rating">${game.rating ? `${game.rating}/10` : "—"}</td>
        `;
        table.appendChild(row);
    });

    list.appendChild(table);
}

async function performSearch(query) {
    if (!query.trim()) {
        document.getElementById("section-search-results").classList.add("hidden");
        return;
    }

    document.getElementById("profiles-search-loading").classList.remove("hidden");
    document.getElementById("grid-search").innerHTML = "";
    document.getElementById("search-empty").classList.add("hidden");

    try {
        const response = await fetch(`/api/search_profiles?q=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error("Search failed");

        const results = await response.json();

        document.getElementById("profiles-search-loading").classList.add("hidden");
        document.getElementById("section-search-results").classList.remove("hidden");

        if (results.length === 0) {
            document.getElementById("grid-search").innerHTML = "";
            document.getElementById("search-empty").classList.remove("hidden");
            document.getElementById("search-results-sub").textContent = `No results for "${escapeHtml(query)}"`;
        } else {
            document.getElementById("search-empty").classList.add("hidden");
            const grid = document.getElementById("grid-search");
            grid.innerHTML = "";
            results.forEach((profile) => {
                grid.appendChild(renderProfileCard(profile));
            });
            document.getElementById("search-results-sub").textContent = `${results.length} result${results.length !== 1 ? 's' : ''}`;
        }
    } catch (error) {
        console.error("Search error:", error);
        document.getElementById("profiles-search-loading").classList.add("hidden");
        document.getElementById("search-empty").classList.remove("hidden");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("profiles-search");
    const searchBtn = document.getElementById("profiles-search-btn");

    searchBtn.addEventListener("click", () => {
        performSearch(searchInput.value);
    });

    searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
            performSearch(searchInput.value);
        }
    });

    document.getElementById("profile-detail-modal").addEventListener("click", (e) => {
        if (e.target === e.currentTarget) {
            closeProfileDetail();
        }
    });
});
