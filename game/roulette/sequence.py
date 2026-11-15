"""Five future draws, stored with the game's normal save slot."""
import random

def generate(config, rng=random):
    weights=config['roulette']['weights']
    category=rng.choices(list(weights),weights=list(weights.values()),k=1)[0]
    pools={'crop_seed':list(config['seeds']), 'flower_seed':list(config['flowers']['species']),
           'pet_voucher':['dog_voucher','cat_voucher'], 'gold_tool':['gold_pickaxe','gold_rod']}
    item=rng.choice(pools[category]) if category in pools else category
    return dict(category=category,item=item)
