window.onload = () => {
    for (const elem of document.getElementsByClassName("datetime")) {
        elem.innerHTML = new Date(elem.innerHTML).toLocaleString();
    }
};

function debounced(func) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), 1500);
    };
}

function send(form) {
    fetch("", { method: "POST", body: form, redirect: "manual" });
}

let players = document.getElementById("players");
if (players != null) {
    var sortable = new Sortable(players, {
        swap: true,
        swapClass: "highlight",
        animation: 100,
        filter: '.you',
        onMove: (evt) => !evt.related.classList.contains("you"),
        onSort: debounced(() => {
            let form = new FormData();
            form.append("type", "guess");
            for (const id of sortable.toArray()) {
                form.append("guess", id);
            }
            send(form);
        }),
    });
}

let target = document.getElementById("target");
if (target != null) {
    target.addEventListener("change", debounced(() => {
        let form = new FormData();
        form.append("type", "target");
        form.append("target", target.value);
        send(form);
    }));
}

for (const like of document.getElementsByClassName("like")) {
    like.addEventListener("change", debounced(() => {
        let form = new FormData();
        form.append("type", "like");
        form.append("position", like.getAttribute("like-pos"));
        form.append("checked", like.checked);
        send(form);
    }))
}
