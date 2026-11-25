"""Individual pets, care, daily health and gifts. Tactile artwork is fixed-grid."""
from engine.core.petting import PettingSession, next_feedback_id
from .shapes import drawing
import math
import random
import time
from engine.core.registry import Feature
from .patterns import ICON_PATTERNS, SCENE_PATTERNS, DETAIL_PATTERNS

class Pets(Feature):
    name='pets'
    def register(self,r):
        r.owns('pets','pet_next_id','pet_selected','pet_contact','pet_pose_until','pet_active','pet_adoption','pet_motion')
        r.on('reset',self.reset)
        r.on('before_state',self.pet_idle)
        r.on('end_of_day',self.advance)
        r.on('before_navigation',self.clear_contact)
        r.on('leave_activity',self.clear_contact)
        r.save_fields(defaults=('pets','pet_next_id','pet_selected','pet_active'),transient={'pet_contact':None,'pet_pose_until':None,'pet_adoption':None,'pet_motion':{}})
        r.page('care',name='Care',objects=self.care_objects,scene=lambda:self.engine.registry.features['home'].draw_scene(),icon_grid=True,live=True)
        r.page('pets',name='Pets',objects=self.objects,icon_grid=True)
        r.page('pet_detail',name='Pet care',objects=self.detail_objects,scene=self.draw_detail,live=True,pointer_move=self.stroke,pointer_drag=self.stroke)
        r.page('pet_release',name='Find a new family',objects=self.release_objects,icon_grid=True)
        r.page('pet_give',name='Give something',objects=self.give_objects,icon_grid=True)
        r.page('pet_names',name='Choose a name',objects=self.name_objects,icon_grid=True)
        r.action('pet:',self.action)
        r.icon('pet_icon',pattern=lambda o:ICON_PATTERNS[o['species']])
        r.icon('pet_button',symbol=lambda o:self.engine.icons.category(o.get('symbol','tool')),layout_order=3)
        r.renderer('pet_body',lambda o:None)
        r.object_tts('pet_icon',lambda o:o['short'])
        r.object_tts('pet_body',lambda o:o['short'])
        r.object_tts('pet_button',lambda o:o['label'])
        r.state('pets',self.public)
        r.contribute('home.objects',lambda:[self.button('care','Care',0,'pet:care')])
        r.contribute('home.scene',self.draw_home)
        r.contribute('home.scene_objects',self.home_objects)
        r.contribute('harvest.bonus',self.harvest_bonus)
    def cfg(self):return self.engine.config['pets']
    def reset(self):
        self._pet_session=PettingSession();self._pet_feedback=None
        e=self.engine;e.pets=[];e.pet_next_id=1;e.pet_selected=None;e.pet_contact=None;e.pet_pose_until=None;e.pet_active=None;e.pet_adoption=None;e.pet_motion={}
    def clear_contact(self):
        self.engine.pet_contact=None;self.engine.pet_pose_until=None
        self._pet_session.clear();self._pet_feedback=None
    def selected(self):return next((a for a in self.engine.pets if a['id']==self.engine.pet_selected),None)
    def button(self,id,label,i,action,symbol='tool'):
        return dict(id='pet_'+id,type='pet_button',x=8+14*(i%4),y=6+10*(i//4),width=12,height=10,hit_width=12,hit_height=10,label=label,tts=label+'.',action=action,symbol=symbol)
    def back(self,page,label='Back'):return self.engine.back_arrow('pet_back',label,'pet:'+page)
    def care_objects(self):
        # The Care page shows the home scene, so the arrow keys travel like on the home page
        # (Left: farm, Right: village) instead of answering "Cannot go left/right".
        travel=[dict(id='care_farm',type='arrow',direction='left',x=3,y=35,label='Farm',tts='Farm.',action='travel:farm'),
                dict(id='care_town',type='arrow',direction='right',x=56,y=5,label='Village',tts='Village.',action='travel:town')]
        return [self.button('home','Back',0,'pet:home','nav_left'),self.button('plants','Plants',1,'flower:open','seed'),self.button('pets','Pets',2,'pet:active')]+self.engine.registry.features['home'].scene_objects()+travel
    def mood(self,a):return 'Trusts you' if a['affection']>=200 else 'Recognizes you' if a['affection']>=100 else 'Getting to know you'
    def describe(self,a):
        health='Sick' if a['sick'] else 'Hungry' if self.engine.day-a['fed_day']>=self.cfg()['hungry_days'] else self.mood(a)
        return a['name']+'. '+health+'.'+(' A gift is ready.' if a['gift'] else '')
    def objects(self):
        rows=[]
        for i,a in enumerate(self.engine.pets):
            rows.append(dict(id='pet_'+str(a['id']),type='pet_icon',species=a['species'],x=8+(i%4)*14,y=6+(i//4)*10,width=12,height=10,hit_width=12,hit_height=10,label=a['name'],short=self.describe(a),tts=self.describe(a)+' Select to care for your pet.',action='pet:open:'+str(a['id'])))
        return rows+[self.back('detail')]
    def detail_objects(self):
        a=self.selected()
        if not a:return [self.back('list')]
        actions=[('give','Give something','food'),('gift','Receive','crop'),('list','Change pet','tool'),('release','Let pet go','nav_down')]
        buttons=[self.button(k,label,i,'pet:'+k,symbol) for i,(k,label,symbol) in enumerate(actions)]
        x,y=self.position(a,True)
        body=dict(id='pet_body',type='pet_body',skip_grid=True,x=x,y=y,width=36,height=24,hit_width=36,hit_height=24,label=a['name'],short=self.describe(a),tts=self.describe(a)+' Move your hand over the animal to pet it.',action='')
        if a['gift']:buttons.append(dict(id='pet_gift',type='pet_button',skip_grid=True,x=54,y=32,width=8,height=8,hit_width=8,hit_height=8,label='Gift',tts='Gift. Select to collect.',symbol='crop',action='pet:gift'))
        return buttons+[body,self.back('care')]
    def give_objects(self):
        a=self.selected()
        rows=[self.button('feed','Animal feed',0,'pet:feed','fertilizer'),self.button('treat','Special feed',1,'pet:treat','fertilizer')]
        if a and a['sick']:rows.append(self.button('medicine','Medicine',2,'pet:medicine','chest'))
        return rows+[self.back('detail')]
    def name_objects(self):
        species=self.engine.pet_adoption
        if species not in ('dog','cat'):return [self.back('list')]
        return [self.button('name_'+str(i),species.title()+' '+n,i,'pet:name:'+str(i),'tool') for i,n in enumerate(self.cfg()['names'][species]) if n.casefold() not in self.used_names()]+[self.back('care')]
    def used_names(self):
        return {a['name'].split(' ',1)[-1].casefold() for a in self.engine.pets}
    def available_names(self,species):
        return [n for n in self.cfg()['names'][species] if n.casefold() not in self.used_names()]
    def begin_adoption(self,species):
        e=self.engine
        if len(e.pets)>=self.cfg()['max_pets']:return e.response(tts='No room for another pet.')
        e.pet_adoption=species;e.set_page('pet_names');e.clear_hover();e.render()
        return e.response(tts='Choose a name for your '+species+'.')
    def release_objects(self):
        a=self.selected()
        return [self.button('confirm','Confirm: '+(a['name'] if a else 'pet'),0,'pet:release_confirm'),self.button('cancel','Keep pet',1,'pet:detail')]
    def sound(self,a):return dict(kind='pet_sound',sound=a['species']+'_main',pet_id=a['id'],pitch=a['pitch'])
    def adopt(self,species,name=None):
        e=self.engine
        if species not in ('dog','cat'):return False,'Unknown pet.'
        if len(e.pets)>=self.cfg()['max_pets']:return False,'No room for another pet.'
        available=self.available_names(species)
        if name is not None and name.casefold() in self.used_names():return False,'That name is already in use. Choose another name.'
        if not available:return False,'No unused names available.'
        name=name or random.choice(available)
        number=e.pet_next_id;e.pet_next_id+=1
        # Stable per-individual pitch, chosen once and saved, rather than per call.
        pitch=self.cfg()['pitch_values'][(number-1)%len(self.cfg()['pitch_values'])]
        a=dict(id=number,species=species,name=f'{species.title()} {name or random.choice(self.cfg()["names"][species])}',pitch=pitch,appearance=random.randrange(3),affection=0,fed_day=e.day,pet_day=-1,sick=False,gift=None)
        e.pets.append(a);e.pet_selected=number;e.pet_active=number
        return True,a['name']+' joined your home.'
    def action(self,arg,obj):
        e=self.engine;events=[];text=None
        if arg=='empty':return e.response(tts='Empty pet slot. Use an adoption voucher to adopt a pet.')
        if arg.startswith('name:'):
            species=e.pet_adoption
            try:index=int(arg.split(':')[1])
            except ValueError:return e.response()
            if e.current_page!='pet_names' or species not in ('dog','cat') or not 0<=index<12 or e.roulette_goods.get(species+'_voucher',0)<1:return e.response(tts='Adoption unavailable.')
            ok,text=self.adopt(species,self.cfg()['names'][species][index])
            if not ok:return e.response(tts=text)
            e.roulette_goods[species+'_voucher']-=1;e.pet_adoption=None;e.set_page('pet_detail');events=[self.sound(self.selected())]
        elif arg=='detail' and e.current_page=='pets':
            e.set_page('pet_detail' if self.selected() else 'care');text=self.describe(self.selected()) if self.selected() else 'Care.'
        elif arg=='active':
            a=self.active()
            if not a:return e.response(tts='No pets yet. Use an adoption voucher from your inventory.')
            return self.action('open:'+str(a['id']),obj)
        elif arg in ('care','list','home'):
            if arg=='list' and e.current_page!='pet_detail':return e.response(tts='Choose Change pet from pet care.')
            self.clear_contact();e.set_page({'care':'care','list':'pets','home':'home'}[arg]);text={'care':'Care. Plants and pets.','list':'Pets.' if e.pets else 'No pets yet. Use an adoption voucher from your inventory.','home':'Home.'}[arg]
        elif arg.startswith('open:'):
            a=next((a for a in e.pets if str(a['id'])==arg.split(':')[1]),None)
            if not a:return e.response(tts='Pet unavailable.')
            e.pet_selected=a['id'];e.pet_active=a['id'];self.clear_contact();e.set_page('pet_detail');events=[self.sound(a)];text=self.describe(a)
        else:
            a=self.selected()
            if not a or e.current_page not in ('pet_detail','pet_release','pet_give'):return e.response()
            goods=e.roulette_goods
            if arg=='detail':e.set_page('pet_detail')
            elif arg=='give':e.set_page('pet_give');text='Give something.'
            elif arg=='release':e.set_page('pet_release');text='Are you sure you want to let '+a['name']+' go? Select Confirm or Keep pet.'
            elif arg=='release_confirm' and e.current_page=='pet_release':
                text=a['name']+' has joined a new family.';e.pets.remove(a);e.pet_selected=None;e.pet_active=next((p['id'] for p in e.pets),None);self.clear_contact();e.set_page('care')
            elif e.current_page not in ('pet_detail','pet_give'):return e.response()
            elif arg=='feed':
                if a['fed_day']==e.day:return e.response(tts='Already fed today.')
                if e.pasture_goods.get('animal_feed',0)<=0:return e.response(tts='No animal feed. Buy some at General goods.')
                e.pasture_goods['animal_feed']-=1;a['fed_day']=e.day;a['affection']=min(299,a['affection']+self.cfg()['feed_points']);text=a['name']+' fed.';events=[{'kind':'one_shot','sound':'feed'},self.sound(a)];e.pet_pose_until=('eating',time.monotonic()+3)
            elif arg in ('treat','medicine'):
                key='special_feed' if arg=='treat' else 'medicine'
                if goods.get(key,0)<=0:return e.response(tts='No '+key.replace('_',' ')+'.')
                if arg=='medicine' and not a['sick']:return e.response(tts='Your pet is healthy.')
                goods[key]-=1
                if arg=='treat':a['affection']=min(299,a['affection']+self.cfg()['treat_points']);a['fed_day']=e.day
                else:a['sick']=False;a['fed_day']=e.day
                text=a['name']+(' enjoyed the treat.' if arg=='treat' else ' is feeling better.');events=[{'kind':'one_shot','sound':'feed'},self.sound(a)] if arg=='treat' else [self.sound(a)]
            elif arg=='gift':
                if not a['gift']:return e.response(tts='No gift today.')
                g=a['gift'];e.resources[g['resource']][g['item']]=e.resources[g['resource']].get(g['item'],0)+g['count'];a['gift']=None;text=a['name']+' brought '+g['label']+'.';events=[self.sound(a),{'kind':'correct','count':1}]
            else:return e.response()
        if arg.startswith(('open:','name:')) or arg in ('feed','treat','medicine','gift'):
            a=self.selected()
            if a:self.motion(a)['pose']=random.choice(['standing','sitting'])
        if arg in ('feed','treat','medicine'):e.set_page('pet_detail')
        e.clear_hover();e.render();return e.response(tts=text or (self.describe(self.selected()) if self.selected() else 'Pets.'),sound_events=events)
    def motion(self,a):
        e=self.engine;now=time.monotonic();key=str(a['id']);m=e.pet_motion.get(key)
        if m is None:
            m=dict(next=now+random.uniform(3,5),dx=0,dy=0,pose='sitting',left=False);e.pet_motion[key]=m
        if now>=m['next'] and not e.paused and not e.day_ended:
            m.update(next=now+random.uniform(3,5),dx=random.randint(-2,2),dy=random.randint(0,1))
        return m
    def pose(self,a):
        if self.engine.day_ended or self.engine.time_used_cells>=self.engine.time_total_cells*.75:return 'sleeping'
        if a['sick']:return 'unwell'
        return self.motion(a)['pose']
    def position(self,a,detail=False):
        m=self.motion(a)
        return (29+m['dx'],25+m['dy']) if detail else (42+max(-1,min(1,m['dx'])),33+m['dy'])
    def rows(self,a):
        rows=DETAIL_PATTERNS[a['species']][self.pose(a)]
        return tuple(r[::-1] for r in rows) if self.motion(a)['left'] else rows
    def draw_detail(self):
        a=self.selected()
        # Large drawing: solid legs, tail and ears, one-pin outline, line texture on the body to feel
        # while stroking (shapes.drawing; tactile design rules, README.md).
        if a:self.engine.draw_icon_pattern(*self.position(a,True),drawing(a['species'],self.pose(a),self.motion(a)['left']))
    def active(self):
        return next((a for a in self.engine.pets if a['id']==self.engine.pet_active),self.engine.pets[0] if self.engine.pets else None)
    def home_objects(self):
        rows=[]
        a=self.active()
        if a:
            x,y=self.position(a)
            rows.append(dict(id='home_pet_'+str(a['id']),type='pet_body',skip_grid=True,x=x,y=y,width=7,height=5,hit_width=9,hit_height=7,label=a['name'],short=self.describe(a),tts=self.describe(a),action='pet:open:'+str(a['id'])))
        return rows
    def home_rows(self,a):
        pose=self.pose(a)
        rows=ICON_PATTERNS[a['species']]
        if pose=='sleeping':rows=('0000000','0000000','0111110','1111111','0111110')
        elif pose=='sitting':rows=tuple(rows[:3])+('0011110','0011110')
        return tuple(r[::-1] for r in rows) if self.motion(a)['left'] else rows
    def draw_home(self):
        a=self.active()
        if a:
            self.engine.draw_icon_pattern(*self.position(a),self.home_rows(a))
    def pet_complete(self,a,now):
        e=self.engine
        if a['pet_day']!=e.day:
            a['pet_day']=e.day
            a['affection']=min(299,a['affection']+self.cfg()['pet_points'])
        self._pet_feedback=dict(id=next_feedback_id(),at=now,events=[self.sound(a)])
    def pet_idle(self):
        e=self.engine;a=self.selected()
        if e.current_page!='pet_detail' or not a or e.paused or e.day_ended or e.sleep_until is not None:
            self.clear_contact();return
        now=time.monotonic()
        if self._pet_session.poll(now,self.cfg()['pet_seconds'],self.cfg().get('pet_release_idle_seconds',0.5)):
            self.pet_complete(a,now)
    def stroke(self,x,y):
        e=self.engine;a=self.selected();now=time.monotonic()
        if not a or e.paused or e.day_ended or e.sleep_until is not None:
            self.clear_contact();return None
        rows=self.rows(a);cx,cy=self.position(a,True);ix=int(x)-(cx-18);iy=int(y)-(cy-12)
        inside=0<=ix<36 and 0<=iy<24 and rows[iy][ix]=='1'
        if self._pet_session.move(x,y,now,inside,self.cfg()['pet_seconds'],self.cfg().get('pet_release_idle_seconds',0.5),self.cfg()['contact_gap_seconds']):
            self.pet_complete(a,now)
            return e.response()
        return None
    def advance(self):
        e=self.engine;cfg=self.cfg();notes=[]
        for a in e.pets:
            missed=e.day+1-a['fed_day']
            if missed>=cfg['sick_after_days'] and not a['sick']:
                a['sick']=True;notes.append(a['name']+' is sick. Give medicine.')
            if missed>=cfg['hungry_days']:a['affection']=max(0,a['affection']-cfg['neglect_points'])
            if not a['sick'] and not a['gift'] and missed<cfg['hungry_days'] and random.random()<cfg['gift_chances'][min(2,a['affection']//100)]:
                resource='seeds' if a['species']=='dog' else 'fish'
                pool=list(e.config['seeds']) if resource=='seeds' else [k for k,v in e.config['fishing']['fish'].items() if v['grade']=='low']
                item=random.choice(pool);label=(e.config['seeds'][item].get('label',item)+' seeds') if resource=='seeds' else e.config['fishing']['fish'][item]['label']
                a['gift']=dict(resource=resource,item=item,count=1,label=label)
        self.clear_contact();return ' '.join(notes) or None
    def harvest_bonus(self):
        return int(any(a['affection']>=200 and not a['sick'] and self.engine.day-a['fed_day']<self.cfg()['hungry_days'] for a in self.engine.pets))*self.cfg()['trusted_harvest_bonus']
    def public(self):
        a=self.selected();e=self.engine;active=self.active()
        return dict(petting_feedback=self._pet_feedback if self._pet_feedback and time.monotonic()-self._pet_feedback["at"]<2 else None,home_pet=dict(id=active['id'],name=active['name'],species=active['species'],appearance=active.get('appearance',(active['id']-1)%3),pose=self.pose(active),position=self.position(active),pattern=self.rows(active)) if active else None,animals=[dict(id=p['id'],species=p['species'],name=p['name'],appearance=p.get('appearance',(p['id']-1)%3),pitch=p['pitch'],status=self.describe(p)) for p in e.pets],selected=e.pet_selected,detail=dict(species=a['species'],appearance=a.get('appearance',(a['id']-1)%3),position=self.position(a,True),pose=self.pose(a),name=a['name']) if a else None,active=e.pet_active,pose=self.pose(a) if a else None,brush_region=dict(x=self.position(a,True)[0]-18,y=self.position(a,True)[1]-12,width=36,height=24) if a else None,audio=self.cfg()['audio'])
