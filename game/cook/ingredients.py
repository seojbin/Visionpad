def bucket(engine, item):
    return engine.pasture_goods if item == 'egg' else engine.resources['crops']

def label(engine, item):
    return 'Egg' if item == 'egg' else engine.get_seed_label(item)
