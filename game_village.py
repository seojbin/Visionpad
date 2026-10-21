"""Rowan's sequential tutorials and the village's weekly trading calendar."""


class VillageMixin:
    def reset_village(self):
        self.rowan_stage = 'new'
        self.rowan_greeted = False
        self.rowan_dialogue = ''
        self.rowan_submit_open = False

    def weekday_index(self):
        return (self.day - 1) % 7

    def calendar_days(self):
        return self.config['weekly_market']['days']

    def market_price(self, price, kind, mode):
        day = self.calendar_days()[self.weekday_index()]
        categories = day.get(mode, [])
        if 'all' in categories or kind in categories:
            percentage = self.config['weekly_market']['bonus_percent' if mode == 'sell' else 'discount_percent']
            price = int(price) * (100 + percentage if mode == 'sell' else 100 - percentage) // 100
        return self.sale_price(price) if mode == 'sell' else int(price)

    def calendar_text(self, index=None):
        index = self.weekday_index() if index is None else index
        day = self.calendar_days()[index]
        percent=self.config['weekly_market']['bonus_percent' if day.get('sell') else 'discount_percent']
        return f"{day['name']}. {day['description'].format(percent=percent)}"

    def open_calendar(self):
        offers = ['Monday: ore discount!', 'Tuesday: better food prices!',
                  'Wednesday: better fish prices!', 'Thursday: seed discount!',
                  'Friday: better ore prices!', 'Saturday: tool discount!',
                  'Sunday: better prices for everything!']
        return self.response(tts='Today is '+self.calendar_days()[self.weekday_index()]['name']+'. '+offers[self.weekday_index()])

    def get_calendar_objects(self):
        result = []
        for i, day in enumerate(self.calendar_days()):
            result.append(dict(id=f'calendar_{i}', type='calendar_day', x=8+14*(i%4), y=7+12*(i//4),
                width=12,height=9,hit_width=10,hit_height=8,label=day['name'],
                selected=i==self.weekday_index(), tts=self.calendar_text(i), action=f'calendar_day:{i}'))
        result.append(self.back_arrow('calendar_back','Back to shop','return_shop_choice'))
        return result

    def rowan_object(self):
        return dict(id='town_rowan',type='rowan',x=22,y=6,width=12,height=10,hit_width=10,hit_height=8,
                    label='Rowan',tts='Rowan. Quest available.' if self.rowan_stage!='done' else 'Rowan.',
                    quest_available=self.rowan_stage!='done',action='talk_rowan')

    def town_nav_objects(self):
        return [
            dict(id='town_nav_mine', type='nav_up', x=36, y=6, width=12, height=10,
                 hit_width=10, hit_height=8, label='Mine', tts='Mine. Go north.',
                 action='travel:mine'),
            dict(id='town_nav_fishing', type='nav_down', x=50, y=6, width=12, height=10,
                 hit_width=10, hit_height=8, label='Fishing lake', tts='Fishing lake. Go south.',
                 action='travel:fishing'),
        ]

    def town_spatial_objects(self):
        """
        마을 하단 공간 그래픽(y >= 14)의 클릭 히트박스:
        - NPC 로완: 사거리 바깥 좌상단 (x=10, y=18)
        - 상점 건물: 우측 (x=43, y=25)
        - 광산/낚시터/집 방향 길 끝 화살표
        """
        return [
            dict(id='town_scene_shop', type='town_hitbox', skip_grid=True,
                 x=43, y=25, width=20, height=18, hit_width=20, hit_height=18,
                 label='Shop', tts='Shop. Buy or sell.', action='open_shop'),
            dict(id='town_scene_rowan', type='town_hitbox', skip_grid=True,
                 x=10, y=18, width=7, height=7, hit_width=9, hit_height=9,
                 label='Rowan', tts='Rowan. Quest available.' if self.rowan_stage != 'done' else 'Rowan.',
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
        pad = self.dotpad
        # 1. 상단 아이콘 하단(y=10)과 2칸 떨어진 y=12에 실선 구분선
        pad.draw_line(0, 12, pad.width - 1, 12)

        # 2. 마을 길 (세로길 x: 16~24, 가로길 y: 24~30) - 경계선 아래 2칸(y=14)부터 시작
        for y in range(14, pad.height):
            if not (24 <= y <= 30):
                pad.set_dot(16, y)
                pad.set_dot(24, y)
            if y % 3 == 0 and 19 <= y <= 33:
                pad.set_dot(18 if (y // 3) % 2 == 0 else 22, y)

        for x in range(0, 34):
            if not (16 < x < 24):
                pad.set_dot(x, 24)
                pad.set_dot(x, 30)
            if x % 4 == 2 and 7 <= x <= 29:
                pad.set_dot(x, 27)

        # 3. 사거리 교차부 바깥 좌상단(x=10, y=18)에 자연스럽게 배치된 NPC 로완
        self.draw_icon_pattern(10, 18, (
            '01110',
            '01110',
            '11111',
            '01110',
            '01010',
        ))

        # 4. 상행 길 끝 화살표 ▲ (광산 이동: x=20, y=16)
        self.draw_icon_pattern(20, 16, (
            '0001000',
            '0011100',
            '0111110',
            '1111111',
        ))

        # 5. 하행 길 끝 화살표 ▼ (낚시터 이동: x=20, y=37)
        self.draw_icon_pattern(20, 37, (
            '1111111',
            '0111110',
            '0011100',
            '0001000',
        ))

        # 6. 좌측 길 끝 화살표 ◀ (집 이동: x=3, y=27)
        self.draw_icon_pattern(3, 27, (
            '0001',
            '0011',
            '0111',
            '1111',
            '0111',
            '0011',
            '0001',
        ))

        # 7. 우측 상점 실제 집 건물 도트 그래픽 (x: 33~53, y: 15~34)
        for dy in range(7):
            half = 4 + dy
            y = 15 + dy
            for x in range(43 - half, 43 + half + 1):
                if dy in (0, 6) or x in (43 - half, 43 + half) or (x + dy) % 2 == 0:
                    pad.set_dot(x, y)

        for y in range(22, 35):
            pad.set_dot(34, y)
            pad.set_dot(52, y)
            if y in (22, 34):
                for x in range(34, 53):
                    pad.set_dot(x, y)
            elif y % 2 == 0:
                for x in range(36, 51, 4):
                    if not (40 <= x <= 46 and y >= 27):
                        pad.set_dot(x, y)

        for wy in (25, 26):
            for wx in (37, 38, 48, 49):
                pad.set_dot(wx, wy)

        for y in range(27, 35):
            pad.set_dot(41, y)
            pad.set_dot(45, y)
        for x in range(41, 46):
            pad.set_dot(x, 27)
        pad.set_dot(44, 31)

    def show_rowan(self, text, page='rowan_dialogue', events=None):
        self.rowan_dialogue=text
        self.current_page='rowan_submit' if page=='rowan_submit' else 'town'
        self.rowan_submit_open = page=='rowan_submit'
        self.clear_hover()
        if self.current_page == 'town':
            self.hover_object_id = 'town_rowan'
        self.render()
        result = self.response(tts=f'Rowan. {text}',sound_events=events)
        result['speech_channel'] = 'quest'
        return result

    def talk_rowan(self):
        if self.current_location != 'town': return self.response(tts='Rowan is in the village.')
        cfg=self.config['rowan']
        if self.rowan_stage=='new':
            self.resources['foods']['rowan_soup']=self.resources['foods'].get('rowan_soup',0)+1
            self.rowan_stage='soup_given'
            return self.show_rowan("Welcome! I'm Rowan. Here's my soup. Press the second button, F2, to open your inventory. Select Rowan's soup to eat it. Press F2 again to return to the village, then talk to me.")
        if self.rowan_stage=='soup_given':
            if self.resources['foods'].get('rowan_soup',0)>0:
                return self.show_rowan("Try my soup. Press the second button, F2, and select Rowan's soup. Press F2 again to return here.")
            for seed in self.config['seeds']:
                self.resources['seeds'][seed]=self.resources['seeds'].get(seed,0)+cfg['seed_gift_each']
            self.rowan_stage='seeds_given'
            return self.show_rowan("Glad you enjoyed the soup! Here are tomato, carrot, and potato seeds. Talk to me again when you're ready.")
        if self.rowan_stage=='seeds_given':
            self.rowan_stage='vegetable_requested'
            return self.show_rowan("I'm short of vegetables. Could you bring me one? Go to the farm, select a plot, and plant a seed. Water it, then sleep at home. Water it each day as it grows. When it's ready, harvest it and bring me any one vegetable. " + self.rowan_advice("farming"))
        if self.rowan_stage=='vegetable_requested':
            text = 'Choose one vegetable to give me. You can leave and come back anytime.' if any(self.resources['crops'].values()) else 'You have no vegetables yet. Plant a seed, water it each day, and sleep until it grows. Come back after harvesting.'
            return self.show_rowan(text, 'rowan_submit')
        return self.show_rowan(self.next_rowan_advice())

    def get_rowan_objects(self):
        result=[]
        if self.current_page!='rowan_submit': return result
        for key in self.config['seeds']:
            count=self.resources['crops'].get(key,0)
            if count:
                result.append(dict(id='rowan_crop_'+key,type='ingredient',ingredient_id=key,seed_id=key,
                    item_kind='crop',x=8+16*len(result),y=22,width=12,height=9,hit_width=10,hit_height=8,
                    label=self.get_seed_label(key),count=count,required_count=1,selected=False,
                    tts=f"{self.get_seed_label(key)}. Stock {count}. Give one to Rowan.",action='rowan_submit:'+key))
        result.append(self.back_arrow('rowan_back','Back to village','return_scene'))
        return result

    def submit_rowan_crop(self, seed):
        if self.current_page!='rowan_submit' or not self.rowan_submit_open or self.rowan_stage!='vegetable_requested':return self.response()
        if seed not in self.config['seeds'] or self.resources['crops'].get(seed,0)<1:
            return self.response(tts='No vegetable to give.')
        self.resources['crops'][seed]-=1
        self.resources['coin']+=self.config['rowan']['vegetable_reward_gold']
        self.rowan_stage='done'
        return self.show_rowan(f"Thank you! This is just what I needed. Here's {self.config['rowan']['vegetable_reward_gold']} gold.",events=[{'kind':'one_shot','sound':'coin'}])

    def draw_rowan(self, obj):
        self.icons.draw(obj)

    def draw_calendar(self, obj):
        self.icons.draw(obj)