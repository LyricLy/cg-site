function doUnit(s, ms, amount, unit) {
    const u = Math.floor(ms / amount);
    if (u) {
        s.push(`${u} ${unit}${u > 1 ? "s" : ""}`);
    }
    return ms % amount;
}

for (const elem of document.getElementsByClassName("datetime")) {
    const date = new Date(elem.innerHTML);
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
        const s = [];
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
let sortable;
if (players != null) {
    sortable = new Sortable(players, {
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
        const form = new FormData();
        form.append("type", "like");
        form.append("position", like.getAttribute("like-pos"));
        form.append("checked", like.checked);
        send(form);
    }))
}

const stickyButton = document.getElementById("sticky-button");
const guessPanel = document.getElementById("guess-panel");
function toggleSticky() {
    const list = guessPanel.classList;
    if (list.contains("sticky")) {
        list.remove("sticky");
        stickyButton.innerHTML = "Hide";
    } else {
        list.add("sticky");
        stickyButton.innerHTML = "Show";
    }
}

const download = document.getElementById("download");
const egg = new Konami(() => { download.href = download.href.replace(/bz2/, "bz3"); });
egg.pattern = "788965";

function shuffleGuesses() {
    let order = sortable.toArray();
    for (let i = order.length - 1; i > 0; i--) {
        if (order[i] == "me") continue;
        let j;
        while (true) {
            j = Math.floor(Math.random() * (i + 1));
            if (order[j] != "me") break;
        }
        [order[i], order[j]] = [order[j], order[i]];
    }
    sortable.sort(order, true);
    sortable.option("onSort")();
}

function resize(element) {
    element.style.height = "1px";
    element.style.height = element.scrollHeight+"px";
}

function considerSubmit(event) {
    if (event.which == 13 && !event.shiftKey) {
        event.preventDefault();
        event.target.form.submit();
    }
}

function un(element) {
    element.parentElement.parentElement.removeChild(element.parentElement);
}

const unner = '<button type="button" onclick="un(this)">[x]</button>'

function edit(id, parent, content, anonymous, replyId) {
    const panel = document.getElementById("post-" + parent);
    if (panel.anon) panel.anon.value = anonymous ? "yes" : "no";
    panel.content.value = content;
    const extra = panel.querySelector(".extra");
    extra.innerHTML = ` <span class="edit">editing <a href="#c${id}">#${id}</a> ${unner}<input type="hidden" name="edit" value="${id}"></span>`
    if (replyId) reply(replyId, parent);
}

function reply(id, parent) {
    const panel = document.getElementById("post-" + parent);
    const extra = panel.querySelector(".extra");
    const reply = extra.querySelector(".reply");
    if (reply) extra.removeChild(reply);
    extra.innerHTML += ` <span class="reply">replying to <a href="#c${id}">#${id}</a> ${unner}<input type="hidden" name="reply" value="${id}"></span>`
}
