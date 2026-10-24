/* Inventory: what the game page shows for this feature. */
DotdewPages.register({
    tasks: {inventory: "Select a dish to use its effect"},
    taskUpdate(state, task) {
        if (state.page === "inventory") task = `Inventory ${state.inventory.page}/${state.inventory.pages} · Owned items only`;
        return task;
    },
});
