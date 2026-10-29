"""Public, detached visual data. Never changes gameplay or exposes hidden rolls."""
import copy


# Key order of the companion snapshot before features added their own keys; new keys follow.
SPECTATOR_KEY_ORDER = ('schema', 'objects', 'plots', 'routes', 'rocks', 'care_targets', 'harvest_targets', 'path')


def spectator_snapshot(engine, objects):
    fields = ('grid_row', 'grid_column', 'grid_slot', 'id', 'type', 'x', 'y', 'width', 'height', 'label', 'selected',
              'resource_kind', 'recipe_id', 'seed_id', 'ingredient_id', 'choice',
              'item_kind', 'shop_kind', 'item_id', 'count', 'price', 'direction',
              'research_kind', 'required_count', 'display_quantities', 'quest_available')
    public_objects = [{k: copy.deepcopy(o[k]) for k in fields if k in o}
                      for o in objects if o.get('type') not in ('arrow', 'route', 'home_hitbox', 'town_hitbox', 'shop_hitbox')]
    for idx, public in enumerate([o for o in public_objects if o.get('type') == 'plot']):
        col, row = idx % 3, idx // 3
        public.update(x=8 + col * 15, y=6 + row * 12, width=12, height=8)
    for public in public_objects:
        kind = public.get('type')
        recipe_id = public.get('recipe_id') or (public.get('item_id') if public.get('shop_kind') == 'food' else None)
        if recipe_id:
            recipe = engine.get_recipe_config(recipe_id)
            if recipe:
                public['effect_description'] = engine.recipe_effect_text(recipe)
        if kind == 'seed':
            public['count'] = int(engine.resources['seeds'].get(public.get('seed_id'), 0))
        elif kind == 'recipe':
            ingredients = engine.get_recipe_config(public.get('recipe_id')).get('ingredients', {})
            public['display_quantities'] = [dict(item=key, label=engine.get_seed_label(key),
                required=int(count), owned=int((engine.pasture_goods if key == 'egg' else engine.resources['crops']).get(key, 0))) for key, count in ingredients.items()]
            if recipe.get('seafood'):
                public['display_quantities'].append(dict(item=recipe.get('allowed_fish',['salmon'])[0],label='Fish',required=recipe.get('fish_required',1),owned=sum(engine.resources.get('fish',{}).get(k,0) for k in recipe.get('allowed_fish',[]))))
        elif public.get('id') == 'plot_detail_fertilizer':
            public['count'] = int(engine.resources.get('fertilizer', 0))
    snapshot = {
        'schema': 1, 'objects': public_objects,
        'routes': [{k: o[k] for k in ('x1', 'y1', 'x2', 'y2')}
                   for o in objects if o.get('type') == 'route'],
    }
    for key, provider in engine.registry.spectator_providers.items():
        if key in snapshot:
            raise ValueError(f"Spectator key {key!r} is provided by both core and a feature")
        snapshot[key] = provider(objects)
    ordered = {key: snapshot.pop(key) for key in SPECTATOR_KEY_ORDER if key in snapshot}
    ordered.update(snapshot)
    return ordered
