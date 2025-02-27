function doUnit(s, ms, amount, unit) {
    const u = ms % amount;
    if (u) {
        s.push(`${u} ${unit}${u > 1 ? "s" : ""}`);
    }
    return Math.floor(ms / amount);
}

for (const elem of document.getElementsByTagName("time")) {
    const date = new Date(elem.innerHTML);
    if (date < new Date()) {
        elem.innerHTML = date.toLocaleString();
        continue;
    }
    const f = () => {
        const ms = date - new Date();
        if (ms < 0) {
            elem.innerHTML = date.toLocaleString();
            return;
        }
        const s = [];
        const seconds = Math.floor(ms / 1000);
        const minutes = doUnit(s, seconds, 60, "second");
        const hours = doUnit(s, minutes, 60, "minute");
        const days = doUnit(s, hours, 24, "hour");
        doUnit(s, days, Infinity, "day");
        elem.innerHTML = `${date.toLocaleString()} (${s.reverse().join(", ")})`;
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
if (players !== null) {
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
    if (s.cursor === "pointer" && !isOnPlayerNumber(event)) {
        s.cursor = null;
    } else if (isOnPlayerNumber(event)) {
        s.cursor = "pointer";
    }
}

function clickPlayer(event) {
    if (isOnPlayerNumber(event)) {
        const index = Array.from(players.children).indexOf(event.target) + 1;
        document.getElementById(index.toString()).scrollIntoView();
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

let toggleFinish = false;
const sendFinish = debounced(() => {
    if (!toggleFinish) return;
    toggleFinish = false;
    const form = new FormData();
    form.append("type", "finish");
    send(form);
    sortable.option("onSort")();
})
function finish() {
    toggleFinish = !toggleFinish;
    sendFinish();
    hideLocked();
}

const entries = document.getElementsByClassName("entry");
const hideButton = document.getElementById("hide-button");

if (+localStorage.getItem("hideLocked")) {
    hideButton?.click();
}

function toggleHide() {
    localStorage.setItem("hideLocked", +hideButton.hasAttribute("togglevalue"));
    hideLocked();
}

function hideLocked() {
    document.getElementById("temp")?.remove();
    let numHidden = 0;
    for (let i = 0; i < entries.length; i++) {
        const isHidden = !!+localStorage.getItem("hideLocked") && !!document.querySelector(`[alt="unfinish"]`) && players.children[i].classList.contains("locked");
        numHidden += isHidden;
        if (isHidden !== entries[i].classList.contains("hidden")) entries[i].classList.toggle("hidden");
    }
    if (numHidden) {
        const message = numHidden !== 1 ? `${numHidden} entries are hidden because you are hiding entries you have locked in guesses for.`
            : "your entry is hidden because you are hiding entries you have locked in guesses for.";
        entries[0].insertAdjacentHTML("beforebegin", `<p id="temp">${message}</p>`)
    }
}

function lock(elem) {
    elem.parentElement.classList.toggle("locked");
    hideLocked();
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
    const other = element.cloneNode(true);
    other.style.height = "1px";
    other.style.padding = "0px";
    element.parentElement.append(other);
    other.scrollHeight;  // removing this breaks us on Firefox. I don't know why.
    element.style.height = other.scrollHeight + "px";
    other.remove();
}

for (const elem of document.getElementsByClassName("comment-content")) {
    resize(elem);
    elem.addEventListener("input", () => resize(elem));
}

function considerSubmit(event) {
    if (event.which === 13 && !event.shiftKey) {
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
