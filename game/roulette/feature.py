"""One paid draw, persisted rewards, care supplies and gold tool upgrades."""
import random
from .sequence import generate
from engine.core.registry import Feature

LABELS={'special_feed':'Special feed','plant_nutrient':'Plant nutrient','medicine':'Pet medicine','gold_pickaxe':'Gold pickaxe kit','gold_rod':'Gold fishing rod kit','dog_voucher':'Dog adoption voucher','cat_voucher':'Cat adoption voucher'}
class Roulette(Feature):
    name='roulette'
    def register(self,r):
        r.owns('roulette_goods','gold_tools','roulette_last_result','roulette_queue')
        r.on('reset',self.reset)
        r.save_fields(defaults=('roulette_goods','gold_tools','roulette_last_result','roulette_queue'),migrate=self.migrate)
        r.action('prize:',self.use)
        r.shop_item('roulette',self.buy,market_price=False)
        r.shop_item('pet_medicine',self.buy_medicine)
        r.shop_item('pet_voucher',sell=self.sell_voucher,market_price=False)
        r.contribute('shop.buy_items',self.buy_rows)
        r.contribute('shop.sell_items',self.sell_rows)
        r.contribute('inventory.items',self.inventory)
        r.icon_alias('pet_voucher','tool');r.icon_alias('roulette','tool');r.icon_alias('pet_medicine','tool')
        r.state('roulette',lambda:dict(last_result=self.engine.roulette_last_result,gold_tools=self.engine.gold_tools))
    @staticmethod
    def migrate(state,fresh):
        if 'roulette_queue' not in state:
            rng=random.Random();rng.setstate(state['random_state'])
            state['roulette_queue']=[generate(fresh.config,rng) for _ in range(5)]
            state['random_state']=rng.getstate()
    def cfg(self):return self.engine.config['roulette']
    def reset(self):
        e=self.engine;e.roulette_goods={k:0 for k in LABELS};e.gold_tools={'pickaxe':False,'fishing_rod':False};e.roulette_last_result=None;e.roulette_queue=[generate(e.config) for _ in range(5)]
    def buy_rows(self):return [('roulette','draw','Prize draw',0,self.cfg()['price']),('pet_medicine','medicine','Pet medicine',self.engine.roulette_goods['medicine'],self.cfg()['medicine_price'])]
    def buy(self,item):
        e=self.engine
        if item!='draw':return None
        # A draw is always the advertised flat price; sale/discount buffs do not affect it.
        price=self.cfg()['price']
        if e.resource('coin')<price:return e.response(tts=f'Prize draw costs {price} gold.',sfx='error')
        draw=e.roulette_queue.pop(0);e.roulette_queue.append(generate(e.config))
        category=draw['category'];item=draw['item'];amount=1
        if category=='crop_seed':amount=self.cfg()['seed_quantity'];e.resources['seeds'][item]=e.resources['seeds'].get(item,0)+amount;label=e.get_seed_label(item)+' seeds'
        elif category=='fertilizer':amount=self.cfg()['fertilizer_quantity'];e.add_resource('fertilizer',amount);label='Fertilizer'
        elif category=='diamond':e.add_resource('diamond',1);label='Diamond'
        elif category=='flower_seed':
            e.registry.features['flowers'].add_seed(item,1);label=e.config['flowers']['species'][item]['label']+' seeds'
        else:e.roulette_goods[item]+=1;label=LABELS[item]
        e.add_resource('coin',-price)
        e.roulette_last_result=dict(category=category,item=item,label=label,count=amount)
        e.render();result=e.response(tts=f'{label}, {amount}.',sound_events=[dict(kind='one_shot',sound='roulette')]);result['tts_after_sound']='roulette';result['tts_delay_ms']=self.cfg().get('result_delay_ms',1000);return result
    def buy_medicine(self,item):
        if item!='medicine':return None
        e=self.engine;price=e.market_price(self.cfg()['medicine_price'],'pet_medicine','buy')
        if e.resource('coin')<price:return e.response(tts='Not enough gold.',sfx='error')
        e.add_resource('coin',-price);e.roulette_goods['medicine']+=1;e.render();return e.response(tts='Pet medicine bought.',sound_events=[dict(kind='one_shot',sound='coin')])
    def sell_rows(self):return [('pet_voucher',k,LABELS[k],self.engine.roulette_goods[k],self.cfg()['voucher_sell_price']) for k in ('dog_voucher','cat_voucher') if self.engine.roulette_goods[k]>0]
    def sell_voucher(self,item):
        e=self.engine
        if item not in ('dog_voucher','cat_voucher') or e.roulette_goods[item]<=0:return None
        # Voucher redemption value is exactly 300, independent of market offers.
        e.roulette_goods[item]-=1;e.add_resource('coin',self.cfg()['voucher_sell_price']);e.render()
        return e.response(tts=f'{LABELS[item]} sold. {self.cfg()["voucher_sell_price"]} gold.',sound_events=[dict(kind='one_shot',sound='coin')])
    def inventory(self):return [dict(id=k,label=label,count=self.engine.roulette_goods[k],kind='food',action='prize:'+k) for k,label in LABELS.items()]
    def use(self,item,obj):
        e=self.engine
        if item not in LABELS or e.roulette_goods[item]<=0:return e.response(tts='Item unavailable.')
        if item in ('medicine','special_feed'):
            e.set_page('pets');e.clear_hover();e.render();return e.response(tts='Select a pet, then Give something.')
        events=[]
        if item.endswith('_voucher'):
            return e.registry.features['pets'].begin_adoption(item.split('_')[0])
        elif item=='plant_nutrient':
            p=e.houseplant
            if p['stage'] in ('empty','withered'):return e.response(tts='Use on a living plant.')
            p.update(dry_days=0,bloom_days=0,bloom_cycles=0,nutrient_days=self.cfg()['nutrient_days']);text='Flower pot refreshed.'
        else:
            tool='pickaxe' if item=='gold_pickaxe' else 'fishing_rod'
            if not e.resources.get(tool,0):return e.response(tts='You need the tool first.')
            if e.gold_tools[tool]:return e.response(tts='Already upgraded.')
            e.gold_tools[tool]=True
            if tool=='pickaxe':e._pickaxe_hits=0
            else:e.rod_casts=0;e.rod_catches=0
            text='Gold '+tool.replace('_',' ')+'. Durability restored and improved.'
        e.roulette_goods[item]-=1;e.clear_hover();e.render();return e.response(tts=text,sound_events=events)
