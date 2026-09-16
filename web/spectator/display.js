(function(){
"use strict";
try {
const WORLD = { width: 960, height: 600 };
const SCENES = ["home", "farm", "town", "mine"];
const TITLES = {
  home: "Home",
  farm: "The farm",
  town: "Village square",
  mine: "Mountain quarry",
  minimap: "Valley map",
  inventory: "Your inventory",
  research: "Research workshop",
  recipe_select: "The recipe book",
  ingredient_select: "Gathering ingredients",
  cooking: "In the kitchen",
  seed_select: "Choose your seeds",
  plot_detail: "Tending the plot",
  water_minigame: "Watering",
  fertilizer_minigame: "Fertilizing",
  harvest: "Harvest time",
  shop_choice: "The village shop",
  shop_buy: "Buying supplies",
  shop_sell: "Selling produce",
  load_game: "Saved adventures",
};
const SPRITES = {
  tomato: 0,
  carrot: 1,
  potato: 2,
  coin: 3,
  fertilizer: 4,
  seed_tomato: 5,
  seed_carrot: 6,
  seed_potato: 7,
  pickaxe: 8,
  stone: 9,
  copper: 10,
  iron: 11,
  diamond: 12,
  tomato_carrot_stew: 13,
  potato_tomato_soup: 14,
  vegetable_tempura: 15,
  vegetable_fritters: 15,
  sprout: 16,
  leaves: 17,
  plant_tomato: 18,
  plant_carrot: 19,
  plant_potato: 20,
  rock: 21,
  farmer: 22,
  water: 23,
  research: 24,
  wood: 25,
};
function phase(s) {
  const ratio = Math.max(
    0,
    Math.min(1, (s.time?.used_cells || 0) / (s.time?.total_cells || 20)),
  );
  return ratio < 0.25
    ? { name: "Morning", color: "#ffc876", alpha: 0.06 }
    : ratio < 0.6
      ? { name: "Daytime", color: "#ffe8ac", alpha: 0 }
      : ratio < 0.85
        ? { name: "Dusk", color: "#b35b71", alpha: 0.23 }
        : { name: "Evening", color: "#15264f", alpha: 0.46 };
}
function scene(s) {
  if (s.page?.startsWith("shop_")) return "town";
  return SCENES.includes(s.page)
    ? s.page
    : SCENES.includes(s.current_location)
      ? s.current_location
      : "home";
}
function plots(s) {
  const source =
    s.spectator?.plots ||
    Object.entries(s.farm_plots || {})
      .slice(0, s.unlocked_plot_count || 0)
      .map(([id, p]) => ({ id, ...p }));
  const rows = Math.ceil(source.length / 3),
    w = 194,
    h = Math.min(124, 240 / Math.max(1, rows)),
    gap = 20;
  return source.map((p, i) => ({
    ...p,
    x:
      480 -
      (Math.min(3, source.length) * w +
        (Math.min(3, source.length) - 1) * gap) /
        2 +
      (i % 3) * (w + gap),
    y: 280 + Math.floor(i / 3) * (h + 18),
    w,
    h,
  }));
}
function rockRect(r, s) {
  const k = Math.min(790 / (s.width || 60), 430 / (s.height || 40));
  return {
    x: 85 + r.left * k,
    y: 140 + r.top * k,
    w: r.width * k,
    h: r.height * k,
  };
}
function spriteFor(o = {}) {
  const raw = o.id || "",
    id = raw
      .replace(/^inventory_/, "")
      .replace(/^food_/, "")
      .replace(/^crop_/, "")
      .replace(/^recipe_/, "");
  if (
    o.type === "seed" ||
    o.resource_kind === "seed" ||
    o.item_kind === "seed" ||
    o.shop_kind === "seed" ||
    id.startsWith("seed_")
  )
    return (
      SPRITES["seed_" + (o.seed_id || o.item_id || id.replace(/^seed_/, ""))] ??
      5
    );
  if (o.recipe_id) return SPRITES[o.recipe_id] ?? 15;
  if (o.ingredient_id) return SPRITES[o.ingredient_id] ?? 0;
  if (o.seed_id) return SPRITES[o.seed_id] ?? 0;
  if (o.item_id) return SPRITES[o.item_id] ?? 9;
  if (SPRITES[id] !== undefined) return SPRITES[id];
  if (o.type === "research")
    return /seed/.test(id) ? 26 : /mine|pickaxe/.test(id) ? 8 : 28;
  if (o.type === "care_button")
    return /water/.test(id) ? 23 : /fert/.test(id) ? 4 : 0;
  if (o.type === "save_slot") return 27;
  if (o.type === "shop_choice") return /sell/.test(id) ? 3 : 5;
  return 24;
}
function publicCards(s) {
  return (s.spectator?.objects || s.objects || [])
    .filter(
      (o) =>
        ![
          "route",
          "arrow",
          "growth_gauge",
          "plot_detail_field",
          "care_field",
          "care_target",
          "harvest_field",
          "harvest_crop",
          "plot",
          "mine_rock",
        ].includes(o.type),
    )
    .map((o) => ({
      ...o,
      description:
        (s.objects || []).find((x) => x.id === o.id)?.description ||
        o.label ||
        "",
    }));
}
function snapshot(input) {
  return JSON.parse(JSON.stringify(input));
}

const base = new URL(".", document.currentScript.src);
const css = document.createElement("link");
css.rel = "stylesheet";
css.href = new URL("viewer.css?v=side-3", base);
document.head.append(css);
const root = document.createElement("section");
root.className = "dotdew-observer";
root.setAttribute("aria-label", "Dotdew Valley visual companion");
root.innerHTML = `<header class="dv-heading"><div><div class="dv-eyebrow"><span class="dv-live"></span>Visual companion · read only</div><h2>Dotdew Valley</h2></div><div class="dv-tools"><button type="button" data-view="expand">Expand</button><button type="button" data-view="detach">Open window</button></div></header><div class="dv-stage"><canvas width="960" height="600" aria-label="Visual representation of the current game"></canvas><div class="dv-hud"><span class="dv-badge" data-place>Waiting for the game</span><span class="dv-badge" data-clock>Live view</span></div><section class="dv-menu" hidden><h3></h3><div class="dv-subtitle"></div><div class="dv-cards"></div></section><div class="dv-shade" hidden></div></div><footer class="dv-footer"><div class="dv-caption">Your adventure will appear here.</div><div class="dv-status">Following player input</div></footer><div class="dv-details"><span data-detail>Connected to the tactile display. Controls stay on the game pad.</span><div class="dv-events"></div></div>`;
(document.getElementById("visual-relay") || document.querySelector(".container") || document.body).append(root);
const canvas = root.querySelector(".dv-stage>canvas"),
  ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = false;
const sheets = {};
const assetsReady = Promise.all(
  ["scenes", "items", "extras"].map(
    (name) =>
      new Promise((resolve) => {
        const i = new Image();
        i.onload = () => {
          sheets[name] = i;
          resolve();
        };
        i.onerror = () => {
          root.querySelector("[data-detail]").textContent =
            "Some visual artwork could not load. Game controls are unaffected.";
          resolve();
        };
        i.src = new URL(`assets/${name}.png`, base);
      }),
  ),
).then(() => {
  menuKey = "";
  render();
});
let animationFrame = 0;
let state = null,
  lastEnvelope = null,
  menuKey = "",
  message = "Explore at your own pace.",
  particles = [],
  history = [],
  lastEventAt = 0;
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const q = (s) => root.querySelector(s);
function text(s, x, y, color = "#fff2c7", size = 15) {
  ctx.font = `${size}px Georgia`;
  ctx.fillStyle = "#251e19bb";
  ctx.fillRect(x - 7, y - size - 3, ctx.measureText(s).width + 14, size + 12);
  ctx.fillStyle = color;
  ctx.fillText(s, x, y);
}
// Tight source rectangles keep neighboring atlas sprites out of each item.
const rects = [
  [49, 57, 179, 171],
  [309, 36, 154, 206],
  [536, 68, 176, 160],
  [777, 52, 187, 176],
  [1013, 38, 202, 201],
  [51, 271, 177, 210],
  [296, 270, 172, 210],
  [535, 270, 175, 210],
  [774, 286, 185, 186],
  [1019, 292, 187, 180],
  [49, 526, 182, 169],
  [290, 526, 182, 168],
  [536, 531, 174, 155],
  [760, 516, 212, 178],
  [1012, 516, 208, 179],
  [28, 729, 223, 200],
  [305, 778, 156, 145],
  [525, 728, 198, 206],
  [755, 719, 223, 220],
  [1013, 716, 215, 223],
  [33, 963, 206, 232],
  [264, 977, 239, 210],
  [536, 950, 171, 245],
  [745, 987, 228, 180],
  [1002, 1003, 223, 173],
  [60, 108, 528, 455],
  [656, 129, 559, 434],
  [87, 658, 467, 507],
  [715, 650, 457, 507],
];
function sprite(index, x, y, w = 60, h = w, c = ctx) {
  const i = index >= 25 ? sheets.extras : sheets.items;
  if (!i) return;
  const r = rects[index] || rects[24],
    scale = Math.min(w / r[2], h / r[3]) * 0.92,
    dw = r[2] * scale,
    dh = r[3] * scale;
  c.imageSmoothingEnabled = false;
  c.drawImage(i, ...r, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
}
function background(name) {
  const i = sheets.scenes;
  ctx.fillStyle = "#42563e";
  ctx.fillRect(0, 0, 960, 600);
  if (!i) return;
  const rect = {home:[0,0,768,468], farm:[768,0,768,478], town:[0,482,768,542], mine:[768,482,768,542]}[name] || [0,0,768,468];
  ctx.drawImage(i, ...rect, 0, 0, 960, 600);
}
function focused(id) {
  return state.hover_object === id;
}
function outline(x, y, w, h, id) {
  if (!focused(id)) return;
  ctx.strokeStyle = "#fff3ac";
  ctx.lineWidth = 4;
  ctx.strokeRect(x - 4, y - 4, w + 8, h + 8);
}
function farm() {
  for (const p of plots(state)) {
    ctx.fillStyle = p.watered ? "#503d2c" : "#815532";
    ctx.fillRect(p.x, p.y, p.w, p.h);
    ctx.strokeStyle = "#bd9158";
    ctx.lineWidth = 4;
    ctx.strokeRect(p.x, p.y, p.w, p.h);
    ctx.fillStyle = p.watered ? "#3a3026" : "#624126";
    for (let y = 10; y < p.h; y += 20)
      ctx.fillRect(p.x + 6, p.y + y, p.w - 12, 3);
    if (p.seed_id) {
      const growth = p.growth || 0;
      const idx = p.mature
        ? (SPRITES["plant_" + p.seed_id] ?? 17)
        : growth === 0
          ? 16
          : 17;
      const sz = p.mature ? 57 : growth === 0 ? 29 : 34 + 20 * Math.min(1, growth / (p.growth_days || 3));
      for (let i = 0; i < 6; i++) {
        const x = p.x + 8 + (i % 3) * 58,
          y = p.y + 7 + Math.floor(i / 3) * 48;
        sprite(idx, x + (54 - sz) / 2, y + 50 - sz, sz);
      }
    }
    if (p.fertilized) {
      ctx.fillStyle = "#d6b465";
      for (let i = 0; i < 6; i++)
        ctx.fillRect(p.x + 10 + i * 29, p.y + p.h - 7, 3, 3);
    }
    outline(p.x, p.y, p.w, p.h, p.id);
    text(
      `${p.id.replaceAll("_", " ")} · ${p.mature ? "Ready" : p.seed_id || "Empty"}`,
      p.x + 8,
      p.y + p.h - 9,
      "#f4e1a9",
      11,
    );
  }
}
function mine() {
  for (const r of state.spectator?.rocks || []) {
    const b = rockRect(r, state);
    sprite(21, b.x, b.y, b.w, b.h);
    if (r.hits) {
      ctx.strokeStyle = "#302e39";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(b.x + b.w * 0.5, b.y + b.h * 0.22);
      ctx.lineTo(b.x + b.w * 0.4, b.y + b.h * 0.53);
      ctx.lineTo(b.x + b.w * 0.64, b.y + b.h * 0.75);
      if (r.hits > 1) ctx.lineTo(b.x + b.w * 0.32, b.y + b.h * 0.8);
      ctx.stroke();
    }
    outline(b.x, b.y, b.w, b.h, r.id);
  }
}
function facilities() {
  const objects = state.spectator?.objects || state.objects || [];
  for (const o of objects) {
    let b;
    if (o.type === "bed") b = [52, 89, 188, 164];
    else if (o.type === "chest") b = [365, 54, 206, 164];
    else if (o.type === "stove") b = [613, 57, 270, 166];
    else if (o.type === "shop_npc") b = [62, 66, 338, 202];
    if (b && focused(o.id)) {
      outline(...b, o.id);
      text(o.label || o.type, b[0] + 10, b[1] + b[3] + 23);
    }
  }
}
function map() {
  ctx.fillStyle = "#e3d4a6";
  ctx.fillRect(65, 90, 830, 450);
  const nodes = (state.spectator?.objects || []).filter(
    (o) => o.type === "node",
  );
  if (!nodes.length) return;
  const xs = nodes.map((n) => n.x),
    ys = nodes.map((n) => n.y),
    minX = Math.min(...xs),
    minY = Math.min(...ys),
    dx = Math.max(...xs) - minX || 1,
    dy = Math.max(...ys) - minY || 1;
  const at = (x, y) => [
    200 + ((x - minX) / dx) * 560,
    190 + ((y - minY) / dy) * 240,
  ];
  ctx.strokeStyle = "#8e8558";
  ctx.lineWidth = 7;
  for (const r of state.spectator?.routes || []) {
    ctx.beginPath();
    ctx.moveTo(...at(r.x1, r.y1));
    ctx.lineTo(...at(r.x2, r.y2));
    ctx.stroke();
  }
  for (const node of nodes) {
    const name = node.id.replace("map_", ""),
      [x, y] = at(node.x, node.y),
      i = sheets.scenes;
    if (i) {
      const n = SCENES.indexOf(name),
        seam = i.height * 0.46875;
      ctx.drawImage(
        i,
        ((n % 2) * i.width) / 2,
        n < 2 ? 0 : seam,
        i.width / 2,
        n < 2 ? seam : i.height - seam,
        x - 72,
        y - 50,
        144,
        92,
      );
    }
    ctx.strokeStyle =
      state.current_location === name
        ? "#477f50"
        : focused(node.id)
          ? "#fff8cf"
          : "#876a43";
    ctx.lineWidth = state.current_location === name ? 6 : 3;
    ctx.strokeRect(x - 72, y - 50, 144, 92);
    text(node.label, x - 40, y + 67, "#f9e9be", 15);
    if (state.current_location === name) sprite(22, x - 19, y - 88, 40);
  }
}
function mini() {
  const page = state.page,
    cook = page === "cooking";
  ctx.fillStyle = "#1d2119ae";
  ctx.fillRect(0, 0, 960, 600);
  ctx.fillStyle = cook ? "#bc8c52" : "#6c452b";
  ctx.fillRect(75, 95, 810, 450);
  ctx.strokeStyle = "#d8b17d";
  ctx.lineWidth = 7;
  ctx.strokeRect(75, 95, 810, 450);
  const project = (x, y) => [
    95 + (x / (state.width || 60)) * 770,
    110 + (y / (state.height || 40)) * 415,
  ];
  if (cook) {
    const path = state.spectator?.path || [];
    ctx.globalAlpha = 0.3;
    sprite(SPRITES[state.cooking?.recipe_id] ?? 13, 330, 175, 300);
    ctx.globalAlpha = 1;
    ctx.lineWidth = 9;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (let i = 1; i < path.length; i++) {
      if (!path[i].visible && !path[i - 1].visible) continue;
      ctx.strokeStyle = path[i].passed ? "#9cad69" : "#f7e6b7";
      ctx.beginPath();
      ctx.moveTo(...project(path[i - 1].x, path[i - 1].y));
      ctx.lineTo(...project(path[i].x, path[i].y));
      ctx.stroke();
    }
    for (const point of [
      path[0]?.visible ? state.cooking?.start_point : null,
      state.cooking?.resume_point,
    ]) {
      if (!point) continue;
      const [x, y] = project(...point);
      ctx.fillStyle = "#fce7aa";
      ctx.fillRect(x - 10, y - 10, 20, 20);
    }
    text(
      `${state.cooking?.stage_label || "Cooking"} · ${state.cooking?.recipe_name || ""}`,
      95,
      82,
    );
  } else {
    const targets =
      page === "harvest"
        ? state.spectator?.harvest_targets
        : state.spectator?.care_targets;
    for (const t of targets || []) {
      if (!t.visible) continue;
      const [x, y] = project(t.x, t.y);
      ctx.globalAlpha = t.collected ? 0.4 : 1;
      if (page === "harvest") {
        const seed = state.farm_plots?.[state.harvest?.plot_id]?.seed_id;
        sprite(SPRITES[seed] ?? 0, x - 23, y - 23, 46);
      } else {
        ctx.fillStyle = page === "water_minigame" ? "#9accdb" : "#e2ba73";
        ctx.beginPath();
        ctx.arc(x, y, 14, 0, Math.PI * 2);
        ctx.fill();
        if (t.collected) {
          ctx.strokeStyle = "#d8ebba";
          ctx.lineWidth = 4;
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
    }
  }
  const p = state.pointer;
  if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
    const [x, y] = project(p.x, p.y);
    ctx.strokeStyle = p.pressed ? "#fffac6" : "#eeeeee90";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(x, y, 17, 0, Math.PI * 2);
    ctx.stroke();
    if (p.pressed) {
      sprite(
        cook
          ? state.cooking?.gesture_kind === "stir"
            ? 14
            : 1
          : page === "water_minigame"
            ? 23
            : page === "fertilizer_minigame"
              ? 4
              : 8,
        x + 12,
        y - 34,
        38,
      );
    }
  }
}
function detail() {
  const id = state.plot_detail_id,
    p = state.spectator?.plots?.find((p) => p.id === id);
  ctx.fillStyle = "#223322b8";
  ctx.fillRect(0, 70, 960, 530);
  ctx.fillStyle = p?.watered ? "#513c29" : "#855632";
  ctx.fillRect(110, 205, 430, 280);
  for (let i = 0; i < 12; i++) {
    ctx.fillStyle = "#503827";
    ctx.fillRect(124 + (i % 4) * 100, 230 + Math.floor(i / 4) * 75, 83, 5);
    if (p?.seed_id)
      sprite(
        p.mature ? (SPRITES["plant_" + p.seed_id] ?? 17) : p.growth ? 17 : 16,
        128 + (i % 4) * 100,
        211 + Math.floor(i / 4) * 75,
        76,
      );
  }
  text(`${id || "Plot"} · ${p?.seed_id || "Empty soil"}`, 125, 177);
  text(
    `${p?.watered ? "Watered" : "Needs water"} · ${p?.fertilized ? "Fertilized" : "No fertilizer"}`,
    125,
    520,
    "#eedbad",
    14,
  );
}
function render() {
  if (document.getElementById("visual-relay")) return;
  if (!state) return;
  const loc = scene(state);
  background(loc);
  if (state.page === "farm") farm();
  else if (state.page === "mine") mine();
  else if (SCENES.includes(state.page)) facilities();
  if (SCENES.includes(state.page) && state.page !== "mine")
    sprite(
      22,
      state.page === "farm" ? 835 : state.page === "town" ? 610 : 425,
      state.page === "farm" ? 430 : state.page === "town" ? 325 : 340,
      74,
    );
  const ph = phase(state);
  ctx.fillStyle = ph.color;
  ctx.globalAlpha = ph.alpha;
  ctx.fillRect(0, 0, 960, 600);
  ctx.globalAlpha = 1;
  if (state.page === "minimap") map();
  if (
    ["cooking", "harvest", "water_minigame", "fertilizer_minigame"].includes(
      state.page,
    )
  )
    mini();
  if (state.page === "plot_detail") detail();
  if (state.sleeping) {
    ctx.fillStyle = "#11192c99";
    ctx.fillRect(0, 0, 960, 600);
  }
  drawParticles();
}
function drawParticles() {
  const now = performance.now();
  particles = particles.filter((p) => p.until > now);
  for (const p of particles) {
    const t = (p.until - now) / 1100;
    ctx.globalAlpha = Math.max(0, t);
    ctx.fillStyle = p.color;
    ctx.fillRect(p.x + p.dx * (1 - t), p.y - 60 * (1 - t), 5, 5);
    ctx.globalAlpha = 1;
  }
}
function burst(color = "#f6d786") {
  if (reduced) return;
  const pointer = state.pointer || {};
  let x = 480,
    y = 300;
  if (
    ["cooking", "water_minigame", "fertilizer_minigame", "harvest"].includes(
      state.page,
    )
  ) {
    x = 95 + ((pointer.x ?? 30) / (state.width || 60)) * 770;
    y = 110 + ((pointer.y ?? 20) / (state.height || 40)) * 415;
  } else if (state.page === "mine") {
    x =
      85 +
      (pointer.x ?? 30) *
        Math.min(790 / (state.width || 60), 430 / (state.height || 40));
    y =
      140 +
      (pointer.y ?? 20) *
        Math.min(790 / (state.width || 60), 430 / (state.height || 40));
  }
  for (let i = 0; i < 12; i++)
    particles.push({
      x,
      y,
      dx: (i - 6) * 12,
      color,
      until: performance.now() + 1100,
    });
  if (!animationFrame) animationFrame = requestAnimationFrame(frame);
}
function menus() {
  const show =
    !SCENES.includes(state.page) &&
    ![
      "minimap",
      "cooking",
      "water_minigame",
      "fertilizer_minigame",
      "harvest",
    ].includes(state.page);
  const menu = q(".dv-menu");
  menu.hidden = !show;
  if (!show) return;
  const cards = publicCards(state),
    key = JSON.stringify([
      state.page,
      cards,
      state.hover_object,
      state.resources,
      state.cooking?.selected_ingredients,
    ]);
  if (key === menuKey) return;
  menuKey = key;
  menu.style.left =
    state.page === "plot_detail"
      ? "61%"
      : state.page?.startsWith("shop_")
        ? "36%"
        : "";
  menu.style.right = state.page === "plot_detail" ? "3%" : "";
  q(".dv-menu h3").textContent = TITLES[state.page] || state.page_name;
  q(".dv-subtitle").textContent =
    state.page === "inventory"
      ? `Page ${state.inventory?.page || 1} of ${state.inventory?.pages || 1}`
      : state.page === "ingredient_select"
        ? "Following the player’s ingredient selection"
        : state.page === "load_game"
          ? "Saved slots · viewing only"
          : "Player selection";
  const grid = q(".dv-cards");
  grid.replaceChildren();
  grid.style.gridTemplateColumns =
    state.page === "plot_detail"
      ? "1fr"
      : state.page?.startsWith("shop_")
        ? "repeat(3,minmax(0,1fr))"
        : "";
  for (const o of cards) {
    const card = document.createElement("article");
    card.className =
      "dv-card" +
      (focused(o.id) ? " is-focused" : "") +
      (o.selected ? " is-selected" : "");
    card.dataset.objectId = o.id;
    const c = document.createElement("canvas");
    c.width = c.height = 80;
    sprite(spriteFor(o), 0, 0, 80, 80, c.getContext("2d"));
    const title = document.createElement("strong");
    title.textContent = o.label;
    const small = document.createElement("small");
    small.textContent = o.description;
    card.append(c, title, small);
    grid.append(card);
  }
  if (!cards.length) {
    const empty = document.createElement("p");
    empty.textContent = "Nothing to display on this page.";
    grid.append(empty);
  }
}
function updateUI() {
  const ph = phase(state);
  q("[data-place]").textContent =
    TITLES[state.page] || state.page_name || "Dotdew Valley";
  q("[data-clock]").textContent =
    `Day ${state.day} · ${ph.name} · ${state.resources?.coin ?? 0} gold`;
  q(".dv-caption").textContent = message;
  q("[data-detail]").textContent =
    state.buff_text ||
    "Read-only companion · selections and actions follow the game pad.";
  const shade = q(".dv-shade");
  shade.hidden = !state.sleeping && !state.paused;
  shade.replaceChildren();
  if (!shade.hidden) {
    const title = document.createElement("div");
    title.textContent = state.sleeping
      ? "Resting until morning…"
      : "Game paused";
    const small = document.createElement("small");
    small.textContent = state.sleeping
      ? "☾  ·  ✦  ·  ☾"
      : "The adventure will resume with the player";
    title.append(small);
    shade.append(title);
  }
  menus();
  render();
}
function receive(envelope) {
  if (!envelope?.state) return;
  const packet = snapshot(envelope),
    prev = state;
  state = packet.state;
  lastEnvelope = packet;
  if (packet.message) message = packet.message;
  else if (prev?.page !== state.page)
    message = TITLES[state.page] || state.page_name;
  const changedDay = prev && prev.day !== state.day;
  if (changedDay) {
    message = `A new morning. Day ${state.day}.`;
    burst("#ffe9a3");
  }
  for (const e of packet.events || []) {
    if (e.kind === "correct") burst();
    else if (e.kind === "item_destroyed") burst("#ef986c");
    else if (e.sound === "shine" || e.reward_sound === "shine")
      burst("#9cedff");
    else if (e.sound !== "step") burst("#e7c88a");
  }
  if (
    packet.message &&
    packet.priority !== "hover" &&
    (packet.events?.length || packet.sfx || changedDay)
  ) {
    const now = performance.now();
    if (now - lastEventAt > 180 || history[0] !== packet.message) {
      history.unshift(packet.message);
      history = history.slice(0, 3);
      lastEventAt = now;
      q(".dv-events").replaceChildren(
        ...history.map((t) => {
          const el = document.createElement("span");
          el.className = "dv-event";
          el.textContent = t;
          return el;
        }),
      );
    }
  }
  updateUI();
}
let channel = null;
const isDetached = document.body.dataset.spectator === "standalone",
  isDemo = document.body.dataset.spectator === "demo";
let session = new URL(location.href).searchParams.get("session");
if (!isDetached && !isDemo)
  session = crypto.randomUUID?.() || String(Date.now());
try {
  if (!isDemo) channel = new BroadcastChannel("dotdew-view-" + session);
} catch {}
if (channel)
  channel.onmessage = (e) => {
    if (isDetached && e.data?.kind === "snapshot") receive(e.data.payload);
    else if (!isDetached && e.data?.kind === "request" && lastEnvelope)
      channel.postMessage({ kind: "snapshot", payload: lastEnvelope });
  };
function relay(data) {
  receive(data);
  if (channel && !isDetached)
    channel.postMessage({ kind: "snapshot", payload: lastEnvelope });
}
if (!isDetached && !isDemo) {
  window.addEventListener("dotdew-state", (e) => relay({ state: e.detail }));
  window.addEventListener("dotdew-observer", (e) => relay(e.detail));
  const initial = window.DotdewInput?.state?.();
  if (initial) relay({ state: initial });
}
if (isDetached || isDemo) {
  q('[data-view="detach"]').hidden = true;
  channel?.postMessage({ kind: "request" });
}
q('[data-view="expand"]').onclick = () => {
  root.classList.toggle("dv-expanded");
  q('[data-view="expand"]').textContent = root.classList.contains("dv-expanded")
    ? "Restore"
    : "Expand";
};
q('[data-view="detach"]').onclick = () => {
  window.open(
    new URL("standalone.html?session=" + encodeURIComponent(session), base),
    "dotdew-visual-" + session,
    "width=1150,height=850",
  );
};
function frame(now) {
  animationFrame = 0;
  if (document.hidden) {particles = []; return;}
  render();
  if (particles.length) animationFrame = requestAnimationFrame(frame);
}
const ready = assetsReady;


const loadStatus = document.getElementById('visual-load-status');
const openButton = document.getElementById('show-visual');
if (openButton) {
  ready.then(() => {
    loadStatus.textContent = 'Ready. Open the linked visual window.';
    openButton.disabled = false;
    openButton.onclick = () => {
      const child = window.open(new URL('standalone.html?session='+encodeURIComponent(session),base),
        'dotdew-visual-'+session, 'width=1150,height=850');
      loadStatus.textContent = child ? 'Visual window connected. Keep this game page open.' : 'Allow pop-ups for this site, then press Open visual display again.';
    };
  });
}

} catch(error) {
 const status=document.getElementById('visual-load-status');
 if(status) status.textContent='Visual display error: '+error.message;
 const hint=document.getElementById('visual-placeholder');
 if(hint) hint.textContent='The visual display could not start. Reload this page. '+error.message;
 console.error('Visual display failed',error);
}
})();
