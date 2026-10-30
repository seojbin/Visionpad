"""Free-range animals, daily production and persistent collection interactions."""
import random
import math
import time
from engine.core.registry import Feature

# 1. UI 아이콘용 패턴 (프레임 안에 쏙 들어가도록 원래의 작은 사이즈 유지)
ICON_PATTERNS = {
    'chicken': ('0001100','0011111','1111100','0111100','0010100'),
    'sheep': ('0111100','1111111','1111111','0111110','0100100'),
    'shorn': ('0000000','0111100','1111111','0111110','0100100'),
}
CARE_PATTERNS = {
    'collect': ('0011100','0111110','0111110','0111110','0011100'),
    'shear': ('1100011','0110110','0011100','0110110','1100011'),
}

# 2. 목장 씬(Scene) 패턴 (양을 닭보다 크게 표현하고 다리 연결부 보강)
SCENE_PATTERNS = {
    'chicken': (
        '00001100',
        '00011010', # 눈, 부리
        '01111111',
        '11111100',
        '01101000',
        '00111000'  # 다리가 떨어져 보이지 않게 결합부 추가
    ),
    'sheep': (
        '0000011111100000',
        '0011111111111100',
        '0111111111111110',
        '1011111111111110',
        '1111111111111110',
        '0111111111111110',
        '0011111111111100',
        '0011110000111100', # 다리 연결 픽셀을 두껍게 보강하여 떨어짐 방지
        '0001100000011000',
        '0001100000011000'
    ),
    'shorn': (
        '0000000000000000',
        '0000000000000000',
        '0000111111110000',
        '0011111111111000',
        '0101111111111100',
        '0011111111111000',
        '0001111111111000',
        '0000111001110000', # 다리 연결 보강
        '0000110000110000',
        '0000110000110000'
    ),
}

# 3. 디테일(Detail) 뷰 패턴 (1:1 해상도로 크고 정밀하게 묘사, 다리 연결부 보강)
DETAIL_PATTERNS = {
    'chicken': (
        '000000000000000000',
        '000000000111100000',
        '000000001111110000',
        '000000011111011000',
        '000000111111111100',
        '000000111111111000',
        '000001111111111100',
        '000011110000111100',
        '000111101111011110',
        '001111011111101110',
        '011111011111101110',
        '111111100000011110',
        '011111111111111100',
        '001111111111111000',
        '000111111111110000',
        '000011100001110000', # 다리 연결 픽셀 보강
        '000001100001100000',
        '000001100001100000',
        '000011100011100000'
    ),
    'sheep': (
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000111111111111110000000000',
        '00000011111111111111111110000000',
        '00000111111111111111111111100000',
        '01111111111111111111111111110000',
        '11101111111111111111111111111000',
        '11111111111111111111111111111000',
        '11111111111111111111111111111000',
        '11111111111111111111111111111000',
        '01111111111111111111111111111000',
        '00111111111111111111111111110000',
        '00000111111111111111111111000000',
        '00000111111111111111111100000000',
        '00000111111100000111111100000000', # 다리 연결 보강
        '00000011111000000011111000000000',
        '00000011111000000011111000000000',
        '00000011111000000011111000000000',
        '00000011111000000011111000000000',
        '00000001110000000001110000000000'
    ),
    'shorn': (
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000000000000000000000000000000',
        '00000111111111111111111100000000',
        '01111111111111111111111110000000',
        '11101111111111111111111111000000',
        '11111111111111111111111111100000',
        '11111111111111111111111111100000',
        '01111111111111111111111111000000',
        '00011111111111111111111110000000',
        '00001111111111111111111100000000',
        '00000111111111111111111100000000',
        '00000111111100000111111100000000',
        '00000111111100000111111100000000', # 다리 연결 보강
        '00000011111000000011111000000000',
        '00000011111000000011111000000000',
        '00000011111000000011111000000000',
        '00000011111000000011111000000000',
        '00000001110000000001110000000000'
    )
}

class Pasture(Feature):
    name = 'pasture'

    def register(self, reg):
        reg.owns('pasture_animals', 'pasture_goods', 'pasture_selected', 'pasture_sheared',
                 'pasture_move_at', 'pasture_stroke', 'pasture_morning_id')
        reg.on('reset', self.reset)
        reg.on('end_of_day', self.advance)
        reg.on('start_of_day', self.morning)
        reg.on('before_state', self.move)
        reg.on('before_navigation', self.stop)
        reg.on('release_drag', self.stop)
        reg.on('leave_activity', self.stop)
        reg.save_fields(defaults=('pasture_animals','pasture_goods','pasture_selected','pasture_sheared','pasture_morning_id'),
                        transient={'pasture_move_at':None,'pasture_stroke':None}, migrate=self.migrate)
        reg.page('pasture', name='Pasture', objects=self.objects, scene=self.draw_scene,
                 live=True, arrival=self.arrival, detail=lambda:self.arrival()+' Animals graze freely. Select a chicken or sheep to care for it.')
        reg.page('animal_detail', name='Animal care', objects=self.detail_objects, scene=self.draw_detail, live=True, pointer_move=self.pet_motion, pointer_drag=self.pet_motion,
                 detail=lambda:'Pet or feed your animal. Collect eggs below the chicken, or select Shear when wool is ready.')
        reg.page('shearing', name='Shearing', objects=lambda:[self.engine.back_arrow('shear_back','Animal care','animal:cancel')], scene=self.draw_wool,
                 pointer_move=self.shear, pointer_drag=self.shear,
                 detail=lambda:'Move over the wool to shear it. No click is needed.')
        reg.page('egg_collect', name='Collect eggs', objects=self.egg_objects, scene=self.draw_detail,
                 detail=lambda:'Select the egg below the chicken to collect it.')
        reg.action('animal:', self.action)
        reg.icon('animal_care', pattern=lambda o:self.engine.icons.PATTERNS['tool'] if o['care_kind']=='feed' else CARE_PATTERNS[o['care_kind']])

        # UI 아이콘은 분리된 ICON_PATTERNS 사용
        reg.icon('animal_icon', pattern=lambda o:ICON_PATTERNS[o['animal']])

        reg.renderer('animal_hitbox', lambda o:None)
        reg.renderer('egg_target', lambda o:None)
        reg.object_tts('animal_care', lambda o:o['label'])
        reg.object_tts('egg_target', lambda o:'Eggs ready.')
        reg.object_tts('animal_icon', lambda o:o['short'])
        reg.object_tts('animal_hitbox', lambda o:o['short'])
        reg.state('pasture', self.public)
        reg.contribute('inventory.items', self.inventory)
        reg.contribute('shop.buy_items', self.buy_rows)
        reg.contribute('shop.sell_items', self.sell_rows)
        reg.icon_alias('animal_feed', 'tool')
        reg.icon_alias('animal_product', 'material')
        reg.icon_alias('animal', 'tool')
        reg.shop_item('animal', self.buy_animal)
        reg.shop_item('animal_feed', self.buy_feed)
        reg.shop_item('animal_product', lambda _:None, sell=self.sell_product)

    @staticmethod
    def migrate(state, fresh):
        if 'pasture_animals' not in state:
            import copy
            state['pasture_animals']=copy.deepcopy(fresh.pasture_animals)
            for animal in state['pasture_animals'].values():
                animal['last_feed_day']=state.get('day',fresh.day)
        goods={**fresh.pasture_goods,**state.get('pasture_goods',{})}
        goods['animal_feed']=goods.get('animal_feed',0)+goods.pop('chicken_feed',0)+goods.pop('sheep_feed',0)
        if goods:state['pasture_goods']=goods
        animals=state.get('pasture_animals',{})
        chicken=animals.get('chicken',{})
        if chicken.get('ready'):chicken['quantity']=min(3,max(1,chicken.get('quantity',1)))
        sheep=animals.get('sheep',{})
        if sheep and sheep.get('shear_format')!='dots_v1':
            tiles=Pasture.wool_tiles();erased=set()
            for i in state.get('pasture_sheared',[]):
                if 0<=i<len(tiles):
                    tx,ty=tiles[i]
                    for y in range(ty-2,ty+3):
                        for x in range(tx-2,tx+3):
                            if (x%7 or y%5):erased.add(y*fresh.dotpad.width+x)
            state['pasture_sheared']=sorted(erased)
            sheep['shear_format']='dots_v1'
            if sheep.get('ready'):sheep['quantity']=max(2,min(5,sheep.get('quantity',2)))


    def arrival(self):
        missing=[k.title() for k,a in self.engine.pasture_animals.items() if a.get('escaped') and not a['owned']]
        return 'Pasture.'+(' '+ ' and '.join(missing)+' escaped.' if missing else '')

    def breathe(self):
        return getattr(self,'_breath_offset',0)

    def cfg(self): return self.engine.config['pasture']
    def reset(self):
        e=self.engine
        self._pet_contact=None; self._pet_seconds=0.0; self._motion={};self._breath_offset=0
        e.pasture_animals={kind:dict(owned=False, friendship=0, remaining=cfg['days'],ready=False,
            ready_day=None, quantity=0, next_boost=False, last_feed_day=e.day, fed_day=0,pet_day=0,
            x=16 if kind=='chicken' else 43,y=25,step=0,facing_left=False,escaped=False,shear_format='dots_v1') for kind,cfg in self.cfg()['animals'].items()}
        e.pasture_goods={'egg':0,'wool':0,'animal_feed':0}
        e.pasture_selected='chicken';e.pasture_sheared=[];e.pasture_move_at=None;e.pasture_stroke=None;e.pasture_morning_id=0
    def stop(self):
        self.engine.pasture_stroke=None
        self._pet_contact=None
    def morning(self): self.engine.pasture_morning_id += 1
    def level(self,a):return min(2,max(0,a['friendship']//100))
    def status(self,a):return ('Indifferent','Recognizes you','Seems happy')[self.level(a)]
    def cycle_days(self,k):
        cfg=self.cfg()['animals'][k]
        days=cfg.get('wait_days',[cfg['days']])
        weights=cfg.get('wait_weights',[1]*len(days))
        return random.choices(days,weights=weights,k=1)[0]

    def production_quantity(self,k):
        cfg=self.cfg()['animals'][k]
        if k=='chicken':
            return min(cfg.get('ready_capacity',3),2 if random.random()<cfg.get('double_egg_chance',.2) else 1)
        return random.randint(*cfg.get('yield_range',[2,5]))

    def short(self,k):
        a=self.engine.pasture_animals[k]; cfg=self.cfg()['animals'][k]
        return f"{k.title()}. {self.status(a)}."+(f" {'Eggs' if k=='chicken' else 'Wool'} ready." if a['ready'] else '')
    def public(self):
        e=self.engine
        return dict(selected=e.pasture_selected,morning_id=e.pasture_morning_id,
            animals={k:dict(owned=a['owned'],status=self.status(a),ready=a['ready'],x=a['x'],y=a['y'],
                            fed=a['fed_day']==e.day,petted=a['pet_day']==e.day,facing_left=a.get('facing_left',False)) for k,a in e.pasture_animals.items()},
            shear_dot_width=e.dotpad.width,breath_offset=self.breathe(),sheared=list(e.pasture_sheared),brush_region=self.brush_region(),audio=self.cfg()['audio'])
    def advance(self):
        e=self.engine; tomorrow=e.day+1; c=self.cfg()
        notes=[]
        for k,a in e.pasture_animals.items():
            if not a['owned']:continue
            days=tomorrow-a['last_feed_day']
            grace=c['escape_grace_days'][self.level(a)]
            chance=min(1.0,max(0,days-grace)*c['escape_increment'])
            if chance > 0 and random.random() < chance:
                a.update(owned=False,ready=False,quantity=0,ready_day=None,next_boost=False,escaped=True)
                if k=='sheep':e.pasture_sheared=[]
                notes.append(k.title()+' escaped from the pasture.')
                continue
            if tomorrow-a['last_feed_day']>c['feed_grace_days']: a['friendship']-=c['unfed_penalty']
            if a['ready'] and tomorrow-a['ready_day']>c['collection_grace_days']: a['friendship']-=c['uncollected_penalty']
            a['friendship']=max(0,a['friendship'])
            capacity=c['animals'][k].get('ready_capacity',3)
            if not a['ready'] or (k=='chicken' and a['quantity']<capacity):
                a['remaining']=max(0,a['remaining']-1)
                if a['remaining']==0:
                    if k=='chicken':
                        was_ready=a['ready']
                        a['quantity']=min(capacity,(a['quantity'] if was_ready else 0)+self.production_quantity(k))
                        a['ready']=True
                        if not was_ready:a['ready_day']=tomorrow
                        a['remaining']=max(1,self.cycle_days(k)-int(a['next_boost'])) if a['quantity']<capacity else 0
                        a['next_boost']=False
                    else:
                        a.update(ready=True,ready_day=tomorrow,quantity=self.production_quantity(k))
        return ' '.join(notes) if notes else None
    def move(self):
        e=self.engine; now=time.monotonic();c=self.cfg()
        if not e.paused and not e.day_ended and e.sleep_until is None:
            self._breath_offset=-(int(now/c.get('breath_seconds',1.5))%2)
        if e.current_page!='pasture' or e.paused or e.day_ended or e.sleep_until is not None:
            e.pasture_move_at=now;self._motion={};return
        if e.pasture_move_at is None:
            self._motion={};e.pasture_move_at=now
        offsets=[(0,0),(3,0),(3,3),(0,4),(-3,2),(-3,0)]
        bounds=c.get('move_interval_seconds',[c.get('move_seconds',4)-1,c.get('move_seconds',4)+1])
        flips=c.get('flip_interval_multipliers',[3,5])
        for k,a in e.pasture_animals.items():
            if not a['owned']:
                self._motion.pop(k,None);continue
            clock=self._motion.get(k)
            if clock is None:
                interval=random.uniform(*bounds)
                self._motion[k]=dict(move_at=now+interval,flip_at=now+interval*random.uniform(*flips))
                continue
            if now>=clock['move_at']:
                a['step']=(a['step']+1)%len(offsets);dx,dy=offsets[a['step']]
                a['x']=(16 if k=='chicken' else 43)+dx;a['y']=25+dy
                clock['move_at']=now+random.uniform(*bounds);e.pasture_move_at=now
            if now>=clock['flip_at']:
                a['facing_left']=not a.get('facing_left',False)
                clock['flip_at']=now+random.uniform(*bounds)*random.uniform(*flips)
    def back(self):return self.engine.back_arrow('animal_back','Pasture','return_scene')

    def objects(self):
        e=self.engine; result=[]
        for i,(k,a) in enumerate(e.pasture_animals.items()):
            if not a['owned']:continue
            desc=self.short(k)+' Select to pet, feed or collect.'

            # UI 아이콘은 점선 프레임 안에 맞도록 다시 작은 사이즈(12x10)로 롤백
            result.append(dict(id='animal_'+k,type='animal_icon',animal=k,x=8+14*i,y=6,width=12,height=10,hit_width=10,hit_height=8,
                label=k.title(),short=self.short(k),tts=desc,action='animal:open:'+k))

            # 씬 히트박스는 씬 패턴(SCENE_PATTERNS)의 커진 사이즈에 맞게 유지
            w = 16 if k == 'sheep' else 12
            h = 10 if k == 'sheep' else 10
            hw = 18 if k == 'sheep' else 12
            hh = 12 if k == 'sheep' else 10

            result.append(dict(id='pasture_'+k,type='animal_hitbox',skip_grid=True,x=a['x'],y=a['y']+self.breathe(),width=w,height=h,
                hit_width=hw,hit_height=hh,label=k.title(),short=self.short(k),tts=desc,action='animal:open:'+k))
        result.append(dict(id='pasture_exit',type='arrow',direction='right',x=56,y=5,label='Farm',action='travel:farm'))
        return result

    def brush_region(self):
        # Match the uploaded detail drawing, excluding the egg collection area.
        return dict(x=22,y=12+self.breathe(),width=18,height=19) if self.engine.pasture_selected=='chicken' else dict(x=14,y=12+self.breathe(),width=32,height=19)

    def pet_motion(self,x,y):
        e=self.engine; a=e.pasture_animals[e.pasture_selected]; now=time.monotonic()
        region=self.brush_region()
        inside=(region['x']<=x<region['x']+region['width'] and region['y']<=y<region['y']+region['height'])
        if e.paused or e.day_ended or e.sleep_until is not None or not a['owned'] or not inside:
            self._pet_contact=None
            return None
        previous=self._pet_contact
        self._pet_contact=(now,x,y)
        if previous is not None:
            elapsed=now-previous[0]
            distance=math.hypot(x-previous[1],y-previous[2])
            if 0<elapsed<=self.cfg().get('pet_contact_gap_seconds',0.5) and distance>0.05:
                self._pet_seconds+=elapsed
                if a['pet_day']!=e.day and self._pet_seconds>=self.cfg().get('pet_seconds',3):
                    a['friendship']=min(299,a['friendship']+self.cfg()['pet_points'])
                    a['pet_day']=e.day
                    self._pet_seconds=0.0
                    e.last_pointer=(x,y)
                    return e.response(sound_events=self.sound(e.pasture_selected))
        # Normal hover handling still runs; no progress or completion TTS.
        return None

    def detail_objects(self):
        e=self.engine;k=e.pasture_selected;a=e.pasture_animals[k]
        buttons=[('feed','Feed','feed')]
        buttons.append(('shear','Shear wool','shear') if k=='sheep' else ('gather','Collect eggs','collect'))
        result=[dict(id='animal_'+action,type='animal_care',care_kind=icon,x=8+14*i,y=6,width=12,height=10,hit_width=12,hit_height=10,
                     label=label,tts=label+'. '+('Once each day.' if action in ('pet','feed') else 'Select the egg below the chicken.' if action=='gather' else 'Move over the wool to collect it.'),action='animal:'+action)
                for i,(action,label,icon) in enumerate(buttons)]
        result.append(dict(id='animal_body',type='animal_hitbox',skip_grid=True,x=30,y=21+self.breathe(),width=36,height=20,hit_width=36,hit_height=20,
                           label=k.title(),short=self.short(k),tts=self.short(k)+' Animals graze without feed. Feed can shorten production.',action='animal:shear' if k=='sheep' else 'animal:gather'))
        if k=='chicken' and a['ready']:
            result.append(dict(id='animal_egg',type='egg_target',skip_grid=True,x=30,y=35,width=12,height=7,hit_width=12,hit_height=7,
                               label='Egg',tts='Eggs ready. Select to collect.',action='animal:collect'))
        return result+[self.back()]
    def egg_objects(self):
        return [dict(id='animal_egg',type='egg_target',skip_grid=True,x=30,y=35,width=12,height=7,hit_width=12,hit_height=7,
                     label='Egg',tts='Eggs ready. Select to collect.',action='animal:collect'),
                self.engine.back_arrow('egg_back','Animal care','animal:cancel')]

    def sound(self,k):return [{'kind':'one_shot','sound':k+'_main'}]
    def action(self,arg,obj):
        e=self.engine
        if e.paused or e.sleep_until is not None:return e.response()
        if arg.startswith('open:'):
            k=arg.split(':')[1]
            if k not in e.pasture_animals or not e.pasture_animals[k]['owned'] or e.current_location!='pasture':return e.response()
            self._pet_contact=None;self._pet_seconds=0.0
            e.pasture_selected=k;e.set_page('animal_detail');e.clear_hover();e.render()
            return e.response(tts=self.short(k),sound_events=self.sound(k))
        if arg=='cancel' and e.current_page in ('egg_collect','shearing'):
            e.set_page('animal_detail');e.pasture_stroke=None;e.clear_hover();e.render();return e.response(tts='Animal care.')
        if e.current_page not in ('animal_detail','egg_collect'):return e.response()
        k=e.pasture_selected;a=e.pasture_animals[k];c=self.cfg()
        if not a['owned']:return e.return_to_scene()
        if arg=='gather' and k=='chicken':
            if not a['ready']:return e.response(tts='No eggs ready.')
            e.set_page('egg_collect');e.clear_hover();e.render();return e.response(tts='Select the egg below the chicken.')
        if arg=='feed':
            key='animal_feed'
            if a['fed_day']==e.day:return e.response(tts='Already fed today.')
            if e.pasture_goods[key]<=0:return e.response(tts='No feed. Buy feed at the shop.')
            e.pasture_goods[key]-=1;a['fed_day']=e.day;a['last_feed_day']=e.day
            if a['ready'] or a['remaining']<=1:a['next_boost']=True
            else:a['remaining']-=1
            text=k.title()+'. Fed.'
        elif arg=='collect' and k=='chicken':return self.collect()
        elif arg=='shear' and k=='sheep':
            if not a['ready']:return e.response(tts='Wool is not ready.')
            e.set_page('shearing');e.pasture_stroke=None;e.clear_hover();e.render()
            return e.response(tts='Shear wool. Move your hand over the wool.', sound_events=self.sound(k))
        else:return e.response()
        e.render();return e.response(tts=text,sound_events=[{'kind':'one_shot','sound':'feed'}]+self.sound(k))
    def collect(self):
        e=self.engine;k=e.pasture_selected;a=e.pasture_animals[k]
        if not a['owned'] or not a['ready']:return e.response(tts='Not ready.')
        cfg=self.cfg()['animals'][k]
        quantity=min(3,max(1,a['quantity'])) if k=='chicken' else max(cfg.get('yield_range',[2,5])[0],min(cfg.get('yield_range',[2,5])[1],a['quantity']))
        level = min(2, max(0, e.research_levels.get('animal_shelter', 0)))
        chances = e.config.get('research', {}).get('animal_shelter', {}).get('bonus_chances', [0.15, 0.30])
        if level:
            quantity += sum(random.random() < chances[level - 1] for _ in range(quantity))
        e.pasture_goods[cfg['product']]+=quantity
        a['friendship']=min(299,a['friendship']+self.cfg()['collect_points'])
        a.update(ready=False,ready_day=None,quantity=0,remaining=max(1,self.cycle_days(k)-int(a['next_boost'])),next_boost=False)
        e.pasture_sheared=[];e.pasture_stroke=None;e.set_page('animal_detail');e.clear_hover();e.render()
        text=f"Collected {quantity} {'egg' if quantity==1 else 'eggs'}." if k=='chicken' else f"Collected {quantity} bundles of wool."
        result=e.consume_time('animal_collect')
        if result['night']:
            response=e.night_response(text);response['sound_events']=self.sound(k);return response
        e.render();return e.response(tts=text,sound_events=self.sound(k))
    @staticmethod
    def wool_tiles():return [(x,y) for y in range(3,38,5) for x in range(4,57,5)]
    def shear(self,x,y):
        e=self.engine
        if e.paused or e.day_ended or e.sleep_until is not None:return e.response()
        if e.pasture_selected!='sheep' or not e.pasture_animals['sheep']['ready']:return e.response()
        if not (0 <= x < e.dotpad.width and 0 <= y < e.dotpad.height):
            e.pasture_stroke=None
            return e.response()
        before=set(e.pasture_sheared);hit=set(before);previous=e.pasture_stroke or (x,y)
        for tx,ty in self.wool_dots():
            if e.point_to_segment_distance(tx,ty,*previous,x,y)<=self.cfg()['shear_radius']:
                hit.add(ty*e.dotpad.width+tx)
        e.last_pointer=(x,y);e.pasture_stroke=(x,y);e.pasture_sheared=sorted(hit)
        if len(hit)>=math.ceil(len(self.wool_dots())*self.cfg()['shear_success_ratio']):return self.collect()
        e.render();return e.response(sound_events=[{'kind':'correct','activity':'shearing','count':len(hit)-len(before)}] if hit!=before else [])

    def draw_scene(self):
        e=self.engine;p=e.dotpad
        p.draw_line(0,12,59,12);p.draw_line(0,13,59,13)
        for x in range(2,58):p.set_dot(x,38)
        for y in range(15,39):p.set_dot(2,y);p.set_dot(57,y)
        for k,a in e.pasture_animals.items():
            # 씬 안의 동물은 SCENE_PATTERNS 사용
            if a['owned']:
                rows=SCENE_PATTERNS['shorn' if k=='sheep' and not a['ready'] else k]
                if a.get('facing_left',False):rows=tuple(row[::-1] for row in rows)
                e.draw_icon_pattern(a['x'],a['y']+self.breathe(),rows)

    def draw_detail(self):
        e = self.engine
        k = e.pasture_selected
        p = e.dotpad

        # 디테일 전용 배열(DETAIL_PATTERNS) 사용
        rows = DETAIL_PATTERNS['shorn' if k=='sheep' and not e.pasture_animals[k]['ready'] else k]

        start_x = 22 if k == 'chicken' else 14
        start_y = (12 if k == 'chicken' else 11)+self.breathe()

        for y, row in enumerate(rows):
            for x, d in enumerate(row):
                if d == '1':
                    p.set_dot(start_x + x, start_y + y)

        if k == 'chicken' and e.pasture_animals[k]['ready']:
            # Raised oval with diagonal grooves; the surrounding space stays flat.
            for y in range(32,39):
                for x in range(24,37):
                    d=((x-30)/5)**2+((y-35)/2.5)**2
                    raised=d<=1 and (d>=0.52 or (x-y)%4!=0)
                    p.set_dot(x,y,int(raised))

    @staticmethod
    def wool_dots():
        return [(x,y) for y in range(1,36) for x in range(2,57) if x%7 or y%5]

    def draw_wool(self):
        e=self.engine;erased=set(e.pasture_sheared)
        for x,y in self.wool_dots():
            if y*e.dotpad.width+x not in erased:e.dotpad.set_dot(x,y)
    def inventory(self):
        return [dict(id=k,label=k.replace('_',' ').title(),kind='tool' if k=='animal_feed' else 'material',count=v,action='') for k,v in self.engine.pasture_goods.items()]
    def buy_rows(self):
        return [('animal_feed','animal_feed','Animal feed',self.engine.pasture_goods['animal_feed'],self.cfg()['feed_price'])] + [
            ('animal',k,k.title(),int(self.engine.pasture_animals[k]['owned']),cfg['buy_price']) for k,cfg in self.cfg()['animals'].items()]

    def buy_animal(self,item):
        e=self.engine
        if item not in self.cfg()['animals']:return None
        a=e.pasture_animals[item]
        if a['owned']:return e.response(tts='You already own a '+item+'.',sfx='error')
        price=e.market_price(self.cfg()['animals'][item]['buy_price'],'animal','buy')
        if e.resource('coin')<price:return e.response(tts='Not enough gold.',sfx='error')
        e.add_resource('coin',-price)
        a.update(owned=True,friendship=0,remaining=self.cycle_days(item),ready=False,ready_day=None,quantity=0,
                 next_boost=False,last_feed_day=e.day,fed_day=0,pet_day=0,facing_left=False,escaped=False)
        self._motion.pop(item,None)
        if item=='sheep':e.pasture_sheared=[]
        e.clear_hover();e.render()
        return e.response(tts=item.title()+' bought. Find it in the pasture.',sound_events=[{'kind':'one_shot','sound':'coin'}])
    def buy_feed(self,item):
        e=self.engine
        if item not in ('animal_feed','chicken_feed','sheep_feed'):return None
        item='animal_feed'
        price=e.market_price(self.cfg()['feed_price'],'animal_feed','buy')
        if e.resource('coin')<price:return e.response(tts='Not enough gold.',sfx='error')
        e.add_resource('coin',-price);e.pasture_goods[item]+=1;e.render()
        return e.response(tts=item.replace('_',' ').title()+' bought.',sound_events=[{'kind':'one_shot','sound':'coin'}])
    def sell_rows(self):return [('animal_product',k,k.title(),self.engine.pasture_goods[k],c['price']) for c in self.cfg()['animals'].values() if self.engine.pasture_goods[k:=c['product']]>0]
    def sell_product(self,item):
        e=self.engine
        cfg=next((a for a in self.cfg()['animals'].values() if a['product']==item),None)
        if not cfg or e.pasture_goods[item]<=0:return e.response(tts='None to sell.',sfx='error')
        e.pasture_goods[item]-=1;return cfg['price'],item.title()
