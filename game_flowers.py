"""Houseplant growth, contact watering and tactile silhouettes."""
import random
import time


class FlowerMixin:
    def flower_config(self):
        return self.config.get('flowers', {})

    def reset_flowers(self):
        self.flower_seeds = 0
        self.houseplant = self.empty_houseplant()
        self.flower_watering = False
        self.flower_contact_at = None

    @staticmethod
    def empty_houseplant():
        return dict(species=None, stage='empty', growth=0, watered=False,
                    water_seconds=0.0, dry_days=0, bloom_days=0, bloom_cycles=0)

    def stop_flower_contact(self):
        self.flower_contact_at = None
        self.flower_watering = False

    def flower_public_state(self):
        p = self.houseplant
        contact = (self.current_page == 'flower_detail' and self.flower_watering
                   and not self.paused and not self.day_ended and self.sleep_until is None
                   and self.flower_contact_at is not None
                   and time.monotonic()-self.flower_contact_at < self.flower_config().get('contact_gap_seconds', .5))
        return dict(stage=p['stage'], species=p['species'], watered=p['watered'],
                    water_progress=min(1, p['water_seconds']/self.flower_config().get('watering_seconds', 3)),
                    watering=self.flower_watering, contact=bool(contact))

    def flower_description(self):
        p = self.houseplant
        if p['stage'] == 'empty': return 'Flower pot. Empty. Select to plant.'
        if p['stage'] == 'withered': return 'Flower pot. Withered. Empty the pot.'
        return 'Flower pot. '+p['stage'].capitalize()+'. '+('Watered.' if p['watered'] else 'Needs water.')

    def flower_object(self, detail=False):
        return dict(id='houseplant', type='flower_pot', x=30 if detail else 15,
                    y=26, width=36 if detail else 26, height=24,
                    hit_width=36 if detail else 26, hit_height=24,
                    label='Flower pot',
                    tts=self.flower_description(), action='' if detail else 'flower:open')

    def get_flower_objects(self):
        p = self.houseplant
        buttons = [('empty', 'Empty pot', 'tool')]
        if p['stage'] == 'empty': buttons = [('plant','Plant morning glory','plant')]
        elif p['stage'] != 'withered': buttons.insert(0, ('water','Water','water'))
        result = [dict(id='flower_'+action, type='care_button', care_kind=kind,
                       x=8+14*i, y=6, width=12,height=10,hit_width=12,hit_height=10,
                       label=label,tts=label+'.',action='flower:'+action)
                  for i,(action,label,kind) in enumerate(buttons)]
        return result+[self.flower_object(True), self.back_arrow('flower_back','Home','return_scene')]

    def flower_action(self, action):
        if self.day_ended: return self.night_only_response()
        if action == 'open':
            self.stop_flower_contact()
            self.current_page = 'flower_detail'
        elif self.current_page != 'flower_detail': return self.response()
        elif action == 'plant':
            if self.houseplant['stage'] != 'empty': return self.response()
            if self.flower_seeds <= 0: return self.response(tts='Buy morning glory seeds at the shop.')
            self.flower_seeds -= 1
            self.houseplant = self.empty_houseplant()
            self.houseplant.update(species='morning_glory',stage='sprout')
        elif action == 'empty':
            self.stop_flower_contact()
            self.houseplant = self.empty_houseplant()
        elif action == 'water':
            if self.houseplant['stage'] in ('empty','withered'): return self.response()
            if self.houseplant['watered']: return self.response(tts='Already watered.')
            self.flower_watering = True
            self.flower_contact_at = None
            return self.response(tts='Keep your hand over the pot to water.')
        self.clear_hover()
        self.render()
        return self.response(tts=self.flower_description())

    def water_flower_at(self, x, y):
        self.last_pointer = (x,y)
        now = time.monotonic()
        eligible = (self.flower_watering and not self.paused and not self.day_ended
                    and self.sleep_until is None and self.houseplant['stage'] not in ('empty','withered'))
        # This target is the same bottom silhouette used by draw_flower_pot.
        inside = (int(round(x)), int(round(y))) in self.flower_pot_dots(True)
        previous = self.flower_contact_at
        self.flower_contact_at = now if eligible and inside else None
        if eligible and inside and previous is not None:
            delta = now-previous
            if 0 <= delta <= self.flower_config().get('contact_gap_seconds', .5):
                self.houseplant['water_seconds'] += delta
            if self.houseplant['water_seconds'] >= self.flower_config().get('watering_seconds', 3):
                self.houseplant.update(watered=True,dry_days=0)
                self.stop_flower_contact()
                self.render()
                return self.response(tts='Flower pot watered.', sound_events=[{'kind':'correct','activity':'flower','count':1}])
        return self.response()

    def advance_flowers(self):
        self.stop_flower_contact()
        p, cfg = self.houseplant, self.flower_config()
        if p['stage'] in ('empty','withered'): return
        p['dry_days'] = 0 if p['watered'] else p['dry_days']+1
        if p['stage'] == 'flower':
            p['bloom_days'] += 1
            if p['bloom_days'] >= cfg.get('bloom_cycle_days', 3):
                p['bloom_days'] = 0
                p['bloom_cycles'] += 1
        elif p['watered']:
            p['growth'] += 1
            if p['growth'] >= cfg.get(p['stage']+'_days', 2):
                p['growth'] = 0
                p['stage'] = 'stem' if p['stage'] == 'sprout' else 'flower'
                if p['stage'] == 'flower': p['bloom_cycles'] = 1
        chance = min(1.0, p['dry_days']*cfg.get('dry_wilt_increment', .3)
                     +p['bloom_cycles']*cfg.get('bloom_wilt_increment', .1))
        if chance > 0 and random.random() < chance: p['stage'] = 'withered'
        p.update(watered=False,water_seconds=0.0)

    def flower_harvest_bonus(self):
        return self.flower_config().get('harvest_bonus',1) if self.houseplant['stage']=='flower' else 0

    def buy_flower_seed(self):
        price = int(self.flower_config().get('seed_price',150))
        if self.resources['coin'] < price: return self.response(tts=f'Not enough gold. Morning glory seeds cost {price} gold.',sfx='error')
        self.resources['coin'] -= price
        self.flower_seeds += 1
        self.render()
        return self.response(tts='Bought morning glory seeds.',sound_events=[{'kind':'one_shot','sound':'coin'}])

    @staticmethod
    def flower_pot_dots(detail=False):
        """The visible pot and watering hit area share exactly the same pixels."""
        cx = 30 if detail else 15
        half = 10 if detail else 8
        dots = set()
        for y in range(32, 38):
            extent = half if y < 34 else half-2-(y-34)//2
            for x in range(cx-extent, cx+extent+1):
                dots.add((x,y))
        return dots

    def draw_flower_pot(self, obj):
        detail = obj['width'] > 26
        cx = int(obj['x'])
        stage = self.houseplant['stage']
        pad = self.dotpad

        # 화분 본체 (물주기 판정 영역과 동일하게 유지)
        for x, y in self.flower_pot_dots(detail):
            pad.set_dot(x, y)

        def stamp(x, y, rows, clear_zero=False):
            for dy, row in enumerate(rows):
                for dx, v in enumerate(row):
                    if v == '1':
                        pad.set_dot(x + dx, y + dy, 1)
                    elif v == '0' and clear_zero:
                        pad.set_dot(x + dx, y + dy, 0)

        def plot(pts):
            for dx, dy in pts:
                pad.set_dot(cx + dx, dy)

        if stage == 'empty':
            return

        # 1. 새싹 (Sprout): 쌍떡잎이 하트 모양으로 활짝 펼쳐진 모습
        if stage == 'sprout':
            plot([(0, 31), (0, 30), (0, 29), (-1, 28), (1, 28)])
            stamp(cx - 6, 25, (
                '01100000110',
                '11110001111',
                '01111011110',
                '00111111100',
            ))
            return

        # 2. 시든 상태 (Withered): 아래로 힘없이 처진 줄기와 말라붙은 꽃잎
        if stage == 'withered':
            plot([
                (0, 31), (0, 30), (-1, 29), (-2, 28), (-2, 27), (-1, 26),
                (0, 25), (1, 24), (2, 23), (3, 24), (4, 25), (5, 26),
                (-2, 26), (-4, 27), (-5, 28), (-6, 29)
            ])
            stamp(cx - 8, 29, ('0110', '1110', '0101', '0010'))
            stamp(cx + 4, 26, ('1100', '1110', '0111', '0010'))
            return

        # 나팔꽃 하트형 잎사귀 패턴 (좌/우)
        leaf_left = (
            '0110110',
            '1111111',
            '0111110',
            '0011100',
            '0001000',
        )
        leaf_right = (
            '0110110',
            '1111111',
            '0111110',
            '0011100',
            '0001000',
        )

        # 3. 줄기 성장 단계 (Stem): S자 덩굴 + 하트 잎사귀 + 말린 덩굴손
        if stage == 'stem':
            vine = [
                (0, 31), (0, 30), (-1, 29), (-1, 28), (0, 27),
                (1, 26), (1, 25), (0, 24), (-1, 23), (-1, 22),
                (0, 21), (1, 20), (1, 19), (0, 18), (-1, 17), (0, 16)
            ]
            branches = [(-2, 28), (-3, 27), (2, 25), (3, 24), (-2, 22), (-3, 21)]
            plot(vine + branches)
            stamp(cx - 9, 25, leaf_left)
            stamp(cx + 3, 22, leaf_right)
            stamp(cx - 8, 18, ('01100', '11110', '01111', '00110'))
            return

        # 4. 개화 단계 (Flower): 상세 화면 vs 홈 화면 맞춤형 나팔꽃 연출
        if detail:
            # 부드러운 S자 메인 덩굴과 끝부분의 말린 덩굴손/꽃봉오리
            vine = [
                (0, 31), (0, 30), (1, 29), (1, 28), (0, 27), (-1, 26),
                (-1, 25), (0, 24), (1, 23), (2, 22), (1, 21), (0, 20),
                (-1, 19), (-1, 18), (0, 17), (1, 16), (2, 15), (3, 14), (2, 13)
            ]
            # 꽃자루(나팔 대롱으로 이어지는 가지)와 잎자루
            stems = [
                # 왼쪽 상단 큰 나팔꽃으로 이어지는 꽃받침/대롱
                (-2, 20), (-3, 20), (-4, 19),
                # 오른쪽 하단 나팔꽃으로 이어지는 꽃받침/대롱
                (2, 24), (3, 24), (4, 24),
                # 왼쪽 하단 하트 잎사귀 가지
                (-2, 27), (-3, 27), (-4, 28),
                # 오른쪽 상단 작은 꽃봉오리
                (3, 15), (4, 14), (5, 13), (4, 12), (5, 12)
            ]
            plot(vine + stems)

            # 왼쪽 아래 하트 모양 잎사귀
            stamp(cx - 10, 26, leaf_left)

            # 왼쪽 상단 메인 나팔꽃 (좌상향을 바라보는 나팔 실루엣 + 별 모양 중심부)
            # '.'은 배경 투명 유지, '0'은 줄기를 지워 꽃 안쪽(Throat) 여백 확보
            left_trumpet = (
                '...111111....',
                '.1111111111..',
                '111100011111.',
                '111001001111.',
                '1110100011111',
                '1110000111111',
                '.11111111111.',
                '..111111110..',
                '....11111....',
            )
            stamp(cx - 16, 13, left_trumpet, clear_zero=True)

            # 오른쪽 중하단 나팔꽃 (우측으로 활짝 핀 나팔 옆모습)
            right_trumpet = (
                '.....111111..',
                '...111111111.',
                '.111111000111',
                '1111100010111',
                '.111111000111',
                '...111111111.',
                '.....111111..',
            )
            stamp(cx + 3, 20, right_trumpet, clear_zero=True)

        else:
            # 홈 화면 (detail=False, cx=15): 좁은 폭에서도 나팔 형태가 한눈에 보이도록 구성
            vine = [
                (0, 31), (0, 30), (1, 29), (1, 28), (0, 27), (-1, 26),
                (-1, 25), (0, 24), (1, 23), (1, 22), (0, 21), (-1, 20),
                (0, 19), (1, 18), (2, 17), (1, 16)
            ]
            stems = [
                (-2, 21), (-3, 20),
                (2, 24), (3, 24),
                (-2, 27), (-3, 27),
            ]
            plot(vine + stems)

            # 왼쪽 아래 작은 하트 잎
            stamp(cx - 7, 26, (
                '01010',
                '11111',
                '01110',
                '00100',
            ))

            # 홈 화면용 왼쪽 상단 나팔꽃 (깔때기 대롱 + 활짝 핀 나팔 입구)
            home_left_trumpet = (
                '..11111...',
                '.1111111..',
                '111000111.',
                '1100101111',
                '1110001111',
                '.11111111.',
                '...1111...',
            )
            stamp(cx - 11, 15, home_left_trumpet, clear_zero=True)

            # 홈 화면용 오른쪽 나팔꽃 (오른쪽으로 벌어진 나팔 옆모습)
            home_right_trumpet = (
                '...11111.',
                '.11111111',
                '111100111',
                '.11111111',
                '...11111.',
            )
            stamp(cx + 2, 22, home_right_trumpet, clear_zero=True)
