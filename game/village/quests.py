"""Rowan's later tutorials and one saved request per game day."""
import random

# One item per submission. Rewards and gifts are granted only by stage transitions.
QUESTS = [
    ('cooking', 'food:vegetable_fritters',
     "Let's make supper together. Here are a potato and a carrot. At home, choose Vegetable fritters in the kitchen, select both ingredients, and follow the two cooking paths. Bring me the finished dish.",
     "Those fritters smell wonderful. Let's share them! You now have their time-saving effect.", None),
    ('copper', 'mineral:stone',
     "My garden wall needs a small repair. Could you bring me one stone? Buy a pickaxe from the shop's Tools counter, then visit the mine. Select a rock repeatedly to break it and collect the mineral inside.",
     "This stone will help repair my garden wall. Thank you! Here is 100 gold.", ('coin', 100)),
    ('egg', 'animal_product:egg',
     "I'd like a fried egg for breakfast. Buy a chicken from the Tools counter and visit the pasture, left of the farm. The animals graze on their own. Feed helps production, and gentle strokes help them know you. Keep feeding them so they stay. When eggs are ready, select the egg below your chicken. Bring me one.",
     "Just right for breakfast. Here are 10 portions of animal feed for your chicken.", ('animal_feed', 10)),
    ('sardine', 'fish:low',
     "I'm cooking supper and need a sardine, bass, or mackerel. Any one will do. Buy a fishing rod from the Tools counter, then visit the lake. Move your hand and listen for the water. Select a spot to fish. Bring me one of those fish when you catch it.",
     "This fish will make a fine supper. Here is 100 gold.", ('coin', 100)),
    ('wool', 'animal_product:wool',
     "My coat is wearing thin. Could you bring me one bundle of wool? Buy a sheep from the Tools counter and visit it in the pasture. Feed it and gently stroke it as its fleece grows. When wool is ready, choose Shear wool and sweep across the fleece to collect it.",
     "Now I can patch my coat. Here are 20 portions of animal feed. There's always something to do around here. Come back for a daily request.", ('animal_feed', 20)),
]


class RowanQuests:
    def __init__(self, village):
        self.v = village
        self.e = village.engine

    def catalog(self):
        """Normal obtainable products, independent of current stock or market bonuses."""
        e = self.e
        result = {}
        def add(kind, key, label, grade, price, bucket):
            result[kind+':'+key] = dict(kind=kind, key=key, label=label, grade=grade,
                                       price=int(price), bucket=bucket)
        for key, cfg in e.config['seeds'].items():
            add('crop', key, e.get_seed_label(key), 'low', cfg['crop_price'], e.resources['crops'])
        for key, cfg in e.fishing_config()['fish'].items():
            add('fish', key, cfg['label'], cfg['grade'], e.get_fish_price(key), e.resources['fish'])
        for key, grade in [('stone','low'), ('copper','medium'), ('iron','high')]:
            add('mineral', key, e.MINERAL_LABELS[key], grade, e.get_mineral_price(key), e.resources)
        for cfg in e.config['pasture']['animals'].values():
            key = cfg['product']
            add('animal_product', key, key.title(), 'low' if key == 'egg' else 'medium', cfg['price'], e.pasture_goods)
        for key, cfg in e.config['recipes'].items():
            if cfg.get('quest_only') or (cfg.get('seafood') and not cfg.get('fish_grade')):
                continue
            grade = 'high' if cfg.get('seafood') or key == 'fried_egg' else 'medium'
            price = e.registry.features['cooking'].food_sell_price(key)
            add('food', key, e.get_recipe_label(key), grade, price, e.resources['foods'])
        return result

    def refresh_daily(self):
        e = self.e
        if e.rowan_stage != 'all_done': return
        if e.rowan_daily.get('day') != e.day:
            e.rowan_daily = dict(day=e.day, item=random.choice(list(self.catalog())), completed=False)

    def available(self):
        return self.e.rowan_stage != 'all_done' or self.e.rowan_daily.get('day') != self.e.day or not self.e.rowan_daily.get('completed')

    def request(self):
        stage = self.e.rowan_stage
        if stage == 'all_done':
            self.refresh_daily()
            return None if self.e.rowan_daily.get('completed') else self.e.rowan_daily.get('item')
        return next((item for name,item,*_ in QUESTS if stage == name+'_requested'), None)

    def accepted_items(self):
        token = self.request()
        if token == 'fish:low' and self.e.rowan_stage == 'sardine_requested':
            return [key for key, item in self.catalog().items()
                    if item['kind'] == 'fish' and item['grade'] == 'low']
        return [token] if token else []

    def talk(self):
        e, v = self.e, self.v
        if e.rowan_stage == 'done':  # Existing saves finished the farming tutorial here.
            e.rowan_stage = 'cooking_requested'
            for key in ('potato', 'carrot'): e.add_resource('crops', 1, item=key)
            return v.show_rowan(QUESTS[0][2], include_reaction=False)
        for i, (name, item, intro, thanks, reward) in enumerate(QUESTS):
            if e.rowan_stage == name+'_complete':
                if i+1 < len(QUESTS):
                    nxt = QUESTS[i+1]
                    e.rowan_stage = nxt[0]+'_requested'
                    return v.show_rowan(nxt[2], include_reaction=False)
            if e.rowan_stage == name+'_requested':
                label = ('of these fish: ' + ', '.join(self.catalog()[key]['label'] for key in self.accepted_items())
                         if item == 'fish:low' else self.catalog()[item]['label'])
                return v.show_rowan(f'Please bring me one {label}. Select it here to hand it over. You can leave and come back anytime.', 'rowan_submit', include_reaction=False)
        if e.rowan_stage == 'all_done':
            self.refresh_daily()
            if e.rowan_daily.get('completed'):
                return v.show_rowan("Thank you for today's help. I'll have another request tomorrow. " + e.rowan_advice('pasture'), include_reaction=False)
            item = self.catalog()[e.rowan_daily['item']]
            reward = int(item['price'] * e.config['rowan']['daily_quests']['reward_multiplier'])
            return v.show_rowan(f"For today's supplies, could you bring me one {item['label']}? I'll pay {reward} gold. Choose it here when you have it. The request changes each morning.", 'rowan_submit', include_reaction=False)
        return None

    def objects(self):
        e = self.e
        catalog = self.catalog()
        result = []
        for token in self.accepted_items():
            item = catalog.get(token)
            if not item: continue
            count = item['bucket'].get(item['key'], 0)
            if count < 1: continue
            result.append(dict(id='rowan_item_'+item['key'], type='ingredient', ingredient_id=item['key'],
                         recipe_id=item['key'] if item['kind']=='food' else None,
                         item_kind=item['kind'], x=8+14*len(result),y=6,width=12,height=9,hit_width=12,hit_height=9,
                         label=item['label'],count=count,required_count=1,selected=False,
                         tts=f"{item['label']}. Stock {count}. Give one to Rowan.",action='rowan_submit:'+token))
        return result

    def submit(self, token):
        e, v = self.e, self.v
        if token not in self.accepted_items(): return e.response(tts='That is not the requested item.')
        item = self.catalog().get(token)
        if not item or item['bucket'].get(item['key'],0) < 1:
            return e.response(tts='You do not have the requested item.')
        item['bucket'][item['key']] -= 1
        events = []
        if e.rowan_stage == 'all_done':
            e.rowan_daily['completed'] = True
            gold = int(item['price'] * e.config['rowan']['daily_quests']['reward_multiplier'])
            e.add_resource('coin', gold)
            text = f'Thank you for the {item["label"]}. Here is {gold} gold.'
            prize = self.prize(item['grade'])
            if prize: text += ' A little extra for your help: '+prize+'.'
            events = [{'kind':'one_shot','sound':'coin'}]
        else:
            quest = next(q for q in QUESTS if q[0]+'_requested' == e.rowan_stage)
            name, _, _, text, reward = quest
            e.rowan_stage = 'all_done' if name == 'wool' else name+'_complete'
            if name == 'cooking':
                e.start_food_effect('vegetable_fritters', e.get_recipe_config('vegetable_fritters'))
                text += ' '+e.buff_text()+'.'
            if reward:
                kind, amount = reward
                if kind == 'coin':
                    e.add_resource('coin',amount); events = [{'kind':'one_shot','sound':'coin'}]
                else: e.pasture_goods[kind] = e.pasture_goods.get(kind,0)+amount
        return v.show_rowan(text, events=events, include_reaction=False)

    def prize(self, grade):
        e = self.e
        outcome = random.choices(['none','low','medium','high','soup','diamond'],
                                 weights=e.config['rowan']['daily_quests']['prize_weights'][grade], k=1)[0]
        if outcome == 'none': return None
        if outcome == 'diamond':
            e.add_resource('diamond',1); return 'one diamond'
        if outcome == 'soup':
            key = random.choice(['rowan_special_red','rowan_special_yellow','rowan_special_fish'])
            e.resources['foods'][key] = e.resources['foods'].get(key,0)+1
            return e.get_recipe_label(key)
        item = random.choice([v for v in self.catalog().values() if v['grade']==outcome])
        item['bucket'][item['key']] = item['bucket'].get(item['key'],0)+1
        return 'one '+item['label']
