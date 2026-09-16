"""Public, detached visual data. Never changes gameplay or exposes hidden rolls."""
import copy
import time


def spectator_snapshot(engine, objects):
    now = time.monotonic()
    fields = ('id', 'type', 'x', 'y', 'width', 'height', 'label', 'selected',
              'resource_kind', 'recipe_id', 'seed_id', 'ingredient_id', 'choice',
              'item_kind', 'shop_kind', 'item_id', 'count', 'price', 'direction')
    public_objects = [{k: copy.deepcopy(o[k]) for k in fields if k in o}
                      for o in objects if o.get('type') not in ('arrow', 'route')]
    plots = []
    for definition in engine.get_unlocked_plot_defs():
        state = engine.farm_plots[definition['id']]
        seed = engine.config.get('seeds', {}).get(state.get('seed_id'), {})
        plots.append(dict(id=definition['id'], **copy.deepcopy(state),
                          growth_days=seed.get('growth_days', 1)))

    def targets(items, collected, deadlines):
        return [dict(id=t['id'], x=t['x'], y=t['y'],
                     collected=t['id'] in collected,
                     visible=t['id'] not in collected or deadlines.get(t['id'], 0) > now)
                for t in items]

    return {
        'schema': 1, 'objects': public_objects, 'plots': plots,
        'routes': [{k: o[k] for k in ('x1', 'y1', 'x2', 'y2')}
                   for o in objects if o.get('type') == 'route'],
        'rocks': [{k: r[k] for k in ('id', 'left', 'top', 'width', 'height', 'hits')}
                  for r in engine.mine_rocks],
        'care_targets': targets(engine.care_targets, engine.care_collected_ids, engine.care_visible_until),
        'harvest_targets': targets(engine.harvest_targets, engine.harvest_collected_ids, {}),
        'path': [dict(x=p[0], y=p[1], passed=i < engine.cooking_progress_index,
                      visible=i >= engine.cooking_progress_index or engine.cooking_visible_until.get(i, 0) > now)
                 for i, p in enumerate(engine.cooking_path_samples)],
    }
