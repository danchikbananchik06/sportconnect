// Slow down the background video on auth pages
window.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('bg-video');
    if (video) {
        video.playbackRate = 0.7; // 0.5x speed = slower
    }
});
// Toggle card description visibility
function toggleDescription(card) {
    // Close any other open card
    document.querySelectorAll('.card').forEach(c => {
        if (c !== card) c.classList.remove('show-description');
    });

    // Toggle the clicked card
    card.classList.toggle('show-description');
}


function addSport(sportName) {
    alert(`${sportName} added to your list!`);
    // later you can send a POST request via fetch() to save it in Flask
}

function addSport(sportName) {
    fetch("/add_sport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sport: sportName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) location.reload();
        else alert("Error adding sport");
    });
}

function removeSport(sportName) {
    fetch("/remove_sport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sport: sportName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) location.reload();
        else alert("Error removing sport");
    });
}

function inviteFriend(button) {
    const parent = button.closest(".added-sport-item");
    const select = parent.querySelector(".invite-friend-select");
    const friendId = select.value;
    const sportName = select.dataset.sport;

    if (!friendId) {
        alert("Select a friend to invite");
        return;
    }

    fetch("/invite_friend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ friend_id: friendId, sport: sportName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Invite sent!");
            select.value = ""; // reset dropdown
        } else {
            alert("Error: " + data.error);
        }
    });
}
function respondInvite(inviteId, response) {
    fetch("/respond_invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ invite_id: inviteId, response: response })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Invite " + response + "!");
            location.reload(); // reload to update the list
        } else {
            alert("Error: " + data.error);
        }
    });
}