/* Game page: pointer and key input, state drawing, speech and sound wiring, companion relay. */

const canvas = document.getElementById("dotpad");
const ctx = canvas.getContext("2d");
const timeCanvas = document.getElementById("timepad");
const timeCtx = timeCanvas.getContext("2d");

const dayText = document.getElementById("day-text");
const locationText = document.getElementById("location-text");
const pageText = document.getElementById("page-text");
const coinText = document.getElementById("coin-text");
const fertilizerText = document.getElementById("fertilizer-text");
const plotText = document.getElementById("plot-text");
const researchText = document.getElementById("research-text");
const timeText = document.getElementById("time-text");
const buffText = document.getElementById("buff-text");
const ttsText = document.getElementById("tts-text");
const statusElement = document.getElementById("status");
const padPanel = document.getElementById("pad-panel");
const resetButton = document.getElementById("reset-button");
const ttsTestButton = document.getElementById("tts-test-button");

let logicalWidth = 60;
let logicalHeight = 40;
let pointerX = 0;
let pointerY = 0;
let pointerInside = false;
let pointerPressed = false;          // Only genuine presses/clicks (never pointing gesture).
let detailMode = false;              // Read-only inspect mode: Shift or hand-pointing gesture.
let lastDetailAnnouncement = null;
let currentState = null;
let mouseContact = false;  // The mouse (not hand tracking) is over the pad.
const gameAudio = new GameAudio({onNarration:text=>announce(text),onStatus:text=>document.getElementById("sound-text").textContent=text});
gameAudio.preload();
let lastPointerSendAt = 0;
let hoverTimer = null;
let objectSignature = "";
let scoreTimer = null;
const gameSpeech = new GameSpeech({
    getContext: () => { gameAudio.unlock(); return gameAudio.context; },
    onCaption: text => { document.getElementById("caption").textContent = text; },
    onStatus: text => { ttsText.textContent = text; },
    onDucking: active => gameAudio.setDucked(active)
});
function announce(text, priority="action", profile="system", channel="general") {
    if (text) return gameSpeech.say(text, {priority, profile, channel});
}
function connection(ok, message) {
    document.getElementById("connection").classList.toggle("online", ok);
    document.getElementById("connection-text").textContent = message;
}
let requestQueue = Promise.resolve();
let audioPresenceVersion = 0;
function captureAudioRequest() { return gameAudio.suspended ? null : audioPresenceVersion; }
function unlockSpeech() { gameAudio.unlock(); return gameSpeech.unlock(); }
function speak(text, important=true) { return announce(text, important ? "action" : "hover"); }
gameSpeech.voices().then(info => {
    const ready = info.profiles.every(profile => profile.ready);
    document.getElementById("voice-info").textContent = ready
        ? "Consistent English voices · Guide and Rowan"
        : "English voices need setup. Follow the project speech setup guide.";
    if (!gameSpeech.active && gameSpeech.enabled && !gameSpeech.suspended) ttsText.textContent = ready ? "Ready" : "Voice setup needed";
}).catch(() => { document.getElementById("voice-info").textContent = "Could not check English voices. Reload to retry."; });
document.addEventListener("pointerdown", unlockSpeech, {capture:true});
document.addEventListener("keydown", unlockSpeech, {capture:true});

function eventToLogical(event) {
    const rect = canvas.getBoundingClientRect();

    let x = (
        (event.clientX - rect.left) / rect.width * logicalWidth
    );
    let y = (
        (event.clientY - rect.top) / rect.height * logicalHeight
    );

    x = Math.max(0, Math.min(logicalWidth - 0.001, x));
    y = Math.max(0, Math.min(logicalHeight - 0.001, y));

    pointerX = x;
    pointerY = y;
    updateStatus();
}

function updateStatus() {
    const hover = currentState?.hover_object || "None";
    const paused = currentState?.paused ? "Yes" : "No";
    const usedTime = currentState?.time?.used_cells ?? 0;
    const totalTime = currentState?.time?.total_cells ?? 20;
    const dayEnded = currentState?.day_ended ? "Yes" : "No";
    const dragTool = currentState?.drag_tool || "None";
    const buff = currentState?.active_buff || {};

    const pointerModeLabel = pointerPressed ? "PRESS" : detailMode ? "DETAIL" : "POINTER";
    document.getElementById("pointer-info").textContent = `${pointerModeLabel} ${pointerX.toFixed(0)} · ${pointerY.toFixed(0)}`;
    document.getElementById("pointer-led")?.classList.toggle("active", pointerPressed || detailMode);
    statusElement.textContent =
        "Pointer: " + pointerX.toFixed(2) + ", " + pointerY.toFixed(2)
        + "\nPressed: " + pointerPressed
        + "\nDetail mode: " + detailMode
        + "\nHover Object: " + hover
        + "\nDrag Tool: " + dragTool
        + DotdewPages.statusLines.map(line => line(currentState || {})).join("")
        + "\nBuff ticks: " + (buff.remaining_ticks ?? 0)
        + "\nPaused: " + paused
        + "\nTime: " + usedTime + " / " + totalTime
        + "\nNight: " + dayEnded;
    
}

function drawDotMatrix(targetCanvas, targetCtx, dots, width, height) {
    targetCtx.clearRect(0, 0, targetCanvas.width, targetCanvas.height);
    targetCtx.fillStyle = targetCanvas === canvas ? "#30362f" : "#343c30";
    targetCtx.fillRect(0, 0, targetCanvas.width, targetCanvas.height);

    if (!dots || !width || !height) {
        return;
    }

    const cellWidth = targetCanvas.width / width;
    const cellHeight = targetCanvas.height / height;
    targetCtx.fillStyle = "#fff";

    for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
            targetCtx.fillStyle = dots[y]?.[x] ? "#f0efdf" : "#182218";

            const centerX = x * cellWidth + cellWidth / 2;
            const centerY = y * cellHeight + cellHeight / 2;
            const radius = Math.min(cellWidth, cellHeight) * (dots[y]?.[x] ? 0.29 : 0.10);

            targetCtx.beginPath();
            targetCtx.arc(centerX, centerY, radius, 0, Math.PI * 2);
            targetCtx.fill();
        }
    }
}

// A read-only description is independent of the engine's pressed state.
// Engine sends the same geometry it uses for normal object hit-testing.
function inspectObjectContains(obj, x, y) {
    if (obj.type === "mine_rock") {
        const left = obj.x - Math.floor(obj.width / 2);
        const top = obj.y - Math.floor(obj.height / 2);
        return x >= left && x < left + obj.width && y >= top && y < top + obj.height;
    }
    if (obj.type === "route") {
        const dx = obj.x2 - obj.x1, dy = obj.y2 - obj.y1;
        const denom = dx*dx + dy*dy;
        const t = denom ? Math.max(0, Math.min(1, ((x-obj.x1)*dx+(y-obj.y1)*dy)/denom)) : 0;
        return Math.hypot(x-(obj.x1+t*dx), y-(obj.y1+t*dy)) <= (obj.hit_radius ?? 3);
    }
    const halfWidth = (obj.hit_width ?? obj.width ?? 8) / 2;
    const halfHeight = (obj.hit_height ?? obj.height ?? 8) / 2;
    return Math.abs(x-obj.x) <= halfWidth && Math.abs(y-obj.y) <= halfHeight;
}
function findInspectObject(state, x, y) {
    const objects = state?.inspect_objects || [];
    const priorities = ["care_target","harvest_crop","care_button","growth_gauge","plot","seed","ingredient","recipe","shop_item","research","node","plot_detail_field"];
    for (const type of priorities) {
        const found = objects.find(o=>o.type === type && inspectObjectContains(o,x,y));
        if (found) return found;
    }
    return objects.find(o=>o.type !== "route" && inspectObjectContains(o,x,y))
        || objects.find(o=>o.type === "route" && inspectObjectContains(o,x,y)) || null;
}
function paintPointerCursor() {
    if (!currentState || !(pointerInside || document.activeElement === canvas)) return;
    const pitchX = canvas.width / currentState.width;
    const pitchY = canvas.height / currentState.height;
    ctx.strokeStyle = detailMode ? "#f3dc91" : "#a6d983";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.ellipse((pointerX+.5)*pitchX,(pointerY+.5)*pitchY,pitchX*.85,pitchY*.85,0,0,Math.PI*2);
    ctx.stroke();
}
function inspectPointer() {
    if (!detailMode || !currentState || currentState.sleeping || currentState.paused) return;
    const obj = findInspectObject(currentState,pointerX,pointerY);
    const description = obj?.description || (!obj ? (currentState.location_description || currentState.page_name) : obj.label);
    const key = `${currentState.page}|${obj?.id ?? "background"}|${description}`;
    if (lastDetailAnnouncement !== key && description) {
        lastDetailAnnouncement = key;
        announce(description,"hover");
    }
    // The pointer is drawn locally because inspect mode never sends game movement.
    drawDotMatrix(canvas,ctx,currentState.dots,currentState.width,currentState.height);
    paintPointerCursor();
    updateStatus();
}
function setDetailMode(enabled) {
    const next = Boolean(enabled);
    if (detailMode === next) return;
    detailMode = next;
    lastDetailAnnouncement = null;
    updateStatus();
    if (detailMode) {
        if (pointerInside || document.activeElement === canvas) inspectPointer();
    } else if (currentState) {
        drawDotMatrix(canvas,ctx,currentState.dots,currentState.width,currentState.height);
        paintPointerCursor();
    }
}

function drawState(state) {
    timeCanvas.setAttribute("aria-label", state.lower_panel?.label || "Activity time");
    if (currentState && (currentState.page !== state.page || currentState.paused !== state.paused || currentState.sleeping !== state.sleeping)) gameSpeech.stop();
    currentState = state;
    applyClientSettings(state.client_settings);
    logicalWidth = state.width;
    logicalHeight = state.height;

    dayText.textContent = "Day " + state.day;
    locationText.textContent = state.current_location_name;
    pageText.textContent = state.page_name;
    coinText.textContent = state.resources?.coin ?? 0;
    fertilizerText.textContent = state.resources?.fertilizer ?? 0;
    plotText.textContent = state.unlocked_plot_count ?? 2;
    researchText.textContent = "Level " + (state.research_levels?.seed_return ?? 0);

    const used = state.time?.used_cells ?? 0;
    const total = state.time?.total_cells ?? 20;
    timeText.textContent = state.day_ended
        ? "Night " + used + " / " + total
        : used + " / " + total;

    const buff = state.active_buff || {};
    buffText.textContent = state.buff_text || "No food effect";

    if (state.paused) {
        padPanel.classList.add("paused");
    } else {
        padPanel.classList.remove("paused");
    }

    drawDotMatrix(canvas, ctx, state.dots, state.width, state.height);
    drawDotMatrix(
        timeCanvas,
        timeCtx,
        state.time_dots,
        state.time_width,
        state.time_height
    );

    document.getElementById("activity-fill").style.width = `${100 * used / total}%`;
    document.getElementById("remaining-text").textContent = `${total-used} hours`;
    canvas.style.aspectRatio = `${state.width} / ${state.height}`;
    timeCanvas.style.aspectRatio = `${state.time_width} / ${state.time_height}`;
    for (const button of document.querySelectorAll("[data-command]")) {
        const active = ({minimap:"minimap",resources:"inventory",load:"load_game"})[button.dataset.command] === state.page || (button.dataset.command === "pause" && state.paused);
        button.classList.toggle("active", active);
        button.setAttribute("aria-pressed", String(active));
    }
    let task = DotdewPages.task(state, "Select an object to continue");
    if (state.sleeping) task = "Sleeping · A new day will begin shortly";
    if (state.day_ended && !state.sleeping) task = "Night. Select the bed.";
    if (state.paused) task = "Paused · Press F4 to resume";
    document.getElementById("task-progress").textContent = task;
    const objects = (state.objects || []).filter(o=>!DotdewPages.hiddenObjectTypes.has(o.type));
    const signature = JSON.stringify(objects);
    if (signature !== objectSignature) {
        objectSignature = signature;
        const list = document.getElementById("object-list");
        list.replaceChildren();
        if(!objects.length){
            const help=document.createElement("p");help.className="scene-sub";help.style.lineHeight="1.7";
            help.textContent=DotdewPages.emptyHelp[state.page] || "Move over targets. No press needed. Press F1 to open the map.";
            list.append(help);
        }
        objects.forEach(o => {
            const button = document.createElement("button");
            button.append(document.createTextNode(o.label));
            const small = document.createElement("small"); small.textContent = o.description; button.append(small);
            button.addEventListener("focus", ()=>announce(o.description, "hover"));
            button.addEventListener("click", ()=>{
                unlockSpeech();
                if (!o.actionable) { announce(o.description); return; }
                queuePointer("/api/pointer/down",o.x,o.y);
                queuePointer("/api/pointer/up",o.x,o.y);
            });
            list.append(button);
        });
    }
    paintPointerCursor();
    window.dispatchEvent(new CustomEvent("dotdew-state", {detail:state}));
    updateStatus();
    if (detailMode && (pointerInside || document.activeElement === canvas)) inspectPointer();
}

async function handleResponse(response, audioToken) {
    if (!response.ok) throw new Error(`Server error ${response.status}`);
    const data = await response.json();
    const playAudio = audioToken === audioPresenceVersion && !gameAudio.suspended;
    connection(true, "Connected");

    if (data.state) {
        drawState(data.state);
    }

    // Passive visual observer: no input or game logic depends on this listener.
    try { window.dispatchEvent(new CustomEvent("dotdew-observer", {detail: {state:data.state, events:data.sound_events || [], message:data.tts, priority:data.priority, sfx:data.sfx}})); } catch (error) { console.warn("Observer unavailable", error); }

    if (data.tts && playAudio) gameAudio.miningNarrationToken++;
    gameAudio.handle(data.state, playAudio ? data.sound_events || [] : [], playAudio ? data.sfx : null);
    const score = (data.sound_events || []).filter(e=>e.kind === "correct").reduce((n,e)=>n+e.count,0);
    if(score) {
        clearTimeout(scoreTimer);
        document.getElementById("score-feedback").textContent = `+${score} targets reached`;
        scoreTimer=setTimeout(()=>{document.getElementById("score-feedback").textContent="";},1400);
        document.getElementById("score-feedback").animate([{opacity:1},{opacity:0.25}],{duration:600});
    }
    if (!playAudio) {
        if (data.tts) gameSpeech.say(data.tts, {priority:data.priority || "action", profile:data.speech_profile || "system", channel:data.speech_channel || "general", silent:true});
        return;
    }

    if (data.tts) {
        announce(data.tts, data.priority || "action", data.speech_profile || "system", data.speech_channel || "general");
    }
}

let queuedHover = null;
function queuePointer(endpoint, x, y) {
    const audioToken = captureAudioRequest();
    // Spatial audio follows local mouse/hand movement without waiting for the API.
    if (endpoint.endsWith("/move") || endpoint.endsWith("/drag")) gameAudio.move(x,y);
    if (endpoint.endsWith("/move")) {
        if (queuedHover) {queuedHover.x=x;queuedHover.y=y;queuedHover.audioToken=audioToken;return requestQueue;}
        const hover={x,y,audioToken};queuedHover=hover;
        requestQueue=requestQueue.then(async()=>{
            queuedHover=null;
            try {
                const response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({x:hover.x,y:hover.y})});
                await handleResponse(response, hover.audioToken);
            } catch(error) {connection(false,"Connection error · Check the server");}
        });
        return requestQueue;
    }
    if(endpoint.endsWith("/down")) gameAudio.inputDown(currentState,x,y);
    if(endpoint.endsWith("/up")) gameAudio.inputUp();
    requestQueue = requestQueue.then(async () => {
        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({x, y})
            });
            await handleResponse(response, audioToken);
        } catch (error) {
            console.error(error); gameAudio.stopAll(); connection(false,"Connection error · Check the server");
        }
    });

    return requestQueue;
}

function sendMoveIfPossible(force=false) {
    if (!pointerInside) return;
    // Inspection is exclusively client-side. Never call the server's game-moving
    // endpoint: some minigames intentionally respond to movement without a click.
    if (detailMode && !pointerPressed) { inspectPointer(); return; }

    const now = performance.now();
    if (!force && now - lastPointerSendAt < 65) {
        return;
    }

    lastPointerSendAt = now;
    const endpoint = pointerPressed
        ? "/api/pointer/drag"
        : "/api/pointer/move";

    queuePointer(endpoint, pointerX, pointerY);
}

function sendCommand(command) {
    // TEMP_EVALUATION_CLICK: use the latest local tracking position, not a
    // potentially delayed server hover. F4 key-up never clicks a second time.
    if (["click", "pause", "f4", "space", "spacebar", " "].includes(String(command).toLowerCase())) {
        unlockSpeech();
        const x = pointerX, y = pointerY;
        pointerPressed = false;
        // Freeze any coalesced hover before queuing the click.
        queuedHover = null;
        queuePointer("/api/pointer/down", x, y);
        return queuePointer("/api/pointer/up", x, y);
    }
    // Original pause route: enqueueRequest("/api/command", {command:"pause"});
    if ((gameSpeech.active || gameSpeech.pending)?.channel !== "quest") gameSpeech.stop();
    gameAudio.stopTasks();
    unlockSpeech();
    pointerPressed = false;
    return enqueueRequest("/api/command", {command});
}
function enqueueRequest(endpoint, body) {
    const audioToken = captureAudioRequest();
    requestQueue = requestQueue.then(async()=>{
        try {
            const response = await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
            await handleResponse(response, audioToken);
        } catch(error) {
            gameAudio.stopAll(); connection(false,"Connection error · Check the server");
            if (audioToken === audioPresenceVersion && !gameAudio.suspended) announce("Connection error. Check the server.");
        }
    });
    return requestQueue;
}
async function loadState() {
    try {
        const response = await fetch("/api/state", {cache:"no-store"});
        if (!response.ok) throw new Error("Connection failed");
        const state = await response.json();
        drawState(state); gameAudio.handle(state); connection(true,"Connected");
    } catch(error) { connection(false,"Connection error · Check the server"); }
}
canvas.addEventListener("pointerenter", event=>{mouseContact=true;pointerInside=true; eventToLogical(event);sendMoveIfPossible(true)});
canvas.addEventListener("pointerleave", ()=>{mouseContact=false;pointerInside=false;lastDetailAnnouncement=null;clearTimeout(hoverTimer)});
canvas.addEventListener("pointermove", event=>{
    if (!event.isPrimary) return;
    mouseContact=true;
    eventToLogical(event);
    if (pointerPressed) queuePointer("/api/pointer/drag",pointerX,pointerY);
    else sendMoveIfPossible();
});
canvas.addEventListener("pointerdown", event=>{
    if (!event.isPrimary || event.button!==0) return;
    event.preventDefault(); canvas.focus(); unlockSpeech();
    canvas.setPointerCapture(event.pointerId); pointerInside=true;
    eventToLogical(event); pointerPressed=true; queuePointer("/api/pointer/down",pointerX,pointerY);
});
function releasePointer(event) {
    if (!pointerPressed) return;
    eventToLogical(event);pointerPressed=false;
    queuePointer("/api/pointer/up",pointerX,pointerY);
}
canvas.addEventListener("pointerup",releasePointer);
canvas.addEventListener("pointercancel",()=>{pointerPressed=false;sendCommand("release")});
// Keyboard Shift mirrors the future hand-pointing gesture. It never presses the pad.
window.addEventListener("keydown", event => {
    if (event.key !== "Shift" || event.repeat) return;
    if (["INPUT","TEXTAREA","SELECT"].includes(event.target.tagName) || event.target.isContentEditable) return;
    event.preventDefault(); unlockSpeech();
    setDetailMode(true);
});
window.addEventListener("keyup", event => {
    if (event.key !== "Shift") return;
    // Always clear the gesture even if focus moved to a form field meanwhile.
    if (!["INPUT","TEXTAREA","SELECT"].includes(event.target.tagName) && !event.target.isContentEditable) event.preventDefault();
    setDetailMode(false);
});
window.addEventListener("blur", () => setDetailMode(false));
document.addEventListener("visibilitychange", () => {if(document.hidden)setDetailMode(false);});

canvas.addEventListener("keydown", event => {
    const moves = {a:[-1,0],d:[1,0],w:[0,-1],s:[0,1],A:[-1,0],D:[1,0],W:[0,-1],S:[0,1]};
    if (moves[event.key]) {
        event.preventDefault();
        const [dx,dy] = moves[event.key];
        // Shift is a description modifier now, not an acceleration/press key.
        pointerX = Math.max(0,Math.min(logicalWidth-1,pointerX+dx));
        pointerY = Math.max(0,Math.min(logicalHeight-1,pointerY+dy));
        if (detailMode && !pointerPressed) inspectPointer();
        else queuePointer(pointerPressed ? "/api/pointer/drag" : "/api/pointer/move",pointerX,pointerY);
    } else if (event.key === "Enter" && !event.repeat) {
        event.preventDefault(); unlockSpeech();
        queuePointer("/api/pointer/down",pointerX,pointerY);
        queuePointer("/api/pointer/up",pointerX,pointerY);
    }
});
// Space acts as a one-shot left click (the same input path as F4).
// Shift is allowed: holding the detail gesture never disables explicit clicks.
// Native keyboard behavior is preserved in inputs and on focused UI controls.
window.addEventListener("keydown", event => {
    if (event.code !== "Space" && event.key !== " " && event.key !== "Spacebar") return;
    if (event.ctrlKey || event.altKey || event.metaKey) return;
    const target = event.target;
    if (target?.isContentEditable || target?.closest?.('input, textarea, select, button, a, summary, [role="button"], [role="textbox"]')) return;
    event.preventDefault(); // No page scroll and no implicit button activation.
    if (!event.repeat) sendCommand("click");
});
const gameKeys = new GameKeys(command => {
    if (command === "save") document.getElementById("caption").textContent = "Saving game…";
    return sendCommand(command);
});
for (const button of document.querySelectorAll("button[data-command]")) {
    if (button.dataset.command !== "load") {
        button.addEventListener("click", () => sendCommand(button.dataset.command));
        continue;
    }
    let lastRelease = -Infinity;
    button.style.touchAction = "none";
    button.style.userSelect = "none";
    button.addEventListener("contextmenu", event => event.preventDefault());
    button.addEventListener("pointerdown", event => {
        if (event.button !== 0) return;
        event.preventDefault();
        unlockSpeech(); gameKeys.down("F3");
        try {button.setPointerCapture(event.pointerId);} catch {}
        button.classList.add("holding");
    });
    const end = cancelled => {gameKeys.up("F3", cancelled);lastRelease=performance.now();button.classList.remove("holding");};
    button.addEventListener("pointerup", () => end(false));
    button.addEventListener("pointercancel", () => end(true));
    button.addEventListener("lostpointercapture", () => end(true));
    button.addEventListener("keydown", event => {
        if (["Enter", " "].includes(event.key)) {
            event.preventDefault();
            if (!event.repeat) gameKeys.down("F3");
        }
    });
    button.addEventListener("keyup", event => {
        if (["Enter", " "].includes(event.key)) {event.preventDefault();end(false);}
    });
    button.addEventListener("click", event => {
        if (event.detail === 0 && !gameKeys.pressed.has("F3") && performance.now()-lastRelease > 250) sendCommand("load");
    });
}
const padKeys = ["F1","F2","F3","F4","ArrowLeft","ArrowRight"];
window.addEventListener("keydown", event => {
    if (!padKeys.includes(event.key)) return;
    if (event.key.startsWith("Arrow") && ["INPUT","TEXTAREA","SELECT"].includes(event.target.tagName)) return;
    event.preventDefault();
    // Auto-repeat must not cancel and restart speech while F3 is held.
    if (event.repeat || gameKeys.pressed.has(event.key.toUpperCase())) return;
    unlockSpeech();gameKeys.down(event.key);
});
window.addEventListener("keyup", event => {
    if (!padKeys.includes(event.key)) return;
    event.preventDefault();gameKeys.up(event.key);
});
window.addEventListener("blur", () => gameKeys.cancel());
document.addEventListener("visibilitychange", () => {if(document.hidden)gameKeys.cancel();});

ttsTestButton.addEventListener("click", () => {
    unlockSpeech();
    gameAudio.feedback("hover_object");
    speak("Press F1 for the map. Press F2 for your inventory. Press F4 to select.");
});

resetButton.addEventListener("click", () => {
    if (window.confirm("Reset your progress and start a new game?")) {
        gameAudio.stopAll(); unlockSpeech(); enqueueRequest("/api/reset", {});
    }
});
document.getElementById("repeat-button").addEventListener("click",()=>{
    unlockSpeech();
    const dialogue = currentState?.dialogue;
    if (dialogue) announce(`${dialogue.name}. ${dialogue.text}`, "dialogue", dialogue.profile, dialogue.channel || "general");
    else gameSpeech.replay();
});
document.getElementById("speech-stop").addEventListener("click",()=>gameSpeech.stop("Stopped"));
document.getElementById("npc-voice-test").addEventListener("click",()=>{
    unlockSpeech();announce("Rowan. Welcome to my shop. Take your time, and let me know what you need.", "dialogue", "shopkeeper");
});
document.getElementById("mute-button").addEventListener("click",event=>{
    gameSpeech.setEnabled(!gameSpeech.enabled);
    event.currentTarget.textContent=gameSpeech.enabled?"Speech on":"Speech off";
    event.currentTarget.setAttribute("aria-pressed",String(!gameSpeech.enabled));
});
document.getElementById("speech-volume").addEventListener("input",event=>{
    gameSpeech.setVolume(event.target.value);
    const percent = Math.round(gameSpeech.volume*100);
    document.getElementById("speech-volume-label").textContent = percent+"%";
    event.target.setAttribute("aria-valuetext", percent+" percent");
});
document.getElementById("speech-rate").addEventListener("input",event=>{
    gameSpeech.setRate(event.target.value);
    document.getElementById("rate-label").textContent=event.target.value+"×";
});
for (const [id, command] of [["nav-prev", "left"], ["nav-next", "right"]]) {
    const button = document.getElementById(id);
    button.addEventListener("click", () => {
        unlockSpeech();
        pointerPressed = false;
        gameAudio.inputUp();
        sendCommand(command);
    });
}
document.getElementById("sfx-volume").addEventListener("input",event=>{
    gameAudio.unlock();gameAudio.setVolume(event.target.value);document.getElementById("volume-label").textContent=Math.round(event.target.value*100)+"%";
});
document.getElementById("target-cues-toggle").addEventListener("click",event=>{
    gameAudio.setGuidanceEnabled(!gameAudio.guidanceEnabled);
    unlockSpeech();
    event.currentTarget.textContent=gameAudio.guidanceEnabled?"Target cues on":"Target cues off";
    event.currentTarget.setAttribute("aria-pressed",String(gameAudio.guidanceEnabled));
    announce(gameAudio.guidanceEnabled?"Farm and mine target cues on.":"Farm and mine target cues off.");
});
document.getElementById("sfx-toggle").addEventListener("click",event=>{
    gameAudio.unlock();gameAudio.setEnabled(!gameAudio.enabled);
    event.currentTarget.textContent=gameAudio.enabled?"Sound on":"Sound off";
    event.currentTarget.setAttribute("aria-pressed",String(!gameAudio.enabled));
    document.getElementById("sound-text").textContent=gameAudio.enabled?"Task and reward sounds ready":"Sound off";
});
function syncAudioPresence() {
    const away = document.hidden || !document.hasFocus();
    if (away && !gameAudio.suspended) audioPresenceVersion++;
    gameSpeech.setSuspended(away);
    gameAudio.setSuspended(away);
    if (away && pointerPressed) {
        pointerPressed = false;
        // Releasing a gesture must not unlock audio in the background.
        enqueueRequest("/api/command", {command:"release"});
    }
}
window.addEventListener("blur", syncAudioPresence);
window.addEventListener("focus", syncAudioPresence);
document.addEventListener("visibilitychange", syncAudioPresence);
syncAudioPresence();
window.DotdewInput = {
    state:()=>currentState,
    command:(command, phase)=>{
        // Adapters may forward key events rather than DOM keyboard events.
        if (command && typeof command === "object") {phase=command.phase;command=command.key;}
        if (phase === "down") {if(gameKeys.pressed.has(String(command).toUpperCase()))return;unlockSpeech();return gameKeys.down(command);}
        if (phase === "up") return gameKeys.up(command);
        if (phase === "cancel") return gameKeys.up(command,true);
        const match = /^(F[1-4]|ArrowLeft|ArrowRight)_(down|up)$/i.exec(String(command));
        if (match) return match[2].toLowerCase()==="down" ? gameKeys.down(match[1]) : gameKeys.up(match[1]);
        return sendCommand(command);
    },
    keyDown:key=>{
        if (gameKeys.pressed.has(String(key).toUpperCase())) return;
        unlockSpeech();gameKeys.down(key);
    },
    keyUp:key=>gameKeys.up(key),
    // Hand tracker: gesture down => setDetailMode(true), release => false.
    // This is NOT the click button and NEVER invokes /api/pointer/down.
    setDetailMode:(enabled)=>setDetailMode(enabled),
    move:(x,y)=>{mouseContact=false;if(!Number.isFinite(x)||!Number.isFinite(y)||x<0||y<0||x>=logicalWidth||y>=logicalHeight)return;pointerX=x;pointerY=y;pointerInside=true;if(detailMode && !pointerPressed){inspectPointer();return;}return queuePointer(pointerPressed?"/api/pointer/drag":"/api/pointer/move",x,y)},
    press:()=>{unlockSpeech();pointerPressed=true;return queuePointer("/api/pointer/down",pointerX,pointerY)},
    release:()=>{pointerPressed=false;return queuePointer("/api/pointer/up",pointerX,pointerY)}
};
loadState();
// Serialize visual refreshes with pointer input to avoid stale snapshots.
let visualPollPending = false;
let visualPollTimer = null;
let clientSettingsSignature = "";
const delayedVisualPages = ["cooking", "water_minigame", "fertilizer_minigame"];
function applyClientSettings(settings = {}) {
    const signature = JSON.stringify(settings);
    if (signature === clientSettingsSignature) return;
    clientSettingsSignature = signature;
    gameAudio.configure(settings.audio || {});
    document.getElementById("sfx-volume").value = gameAudio.volume;
    document.getElementById("volume-label").textContent = Math.round(gameAudio.volume * 100) + "%";
    const visualRefreshIntervalMs = Math.max(50, Number(settings.visual_refresh_interval_ms) || 100);
    clearInterval(visualPollTimer);
    visualPollTimer = setInterval(refreshDelayedVisuals, visualRefreshIntervalMs);
}
function refreshDelayedVisuals() {
    if (visualPollPending || document.hidden || (!delayedVisualPages.includes(currentState?.page) && !currentState?.sleeping) || currentState.paused) return;
    visualPollPending = true;
    const audioToken = captureAudioRequest();
    requestQueue = requestQueue.then(async () => {
        if ((!delayedVisualPages.includes(currentState?.page) && !currentState?.sleeping) || currentState.paused) return;
        try {
            const response = await fetch("/api/visual-tick", {method:"POST"});
            await handleResponse(response, audioToken);
        } catch (error) {
            connection(false, "Connection error · Check the server");
        }
    }).finally(() => { visualPollPending = false; });
}

DotdewPages.startTimers();


