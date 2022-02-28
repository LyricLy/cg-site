for (const elem of document.getElementsByClassName("datetime")) {
    elem.innerHTML = new Date(elem.innerHTML).toLocaleString();
}

let players = document.getElementById("players");
if (players != null) {
    var sortable = new Sortable(players, {
        swap: true,
        swapClass: "highlight",
        animation: 100,
        filter: '.you',
        onMove: function (evt) {
            return !evt.related.classList.contains("you");
        }
    });
}
