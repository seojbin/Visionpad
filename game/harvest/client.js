/* Harvest: what the game page shows for this feature. */
DotdewPages.register({
    taskUpdate(state, task) {
        if (state.page === "harvest") task = `Harvest ${state.harvest.collected_targets} / ${state.harvest.total_targets} · Collect all targets to finish`;
        return task;
    },
    hiddenObjectTypes: ["harvest_crop", "harvest_field"],
    statusLine(state) {
        const harvest = state?.harvest || {};
        return "\nHarvest: " + (harvest.collected_targets ?? 0) + " / " + (harvest.total_targets ?? 0);
    },
});
