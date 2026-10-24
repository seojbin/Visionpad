/* Farming: what the game page shows for this feature. */
DotdewPages.register({
    tasks: {farm: "Choose a plot to manage your crops"},
    taskUpdate(state, task) {
        if (state.page === "plot_detail") task = (state.objects || []).find(o=>o.type === "plot_detail_field")?.description || task;
        if (state.care?.mode) task = `Coverage ${state.care.collected_targets} / ${state.care.total_targets} · Cover the targets to finish`;
        return task;
    },
    hiddenObjectTypes: ["care_target", "care_field"],
    statusLine(state) {
        const care = state?.care || {};
        return "\nField Care: " + (care.mode || "None") + " " + (care.collected_targets ?? 0) + " / " + (care.total_targets ?? 0);
    },
});
