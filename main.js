function doUnit(s, ms, amount, unit) {
    let u = Math.floor(ms / amount);
    if (u) {
        s.push(`${u} ${unit}${u > 1 ? "s" : ""}`);
    }
    return ms % amount;
}

for (const elem of document.getElementsByClassName("datetime")) {
    let date = new Date(elem.innerHTML);
    if (date < new Date()) {
        elem.innerHTML = date.toLocaleString();
        continue;
    }
    let f = () => {
        let ms = date - new Date();
        if (ms < 0) {
            elem.innerHTML = date.toLocaleString();
            return;
        }
        let s = [];
        ms = doUnit(s, ms, 1000*60*60*24, "day");
        ms = doUnit(s, ms, 1000*60*60, "hour");
        ms = doUnit(s, ms, 1000*60, "minute");
        ms = doUnit(s, ms, 1000, "second");
        elem.innerHTML = `${date.toLocaleString()} (${s.join(", ")})`;
    };
    f();
    setInterval(f, 1000);
}

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

for (const like of document.getElementsByClassName("like")) {
    like.addEventListener("change", debounced(() => {
        let form = new FormData();
        form.append("type", "like");
        form.append("position", like.getAttribute("like-pos"));
        form.append("checked", like.checked);
        send(form);
    }))
}

let stickyButton = document.getElementById("sticky-button");
let guessPanel = document.getElementById("guess-panel");
function toggleSticky() {
    let list = guessPanel.classList;
    if (list.contains("sticky")) {
        list.remove("sticky");
        stickyButton.innerHTML = "Restick";
    } else {
        list.add("sticky");
        stickyButton.innerHTML = "Unstick";
    }
}
