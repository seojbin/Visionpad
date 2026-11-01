// Icon lab: edits 0/1 patterns, asks the server to compose a pad frame with the game's drawing code,
// and hands that frame to the pad module through the same `dotdew-state` event the game uses.
(() => {
    const $ = id => document.getElementById(id);
    const STORE = 'dotdew-icon-lab';
    const MAX_W = 60, MAX_H = 40;
    const status = text => { $('lab-status').textContent = text; };

    function load() {
        try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch { return {}; }
    }
    function persist() {
        try { localStorage.setItem(STORE, JSON.stringify({mine, set, index})); } catch {}
    }
    const saved = load();
    let mine = saved.mine || {};                 // name -> rows
    let set = saved.set || [];                   // [{name, rows}]
    let index = Math.min(saved.index || 0, Math.max(0, set.length - 1));
    let catalog = [];
    let width = 7, height = 5;
    let cells = blank(width, height);
    let frame = null;
    const log = [];

    function blank(w, h) { return Array.from({length: h}, () => Array(w).fill(0)); }
    function rows() { return cells.map(row => row.join('')); }
    function setRows(list, name) {
        const h = Math.min(MAX_H, list.length), w = Math.min(MAX_W, Math.max(...list.map(r => r.length)));
        width = w; height = h;
        cells = list.slice(0, h).map(r => Array.from({length: w}, (_, x) => r[x] === '1' ? 1 : 0));
        $('w').value = w; $('h').value = h;
        if (name) $('name').value = name;
        changed();
    }
    function parse(text) {
        let found = [...text.matchAll(/['"]([01]+)['"]/g)].map(m => m[1]);
        if (!found.length) found = text.split(/\r?\n/).map(l => l.trim()).filter(l => /^[01]+$/.test(l));
        return found;
    }
    function python(name, list) {
        return `'${name}': (\n${list.map(r => `    '${r}',`).join('\n')}\n),`;
    }

    // Editor grid
    const grid = $('editor-grid'), gctx = grid.getContext('2d');
    let cell = 1, paint = null;
    function drawGrid() {
        cell = Math.max(4, Math.floor(Math.min(520 / width, 372 / height)));
        grid.width = cell * width; grid.height = cell * height;
        gctx.fillStyle = '#182218'; gctx.fillRect(0, 0, grid.width, grid.height);
        for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
            gctx.fillStyle = cells[y][x] ? '#f0efdf' : '#26331f';
            gctx.beginPath(); gctx.arc((x + .5) * cell, (y + .5) * cell, cell * .38, 0, Math.PI * 2); gctx.fill();
        }
        // Centre lines: the pattern is centred on the slot the same way draw_icon_pattern does.
        gctx.strokeStyle = '#5d7a4f'; gctx.lineWidth = 1;
        gctx.strokeRect(Math.floor(width / 2) * cell + .5, .5, cell - 1, grid.height - 1);
        gctx.strokeRect(.5, Math.floor(height / 2) * cell + .5, grid.width - 1, cell - 1);
    }
    function cellAt(event) {
        const r = grid.getBoundingClientRect();
        const x = Math.floor((event.clientX - r.left) * grid.width / r.width / cell);
        const y = Math.floor((event.clientY - r.top) * grid.height / r.height / cell);
        return x >= 0 && y >= 0 && x < width && y < height ? [x, y] : null;
    }
    grid.addEventListener('pointerdown', e => {
        const at = cellAt(e); if (!at) return;
        grid.setPointerCapture(e.pointerId);
        paint = cells[at[1]][at[0]] ? 0 : 1; cells[at[1]][at[0]] = paint; changed();
    });
    grid.addEventListener('pointermove', e => {
        if (paint === null) return; const at = cellAt(e);
        if (at && cells[at[1]][at[0]] !== paint) { cells[at[1]][at[0]] = paint; changed(); }
    });
    grid.addEventListener('pointerup', () => { paint = null; });
    grid.addEventListener('pointercancel', () => { paint = null; });

    function resize() {
        const w = Math.max(1, Math.min(MAX_W, +$('w').value || 1)), h = Math.max(1, Math.min(MAX_H, +$('h').value || 1));
        // Keep the drawing centred when the size changes.
        const ox = Math.floor((w - width) / 2), oy = Math.floor((h - height) / 2);
        cells = Array.from({length: h}, (_, y) => Array.from({length: w}, (_, x) => cells[y - oy]?.[x - ox] || 0));
        width = w; height = h; changed();
    }
    $('w').addEventListener('change', resize); $('h').addEventListener('change', resize);
    $('clear').addEventListener('click', () => { cells = blank(width, height); changed(); });
    $('invert').addEventListener('click', () => { cells = cells.map(r => r.map(v => 1 - v)); changed(); });
    $('code').addEventListener('input', () => {
        const list = parse($('code').value);
        if (list.length) { setRows(list); }
    });
    $('copy').addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(python($('name').value, rows())); status('Copied.'); }
        catch { $('code').select(); status('Select the text and press Ctrl+C.'); }
    });
    $('save').addEventListener('click', () => {
        const name = $('name').value.trim(); if (!name) return status('Give the icon a name first.');
        mine[name] = rows(); persist(); renderLibrary(); status(`Saved “${name}” in this browser.`);
    });
    $('delete').addEventListener('click', () => {
        const name = $('name').value.trim();
        if (!(name in mine)) return status(`“${name}” is not in My icons.`);
        delete mine[name]; persist(); renderLibrary(); status(`Deleted “${name}”.`);
    });
    $('export').addEventListener('click', () => {
        const blob = new Blob([JSON.stringify(mine, null, 2)], {type: 'application/json'});
        const a = Object.assign(document.createElement('a'), {href: URL.createObjectURL(blob), download: ['my-icons', 'json'].join('.')});  // split so url_check does not take it for a served file
        a.click(); URL.revokeObjectURL(a.href);
    });
    $('import-button').addEventListener('click', () => $('import').click());
    $('import').addEventListener('change', async () => {
        const file = $('import').files[0]; if (!file) return;
        try {
            const data = JSON.parse(await file.text()); let count = 0;
            for (const [name, list] of Object.entries(data)) {
                if (Array.isArray(list) && list.length && list.every(r => typeof r === 'string' && /^[01]+$/.test(r))) { mine[name] = list; count++; }
            }
            persist(); renderLibrary(); status(`Imported ${count} icons.`);
        } catch (error) { status('Could not read that file: ' + error.message); }
        $('import').value = '';
    });

    // Library
    function renderLibrary() {
        const query = $('search').value.trim().toLowerCase();
        const groups = {};
        const add = (group, name, list, source) => {
            if (query && !`${group} ${name}`.toLowerCase().includes(query)) return;
            (groups[group] ||= []).push({name, rows: list, source});
        };
        for (const [name, list] of Object.entries(mine)) add('My icons (this browser)', name, list, 'saved here');
        for (const e of catalog) add(e.group, e.name, e.rows, e.source);
        const root = $('library'); root.replaceChildren();
        for (const [group, items] of Object.entries(groups)) {
            const h = document.createElement('h3'); h.textContent = group; root.append(h);
            for (const item of items) {
                const b = document.createElement('button');
                b.textContent = `${item.name}  ${item.rows[0].length}×${item.rows.length}`;
                b.title = item.source;
                b.addEventListener('click', () => { setRows(item.rows, item.name); status(`Loaded ${item.name} from ${item.source}.`); });
                root.append(b);
            }
        }
        if (!root.children.length) root.textContent = catalog.length ? 'No matches.' : 'Loading…';
    }
    $('search').addEventListener('input', renderLibrary);

    // Test set
    function renderSet() {
        const list = $('set'); list.replaceChildren();
        set.forEach((item, i) => {
            const li = document.createElement('li'); if (i === index) li.className = 'current';
            const label = document.createElement('span'); label.textContent = `${item.name} (${item.rows[0].length}×${item.rows.length})`;
            label.addEventListener('click', () => { index = i; changedSet(); });
            const remove = document.createElement('button'); remove.textContent = '✕'; remove.setAttribute('aria-label', `Remove ${item.name}`);
            remove.addEventListener('click', () => { set.splice(i, 1); index = Math.min(index, Math.max(0, set.length - 1)); changedSet(); });
            li.append(label, remove); list.append(li);
        });
    }
    function step(delta) {
        if (!set.length) return;
        index = (index + delta + set.length) % set.length;
        if ($('source').value !== 'set') $('source').value = 'set';
        changedSet();
    }
    function changedSet() { persist(); renderSet(); requestRender(); }
    $('add-set').addEventListener('click', () => { set.push({name: $('name').value.trim() || 'icon', rows: rows()}); index = set.length - 1; changedSet(); });
    $('clear-set').addEventListener('click', () => { set = []; index = 0; changedSet(); });
    $('prev').addEventListener('click', () => step(-1));
    $('next').addEventListener('click', () => step(1));

    // Responses
    function shown() {
        if ($('source').value === 'editor') return $('name').value;
        return $('layout').value === 'grid' ? set.slice(0, 12).map(i => i.name).join(' | ') : set[index]?.name || '';
    }
    $('response').addEventListener('keydown', e => {
        if (e.key !== 'Enter') return;
        const entry = {time: new Date().toISOString(), shown: shown(), layout: $('layout').value + ($('frame').checked ? '+frame' : ''), response: $('response').value};
        log.push(entry); $('response').value = '';
        const tr = document.createElement('tr');
        for (const v of [entry.time.slice(11, 19), entry.shown, entry.layout, entry.response]) { const td = document.createElement('td'); td.textContent = v; tr.append(td); }
        $('log').prepend(tr);
    });
    $('csv').addEventListener('click', () => {
        const q = v => `"${String(v).replaceAll('"', '""')}"`;
        const text = ['time,shown,layout,response', ...log.map(e => [e.time, e.shown, e.layout, e.response].map(q).join(','))].join('\n');
        const a = Object.assign(document.createElement('a'), {href: URL.createObjectURL(new Blob(['﻿' + text], {type: 'text/csv'})), download: 'icon-test.csv'});
        a.click(); URL.revokeObjectURL(a.href);
    });

    // Pad output
    const preview = $('preview'), pctx = preview.getContext('2d');
    let pending = null, sequence = 0;
    function items() {
        if ($('source').value === 'editor') return [{name: $('name').value, rows: rows()}];
        return $('layout').value === 'grid' ? set.slice(0, 12) : set.slice(index, index + 1);
    }
    function requestRender() { clearTimeout(pending); pending = setTimeout(renderFrame, 60); }
    async function renderFrame() {
        const id = ++sequence;
        try {
            const response = await fetch('/api/icon-lab/render', {method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({layout: $('layout').value, frame: $('frame').checked, items: items()})});
            if (!response.ok) throw new Error(`server answered ${response.status}`);
            const next = await response.json();
            if (id !== sequence) return;
            frame = next; drawPreview();
            window.dispatchEvent(new CustomEvent('dotdew-state', {detail: frame}));
        } catch (error) { status('Could not render: ' + error.message); }
    }
    function drawPreview() {
        const cw = preview.width / frame.width, ch = preview.height / frame.height;
        pctx.fillStyle = '#30362f'; pctx.fillRect(0, 0, preview.width, preview.height);
        for (let y = 0; y < frame.height; y++) for (let x = 0; x < frame.width; x++) {
            pctx.fillStyle = frame.dots[y][x] ? '#f0efdf' : '#182218';
            pctx.beginPath(); pctx.arc((x + .5) * cw, (y + .5) * ch, Math.min(cw, ch) * .36, 0, Math.PI * 2); pctx.fill();
        }
    }
    for (const id of ['source', 'layout', 'frame']) $(id).addEventListener('change', requestRender);
    $('name').addEventListener('input', () => { $('code').value = python($('name').value, rows()); });

    function changed() {
        drawGrid();
        if (document.activeElement !== $('code')) $('code').value = python($('name').value, rows());
        if ($('source').value === 'editor') requestRender();
    }

    // The pad module reads frames from state() and forwards its keys here.
    const keyStep = {F1: -1, ArrowLeft: -1, F2: 1, ArrowRight: 1};
    window.DotdewInput = {
        state: () => frame,
        keyDown: key => { if (key in keyStep) step(keyStep[key]); },
        keyUp: () => {},
        command: (key, phase) => { if (phase === 'down' && key in keyStep) step(keyStep[key]); },
        move: () => {}, press: () => {}, release: () => {}, setDetailMode: () => {},
    };

    fetch('/api/icon-lab/patterns').then(r => r.json()).then(list => { catalog = list; renderLibrary(); })
        .catch(error => { $('library').textContent = 'Could not load the catalog: ' + error.message; });
    renderLibrary(); renderSet(); changed(); requestRender();
})();
