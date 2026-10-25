/* Fishing: what the game page shows for this feature. */
DotdewPages.register({
    tasks: {fishing: "Follow the water sound · Press inside the lake to cast"},
    taskUpdate(state, task) {
        if (state.page === "fishing" && !state.resources?.fishing_rod) task = "Explore using the water sound · Buy a rod at the shop to cast";
        return task;
    },
    emptyHelp: {fishing: "Use stereo headphones. Move toward the water sound, then press inside the lake to cast. Press F1 for the map."},
});
