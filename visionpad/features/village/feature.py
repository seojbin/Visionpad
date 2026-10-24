"""Village: Rowan's sequential tutorial quest, the town square and the weekly trading calendar.

Engine attributes (save format): rowan_stage, rowan_greeted, rowan_dialogue, rowan_submit_open.
Shared state written: resources (rowan_soup, seeds, crops, coin), current_page, hover_object_id.
Uses the NPC feature's engine API: recent_reaction, npc_voice_profile, rowan_advice, next_rowan_advice.
Provides engine.market_price() for every priced item and engine.talk_rowan()/submit_rowan_crop().
"""
from visionpad.core import order
from visionpad.core.registry import Feature
from visionpad.display.icons import IconRenderer

PATTERNS = IconRenderer.PATTERNS


class Village(Feature):
    name = "village"

    def register(self, reg):
        reg.owns("rowan_stage", "rowan_greeted", "rowan_dialogue", "rowan_submit_open")
        reg.page("town", objects=self.town_objects, scene=self.draw_town_scene, icon_grid=True, arrival=self.arrival,
                 detail=lambda: "Village. Shop and Rowan.")
        reg.page("shop_calendar", objects=self.calendar_objects, icon_grid=True)
        reg.page("rowan_dialogue", objects=self.rowan_objects, icon_grid=True)
        reg.page("rowan_submit", objects=self.rowan_objects, icon_grid=True)
        reg.action("talk_rowan", lambda arg, obj: self.talk(), before_night_guard=True)
        reg.action("repeat_rowan", self.repeat, before_night_guard=True)
        reg.action("rowan_submit:", lambda arg, obj: self.submit_crop(arg), before_night_guard=True)
        reg.action("open_calendar", lambda arg, obj: self.open_calendar(), before_night_guard=True)
        reg.action("calendar_day:", self.calendar_day, before_night_guard=True)
        reg.icon("rowan", pattern=lambda obj: PATTERNS['rowan'], layout_order=1)
        reg.icon("nav_up", pattern=lambda obj: PATTERNS['nav_up'], layout_order=2)
        reg.icon("nav_down", pattern=lambda obj: PATTERNS['nav_down'], layout_order=3)
        reg.icon("calendar_day", pattern=lambda obj: PATTERNS['calendar'])
        reg.icon("calendar_button", pattern=lambda obj: PATTERNS['calendar'])
        reg.state("rowan_submission", lambda: self.engine.current_page=="rowan_submit" and self.engine.rowan_submit_open)
        reg.state("calendar", lambda: {"weekday":self.calendar_days()[self.weekday_index()]['name'], "offer":self.calendar_text()})
        reg.on("reset", self.reset, order=order.Reset.VILLAGE)
        reg.on("close_dialogue", self.close_dialogue)
        reg.save_fields(defaults=("rowan_stage", "rowan_greeted", "rowan_dialogue", "rowan_submit_open"),
                        migrate=self.migrate)
        reg.expose("talk_rowan", self.talk)
        reg.expose("submit_rowan_crop", self.submit_crop)
        reg.expose("market_price", self.market_price)
        reg.expose("open_calendar", self.open_calendar)

    def close_dialogue(self):
        e = self.engine
        e.rowan_dialogue = ""
        e.rowan_submit_open = False

    @staticmethod
    def migrate(state, fresh):
        """Saves made on retired Rowan pages reopen on the page that replaced them."""
        if state.get('current_page') == 'rowan_dialogue':
            state['rowan_submit_open'] = False
            state['current_page'] = state['current_location'] = 'town'
        if state.get('current_page')=='rowan_submit': state['rowan_submit_open']=True
        if state.get('current_page')=='shop_calendar': state['current_page']='shop_choice'

    def arrival(self):
        e = self.engine
        if not e.rowan_greeted:
            e.rowan_greeted=True
            return 'Village. Rowan would like to meet you.'
        return None

    def repeat(self, arg, obj):
        e = self.engine
        result = e.response(tts='Rowan. '+e.rowan_dialogue, speech_profile='shopkeeper', priority='dialogue')
        result['speech_channel'] = 'quest'
        return result

    def calendar_day(self, arg, obj):
        return self.engine.response(tts=self.calendar_text(int(arg.split(':')[0])))

    def town_objects(self):
        e = self.engine
        base = [dict(obj) for obj in e.config.get("town", {}).get("objects", [])]
        return base + [self.rowan_object()] + self.town_nav_objects() + self.town_spatial_objects()

    def reset(self):
        e = self.engine
        e.rowan_stage = 'new'
        e.rowan_greeted = False
        e.rowan_dialogue = ''
        e.rowan_submit_open = False

    def weekday_index(self):
        e = self.engine
        return (e.day - 1) % 7

    def calendar_days(self):
        e = self.engine
        return e.config['weekly_market']['days']

    def market_price(self, price, kind, mode):
        e = self.engine
        day = self.calendar_days()[self.weekday_index()]
        categories = day.get(mode, [])
        if 'all' in categories or kind in categories:
            percentage = e.config['weekly_market']['bonus_percent' if mode == 'sell' else 'discount_percent']
            price = int(price) * (100 + percentage if mode == 'sell' else 100 - percentage) // 100
        return e.sale_price(price) if mode == 'sell' else int(price)

    def calendar_text(self, index=None):
        e = self.engine
        index = self.weekday_index() if index is None else index
        day = self.calendar_days()[index]
        percent=e.config['weekly_market']['bonus_percent' if day.get('sell') else 'discount_percent']
        return f"{day['name']}. {day['description'].format(percent=percent)}"

    def open_calendar(self):
        e = self.engine
        offers = ['Monday: ore discount!', 'Tuesday: better food prices!',
                  'Wednesday: better fish prices!', 'Thursday: seed discount!',
                  'Friday: better ore prices!', 'Saturday: tool discount!',
                  'Sunday: better prices for everything!']
        return e.response(tts='Today is '+self.calendar_days()[self.weekday_index()]['name']+'. '+offers[self.weekday_index()])

    def calendar_objects(self):
        e = self.engine
        result = []
        for i, day in enumerate(self.calendar_days()):
            result.append(dict(id=f'calendar_{i}', type='calendar_day', x=8+14*(i%4), y=7+12*(i//4),
                width=12,height=9,hit_width=10,hit_height=8,label=day['name'],
                selected=i==self.weekday_index(), tts=self.calendar_text(i), action=f'calendar_day:{i}'))
        result.append(e.back_arrow('calendar_back','Back to shop','return_shop_choice'))
        return result

    def rowan_object(self):
        e = self.engine
        return dict(id='town_rowan',type='rowan',x=22,y=6,width=12,height=10,hit_width=10,hit_height=8,
                    label='Rowan',tts='Rowan. Quest available.' if e.rowan_stage!='done' else 'Rowan.',
                    quest_available=e.rowan_stage!='done',action='talk_rowan')

    def town_nav_objects(self):
        e = self.engine
        return [
            dict(id='town_nav_mine', type='nav_up', x=36, y=6, width=12, height=10,
                 hit_width=10, hit_height=8, label='Mine', tts='Mine. Go north.',
                 action='travel:mine'),
            dict(id='town_nav_fishing', type='nav_down', x=50, y=6, width=12, height=10,
                 hit_width=10, hit_height=8, label='Fishing lake', tts='Fishing lake. Go south.',
                 action='travel:fishing'),
        ]

    def town_spatial_objects(self):
        e = self.engine
        return [
            dict(id='town_scene_shop', type='town_hitbox', skip_grid=True,
                 x=43, y=25, width=20, height=20, hit_width=20, hit_height=20,
                 label='Shop', tts='Shop. Buy or sell.', action='open_shop'),
            dict(id='town_scene_rowan', type='town_hitbox', skip_grid=True,
                 x=10, y=19, width=7, height=7, hit_width=9, hit_height=9,
                 label='Rowan', tts='Rowan. Quest available.' if e.rowan_stage != 'done' else 'Rowan.',
                 action='talk_rowan'),
            dict(id='town_road_mine', type='town_hitbox', skip_grid=True,
                 x=20, y=16, width=9, height=5, hit_width=11, hit_height=7,
                 label='Mine', tts='Mine. Go north.', action='travel:mine'),
            dict(id='town_road_fishing', type='town_hitbox', skip_grid=True,
                 x=20, y=37, width=9, height=5, hit_width=11, hit_height=7,
                 label='Fishing lake', tts='Fishing lake. Go south.', action='travel:fishing'),
            dict(id='town_road_home', type='town_hitbox', skip_grid=True,
                 x=3, y=27, width=6, height=7, hit_width=8, hit_height=9,
                 label='Home', tts='Home. Go west.', action='travel:home'),
        ]

    def draw_town_scene(self):
        e = self.engine
        pad = e.dotpad
        # 1. 상단 아이콘(하단 y=10)과 2칸 떨어진 y=12, 13에 2칸 두께 경계선 표시
        pad.draw_line(0, 12, pad.width - 1, 12)
        pad.draw_line(0, 13, pad.width - 1, 13)

        # 2. 마을 길 외곽선 (세로길 x: 16~24, 가로길 y: 24~30, 경계선 y=13과 맞닿음)
        for y in range(13, pad.height):
            if not (24 <= y <= 30):
                pad.set_dot(16, y)
                pad.set_dot(24, y)
        for x in range(0, 34):
            if not (16 < x < 24):
                pad.set_dot(x, 24)
                pad.set_dot(x, 30)

        # 3. 길 내부 중앙선만 넓은 간격(4칸 주기)의 점선으로 표시
        for y in range(20, 34, 4):
            pad.set_dot(20, y)
        for x in range(8, 32, 4):
            if x != 20:
                pad.set_dot(x, 27)

        # 4. 사거리 바깥 좌상단(x=10, y=19)에 배치된 NPC 로완
        e.draw_icon_pattern(10, 19, (
            '01110',
            '01110',
            '11111',
            '01110',
            '01010',
        ))

        # 5. 상행 길 끝 화살표 ▲ (광산 이동: x=20, y=16)
        e.draw_icon_pattern(20, 16, (
            '00100',
            '01110',
            '11111',
        ))

        # 6. 하행 길 끝 화살표 ▼ (낚시터 이동: x=20, y=37)
        e.draw_icon_pattern(20, 37, (
            '11111',
            '01110',
            '00100',
        ))

        # 7. 좌측 길 끝 화살표 ◀ (집 이동: x=2, y=27)
        e.draw_icon_pattern(2, 27, (
            '001',
            '011',
            '111',
            '011',
            '001',
        ))

        # 8. 우측 상점 건물: 전체를 꽉 채우고(양각) 처마선·창문·출입문만 음각(0)으로 표현
        # (a) 꽉 채운 박공지붕 (y: 14~20, 경계선 아래에 밀착)
        for dy in range(7):
            half = 4 + dy
            y = 14 + dy
            for x in range(43 - half, 43 + half + 1):
                pad.set_dot(x, y, 1)
        # 지붕 중앙 작은 음각 창
        for wx in (42, 43, 44):
            pad.set_dot(wx, 17, 0)

        # (b) 지붕과 벽면을 구분하는 음각 처마 라인 (y = 21)
        for x in range(34, 53):
            pad.set_dot(x, 21, 0)
        pad.set_dot(34, 21, 1)
        pad.set_dot(52, 21, 1)

        # (c) 꽉 채운 건물 외벽 (x: 34~52, y: 22~34)
        for y in range(22, 35):
            for x in range(34, 53):
                pad.set_dot(x, y, 1)

        # (d) 좌/우 창문을 음각(0)으로 파내기 (3x3 창문)
        for wy in range(24, 27):
            for wx in (36, 37, 38, 48, 49, 50):
                pad.set_dot(wx, wy, 0)

        # (e) 중앙 출입문을 음각(0)으로 파내고 문손잡이만 양각(1)으로 표시
        for y in range(26, 35):
            for x in range(41, 46):
                pad.set_dot(x, y, 0)
        pad.set_dot(44, 30, 1)

    def show_rowan(self, text, page='rowan_dialogue', events=None):
        """Rowan speaks a quest line: the NPC feature adds a one-time reaction and Rowan's voice."""
        e = self.engine
        reaction = e.recent_reaction("shopkeeper")
        if reaction:
            text += " " + reaction
        e.rowan_dialogue=text
        e.set_page('rowan_submit' if page=='rowan_submit' else 'town')
        e.rowan_submit_open = page=='rowan_submit'
        e.clear_hover()
        if e.current_page == 'town':
            e.hover_object_id = 'town_rowan'
        e.render()
        result = e.response(tts=f'Rowan. {text}',sound_events=events)
        result['speech_channel'] = 'quest'
        result["speech_profile"] = e.npc_voice_profile("shopkeeper")
        result["priority"] = "dialogue"
        return result

    def talk(self):
        e = self.engine
        if e.current_location != 'town': return e.response(tts='Rowan is in the village.')
        cfg=e.config['rowan']
        if e.rowan_stage=='new':
            e.resources['foods']['rowan_soup']=e.resources['foods'].get('rowan_soup',0)+1
            e.rowan_stage='soup_given'
            return self.show_rowan("Welcome! I'm Rowan. Here's my soup. Press the second button, F2, to open your inventory. Select Rowan's soup to eat it. Press F2 again to return to the village, then talk to me.")
        if e.rowan_stage=='soup_given':
            if e.resources['foods'].get('rowan_soup',0)>0:
                return self.show_rowan("Try my soup. Press the second button, F2, and select Rowan's soup. Press F2 again to return here.")
            for seed in e.config['seeds']:
                e.resources['seeds'][seed]=e.resources['seeds'].get(seed,0)+cfg['seed_gift_each']
            e.rowan_stage='seeds_given'
            return self.show_rowan("Glad you enjoyed the soup! Here are tomato, carrot, and potato seeds. Talk to me again when you're ready.")
        if e.rowan_stage=='seeds_given':
            e.rowan_stage='vegetable_requested'
            return self.show_rowan("I'm short of vegetables. Could you bring me one? Go to the farm, select a plot, and plant a seed. Water it, then sleep at home. Water it each day as it grows. When it's ready, harvest it and bring me any one vegetable. " + e.rowan_advice("farming"))
        if e.rowan_stage=='vegetable_requested':
            text = 'Choose one vegetable to give me. You can leave and come back anytime.' if any(e.resources['crops'].values()) else 'You have no vegetables yet. Plant a seed, water it each day, and sleep until it grows. Come back after harvesting.'
            return self.show_rowan(text, 'rowan_submit')
        return self.show_rowan(e.next_rowan_advice())

    def rowan_objects(self):
        e = self.engine
        result=[]
        if e.current_page!='rowan_submit': return result
        for key in e.config['seeds']:
            count=e.resources['crops'].get(key,0)
            if count:
                result.append(dict(id='rowan_crop_'+key,type='ingredient',ingredient_id=key,seed_id=key,
                    item_kind='crop',x=8+16*len(result),y=22,width=12,height=9,hit_width=10,hit_height=8,
                    label=e.get_seed_label(key),count=count,required_count=1,selected=False,
                    tts=f"{e.get_seed_label(key)}. Stock {count}. Give one to Rowan.",action='rowan_submit:'+key))
        result.append(e.back_arrow('rowan_back','Back to village','return_scene'))
        return result

    def submit_crop(self, seed):
        e = self.engine
        if e.current_page!='rowan_submit' or not e.rowan_submit_open or e.rowan_stage!='vegetable_requested':return e.response()
        if seed not in e.config['seeds'] or e.resources['crops'].get(seed,0)<1:
            return e.response(tts='No vegetable to give.')
        e.add_resource('crops', -1, item=seed)
        e.add_resource('coin', e.config['rowan']['vegetable_reward_gold'])
        e.rowan_stage='done'
        return self.show_rowan(f"Thank you! This is just what I needed. Here's {e.config['rowan']['vegetable_reward_gold']} gold.",events=[{'kind':'one_shot','sound':'coin'}])
