/* Cooking: what the game page shows for this feature. */
DotdewPages.register({
    tasks: {ingredient_select: "Select all ingredients to start cooking", cooking: "Start at the filled square and follow the line"},
    taskUpdate(state, task) {
        if (state.page === "cooking") task = `${state.cooking.stage_index+1}/${state.cooking.stage_count} ${state.cooking.stage_label} · ${Math.round(100*state.cooking.progress/Math.max(1,state.cooking.total))}% · Follow the line`;
        if (state.page === "cooking" && state.cooking.resume_point) task += " · Continue from the filled square";
        return task;
    },
    emptyHelp: {cooking: "Move to the filled square and follow the line. No press needed. Press F1 to open the map."},
    statusLine(state) {
        const cooking = state?.cooking || {};
        return "\nCooking: " + (cooking.progress ?? 0) + " / " + (cooking.total ?? 0);
    },
});
