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
                width=12,height=9,hit_width=12,hit_height=9,label=day['name'],
                selected=i==self.weekday_index(), tts=self.calendar_text(i), action=f'calendar_day:{i}'))
        result.append(self.back_arrow('calendar_back','Back to shop','return_shop_choice'))
        return result

    def rowan_object(self):
        return dict(id='town_rowan',type='rowan',x=24,y=7,width=12,height=10,hit_width=14,hit_height=12,
                    label='Rowan',tts='Rowan. Quest available.' if self.rowan_stage!='done' else 'Rowan.',
                    quest_available=self.rowan_stage!='done',action='talk_rowan')

    def show_rowan(self, text, page='rowan_dialogue', events=None):
        self.rowan_dialogue=text
        self.current_page='rowan_submit' if page=='rowan_submit' else 'town'
        self.rowan_submit_open = page=='rowan_submit'
        self.clear_hover()
        # A conversation keeps the village open. Mark Rowan as already hovered
        # so the next tracking sample cannot replace the quest narration.
        # Leaving the object clears this normally in pointer_move().
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
                    item_kind='crop',x=8+16*len(result),y=22,width=12,height=9,hit_width=12,hit_height=9,
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
        """중간줄·아랫줄의 닷 그래픽(상점 건물, 로완, 상/하/좌 길 끝 화살표) 클릭 히트박스"""
        return [
            dict(id='town_scene_shop', type='town_hitbox', skip_grid=True,
                 x=43, y=24, width=22, height=16, hit_width=22, hit_height=16,
                 label='Shop building', tts='Shop. Buy or sell.', action='open_shop'),
            dict(id='town_scene_rowan', type='town_hitbox', skip_grid=True,
                 x=28, y=26, width=7, height=9, hit_width=8, hit_height=10,
                 label='Rowan', tts='Rowan. Quest available.' if self.rowan_stage != 'done' else 'Rowan.',
                 action='talk_rowan'),
            dict(id='town_road_mine', type='town_hitbox', skip_grid=True,
                 x=18, y=15, width=9, height=6, hit_width=11, hit_height=7,
                 label='Path to Mine', tts='Mine. Go north.', action='travel:mine'),
            dict(id='town_road_fishing', type='town_hitbox', skip_grid=True,
                 x=18, y=36, width=9, height=6, hit_width=11, hit_height=7,
                 label='Path to Fishing lake', tts='Fishing lake. Go south.', action='travel:fishing'),
            dict(id='town_road_home', type='town_hitbox', skip_grid=True,
                 x=4, y=26, width=7, height=9, hit_width=9, hit_height=11,
                 label='Path to Home', tts='Home. Go west.', action='travel:home'),
        ]

    def draw_town_scene(self):
        """
        마을 맨 윗줄(y:0~10) 아래에 실선(y=11)을 긋고,
        중간줄·아랫줄(y:12~39)에 길과 실제 상점 집 건물, 길 끝 화살표를 렌더링.
        """
        pad = self.dotpad
        # 1. 맨 윗줄 버튼 영역과 하단 공간 영역을 나누는 가로 실선 구분선 (y = 11)
        pad.draw_line(0, 11, pad.width - 1, 11)

        # 2. 가로·세로 T자형 마을 길 (세로 길 x: 14~22, 가로 길 y: 23~29)
        for y in range(12, pad.height):
            if not (23 <= y <= 29):
                pad.set_dot(14, y)
                pad.set_dot(22, y)
            # 길 내부 잔돌 질감
            if y % 3 == 1 and 18 <= y <= 33:
                pad.set_dot(16 if (y // 3) % 2 == 0 else 20, y)

        for x in range(0, 32):
            if not (14 < x < 22):
                pad.set_dot(x, 23)
                pad.set_dot(x, 29)
            if x % 4 == 2 and 7 <= x <= 25:
                pad.set_dot(x, 26)

        # 3. 상행 길 끝 화살표 ▲ (광산 이동: x=18, y=13~16)
        self.draw_icon_pattern(18, 15, (
            '0001000',
            '0011100',
            '0111110',
            '1111111',
        ))

        # 4. 하행 길 끝 화살표 ▼ (낚시터 이동: x=18, y=35~38)
        self.draw_icon_pattern(18, 37, (
            '1111111',
            '0111110',
            '0011100',
            '0001000',
        ))

        # 5. 좌측 길 끝 화살표 ◀ (집 이동: x=2~5, y=26)
        self.draw_icon_pattern(3, 26, (
            '0001',
            '0011',
            '0111',
            '1111',
            '0111',
            '0011',
            '0001',
        ))

        # 6. 상점 옆 로완(Rowan) 서 있는 실루엣 (x=28, y=26)
        self.draw_icon_pattern(28, 26, (
            '01110',
            '01110',
            '11111',
            '01110',
            '01010',
        ))

        # 7. 우측 실제 상점 집 건물 닷 그래픽 (x: 33~53, y: 14~33)
        # 박공지붕 (y: 14~20, 기와 질감 포함)
        for dy in range(7):
            half = 4 + dy
            y = 14 + dy
            for x in range(43 - half, 43 + half + 1):
                if dy in (0, 6) or x in (43 - half, 43 + half) or (x + dy) % 2 == 0:
                    pad.set_dot(x, y)

        # 건물 외벽 (x: 34~52, y: 21~33)
        for y in range(21, 34):
            pad.set_dot(34, y)
            pad.set_dot(52, y)
            # 벽돌 질감 표현
            if y in (21, 33):
                for x in range(34, 53):
                    pad.set_dot(x, y)
            elif y % 2 == 1:
                for x in range(36, 51, 4):
                    if not (40 <= x <= 46 and y >= 26):
                        pad.set_dot(x, y)

        # 좌/우 창문 (채움 사각형)
        for wy in (24, 25):
            for wx in (37, 38, 48, 49):
                pad.set_dot(wx, wy)

        # 중앙 출입문 (x: 41~45, y: 26~33)
        for y in range(26, 34):
            pad.set_dot(41, y)
            pad.set_dot(45, y)
        for x in range(41, 46):
            pad.set_dot(x, 26)
        pad.set_dot(44, 30)  # 문고리