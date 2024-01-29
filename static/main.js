function doUnit(s, ms, amount, unit) {
    const u = Math.floor(ms / amount);
    if (u) {
        s.push(`${u} ${unit}${u > 1 ? "s" : ""}`);
    }
    return ms % amount;
}

for (const elem of document.getElementsByTagName("time")) {
    const date = new Date(elem.innerHTML);
    if (date < new Date()) {
        elem.innerHTML = date.toLocaleString();
        continue;
    }
    const f = () => {
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

const players = document.getElementById("players");
let sortable;
if (players != null) {
    sortable = new Sortable(players, {
        swap: true,
        swapClass: "highlight",
        animation: 100,
        filter: '.locked',
        onMove: (evt) => !evt.related.classList.contains("locked"),
        onSort: debounced(() => {
            const form = new FormData();
            form.append("type", "guess");
            for (const player of players.children) {
                const id = player.getAttribute("data-id");
                if (player.classList.contains("you")) {
                    form.append("guess", "me");
                } else if (player.classList.contains("locked")) {
                    form.append("guess", id + "-locked");
                } else {
                    form.append("guess", id);
                }
            }
            send(form);
        }),
    });
}

function isOnPlayerNumber(event) {
    return event.x < event.target.getBoundingClientRect().left;
}

function setPlayerCursor(event) {
    const s = event.target.style;
    if (s.cursor == "pointer" && !isOnPlayerNumber(event)) {
        s.cursor = null;
    } else if (isOnPlayerNumber(event)) {
        s.cursor = "pointer";
    }
}

function clickPlayer(event) {
    if (isOnPlayerNumber(event)) {
        const index = Array.from(players.children).indexOf(event.target);
        document.getElementsByClassName("entry-header").item(index).scrollIntoView();
    }
}

function swapAlt(elem) {
    const alt = elem.getAttribute("alt");
    elem.setAttribute("alt", elem.innerHTML);
    elem.innerHTML = alt;
}

for (const button of document.getElementsByClassName("toggle")) {
    if (button.hasAttribute("togglevalue")) swapAlt(button);
    button.addEventListener("click", () => {
        swapAlt(button);
        if (button.hasAttribute("togglevalue")) button.removeAttribute("togglevalue");
        else button.setAttribute("togglevalue", "");
        button.dispatchEvent(new Event("toggle"));
    })
}

const guessPanel = document.getElementById("guess-panel");
function toggleSticky() {
    guessPanel.classList.toggle("sticky");
}

const likeToggles = new Set();

const sender = debounced(() => {
    if (!likeToggles.size) return;
    const form = new FormData();
    form.append("type", "like");
    for (const pos of likeToggles) {
        form.append("position", pos);
    }
    likeToggles.clear();
    send(form);
});

function onLike(pos) {
    if (!likeToggles.delete(pos)) {
        likeToggles.add(pos);
    }
    sender();
}

const download = document.getElementById("download");
const egg = new Konami(() => { download.href = download.href.replace(/bz2/, "bz3"); });
egg.pattern = "788965";

let toggleFinish = false;
const sendFinish = debounced(() => {
    if (!toggleFinish) return;
    toggleFinish = false;
    const form = new FormData();
    form.append("type", "finish");
    send(form);
})
function finish() {
    toggleFinish = !toggleFinish;
    sendFinish();
}

function lock(elem) {
    elem.parentElement.classList.toggle("locked");
    sortable.option("onSort")();
}

function shuffleGuesses() {
    const order = Array.from(players.children);
    for (let i = order.length - 1; i > 0; i--) {
        if (order[i].classList.contains("locked")) continue;
        let j;
        while (true) {
            j = Math.floor(Math.random() * (i + 1));
            if (!order[j].classList.contains("locked")) break;
        }
        [order[i], order[j]] = [order[j], order[i]];
    }
    sortable.sort(order.map(x => x.getAttribute("data-id")), true);
    sortable.option("onSort")();
}

function resize(element) {
    element.style.height = "1px";
    element.style.padding = "0px";
    element.style.height = element.scrollHeight + "px";
    element.style.padding = null;
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

function edit(id, parent, content, persona, replyId) {
    const panel = document.getElementById("post-" + parent);
    panel.persona.value = persona;
    panel.content.value = content;
    resize(panel.content);
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
