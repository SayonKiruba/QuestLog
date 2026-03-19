let selectedGame = null;

async function searchGames() {
    const query = document.getElementById("search").value;

    const res = await fetch(`/api/games?q=${query}`);
    const games = await res.json();

    const results = document.getElementById("results");
    results.innerHTML = "";

games.forEach(g => {
    const card = document.createElement("div");
    card.className = "game-card";

let imageUrl = "";

if (g.cover && g.cover.url) {
    imageUrl = "https:" + g.cover.url.replace("t_thumb", "t_cover_big");
} else {
    imageUrl = "https://via.placeholder.com/200x250?text=No+Image";
}

    const genre = g.genres ? g.genres.map(x => x.name).join(", ") : "Unknown";

    card.innerHTML = `
        <img src="${imageUrl}" class="game-img">
        <div class="game-info">
            <strong>${g.name}</strong><br>
            <small>${genre}</small>
        </div>
    `;

    card.onclick = () => openModal(g);

    results.appendChild(card);
});
}

function openModal(g) {
    let imageUrl = "";

    if (g.cover && g.cover.url) {
        imageUrl = "https:" + g.cover.url.replace("t_thumb", "t_cover_big");
    } else {
        imageUrl = "https://dummyimage.com/200x250/34312D/ffffff&text=No+Image";
    }

    selectedGame = {
        id: g.id,
        name: g.name,
        image: imageUrl
    };

    document.getElementById("modal-title").innerText = g.name;

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
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: selectedGame.name,
            image: selectedGame.image,
            status: status,
            rating: rating,
            notes: notes
        })
    });

    closeModal();
}

async function saveGameChanges() {
    await fetch("/api/update_game", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: selectedGame.name,
            status: document.getElementById("edit-status").value,
            rating: document.getElementById("edit-rating").value,
            notes: document.getElementById("edit-notes").value
        })
    });

    closeGameDetail();
    loadMyGames();
}

async function removeGame() {
    await fetch("/api/remove_game", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: selectedGame.name
        })
    });

    closeGameDetail();
    loadMyGames();
}

function closeGameDetail() {
    document.getElementById("game-detail-modal").classList.add("hidden");
}

function showProfile() {
    document.getElementById("profile-page").classList.remove("hidden");
    document.querySelector(".search-box").classList.add("hidden");
    document.getElementById("results").classList.add("hidden");

    loadProfile();
}

async function loadProfile() {
    const res = await fetch("/api/profile");
    const user = await res.json();

    document.getElementById("display-name").innerText =
        user.display_name || user.username;

    document.getElementById("username").innerText =
        "@" + user.username;

    document.getElementById("bio").innerText =
        user.bio || "No bio yet";

    document.getElementById("avatar").src =
        user.avatar || "https://dummyimage.com/100x100/444/fff&text=User";

    loadMyGames();
}

async function loadMyGames() {
    const res = await fetch("/api/my_games");
    const games = await res.json();

    const container = document.getElementById("profile-games");
    container.innerHTML = "";

    games.forEach(g => {
        const card = document.createElement("div");
        card.className = "game-card";

        card.innerHTML = `
    <img src="${g.image}" class="game-cover">
    <div>${g.name}</div>
    <small>${g.status}</small>
`;
        card.onclick = () => openGameDetail(g);
        container.appendChild(card);
    });

}

function openGameDetail(g) {
    selectedGame = g;

    document.getElementById("detail-image").src = g.image;
    document.getElementById("detail-name").innerText = g.name;

    document.getElementById("view-status").innerText = g.status;
    document.getElementById("view-rating").innerText = g.rating || "N/A";
    document.getElementById("view-notes").innerText = g.notes || "None";

    document.getElementById("view-mode").classList.remove("hidden");
    document.getElementById("edit-mode").classList.add("hidden");

    document.getElementById("game-detail-modal").classList.remove("hidden");
}

function enableEdit() {
    // Pre-fill inputs
    document.getElementById("edit-status").value = selectedGame.status;
    document.getElementById("edit-rating").value = selectedGame.rating || "";
    document.getElementById("edit-notes").value = selectedGame.notes || "";

    // Switch modes
    document.getElementById("view-mode").classList.add("hidden");
    document.getElementById("edit-mode").classList.remove("hidden");
}

function cancelEdit() {
    document.getElementById("view-mode").classList.remove("hidden");
    document.getElementById("edit-mode").classList.add("hidden");
}

async function saveGameChanges() {
    await fetch("/api/update_game", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            name: selectedGame.name,
            status: document.getElementById("edit-status").value,
            rating: document.getElementById("edit-rating").value,
            notes: document.getElementById("edit-notes").value
        })
    });

    closeGameDetail();
    loadMyGames();
}

function closeGameDetail() {
    document.getElementById("game-detail-modal").classList.add("hidden");
}

function editProfile() {
    document.getElementById("profile-modal").classList.remove("hidden");
}

function closeProfileModal() {
    document.getElementById("profile-modal").classList.add("hidden");
}

function showSearch() {
    document.getElementById("profile-page").classList.add("hidden");

    document.querySelector(".search-box").classList.remove("hidden");
    document.getElementById("results").classList.remove("hidden");
}

async function saveProfile() {
    const display_name = document.getElementById("edit-display-name").value;
    const bio = document.getElementById("edit-bio").value;
    const avatar = document.getElementById("edit-avatar").value;

    await fetch("/api/update_profile", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            display_name,
            bio,
            avatar
        })
    });

    closeProfileModal();
    loadProfile();
}

function logout() {
    window.location.href = "/";
}

