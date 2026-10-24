/* Feature hooks for the game page. Each web/features/<name>/client.js registers what the page
   shows for its pages; web/core/game.js asks here. Hooks run in script load order. */
const DotdewPages = {
    taskTexts: {},
    taskUpdates: [],
    emptyHelp: {},
    hiddenObjectTypes: new Set(),
    statusLines: [],
    timers: [],
    // Text under the scene title when no feature update applies.
    task(state, fallback) {
        let task = this.taskTexts[state.page] || fallback;
        for (const update of this.taskUpdates) task = update(state, task);
        return task;
    },
    register({tasks = {}, taskUpdate, emptyHelp = {}, hiddenObjectTypes = [], statusLine} = {}) {
        Object.assign(this.taskTexts, tasks);
        if (taskUpdate) this.taskUpdates.push(taskUpdate);
        Object.assign(this.emptyHelp, emptyHelp);
        hiddenObjectTypes.forEach(type => this.hiddenObjectTypes.add(type));
        if (statusLine) this.statusLines.push(statusLine);
    },
    // Repeating page work; started by game.js once the page is set up.
    every(ms, run) {
        this.timers.push([ms, run]);
    },
    startTimers() {
        for (const [ms, run] of this.timers) setInterval(run, ms);
    },
};
