"""Houseplant growth, contact watering and tactile silhouettes.

Engine attributes (save format): flower_seeds, houseplant, flower_watering,
flower_contact_at. Shared state written: resources["coin"], current_page,
last_pointer.
"""
import random
import time

from engine.core import order
from engine.core.registry import Feature


FLOWER_STAGE_PATTERNS = {
    'empty': (
        '0000000',
        '0000000',
        '0000000',
        '0111110',
        '0011100',
    ),
    'sprout': (
        '0000000',
        '0010100',
        '0001000',
        '0111110',
        '0011100',
    ),
    'stem': (
        '0001000',
        '0111000',
        '0001110',
        '0111110',
        '0011100',
    ),
    'flower': (
        '0111110',
        '1111111',
        '0111110',
        '0111110',
        '0011100',
    ),
    'withered': (
        '0000000',
        '0011000',
        '0001100',
        '0111110',
        '0011100',
    ),
}


class Flowers(Feature):
    name = "flowers"

    def register(self, reg):
        reg.owns("flower_seeds", "houseplant", "flower_watering", "flower_contact_at")
        reg.page("flower_detail", name="Flower pot", objects=self.page_objects,
                 pointer_move=self.pointer, pointer_drag=self.pointer)
        reg.action("flower:", self.action, before_night_guard=True)
        reg.renderer("flower_pot", self.draw_pot)
        reg.icon("flower_pot", pattern=self.icon_pattern, skip=lambda obj: obj.get('width', 12) > 12, layout_order=3)
        reg.icon_alias("flower_seed", "seed")
        reg.state("flowers", self.public_state)
        reg.on("reset", self.reset, order=order.Reset.FLOWERS)
        reg.on("end_of_day", self.advance, order=order.EndOfDay.FLOWERS)
        reg.on("before_navigation", self.stop_contact, order=order.BeforeNavigation.FLOWERS)
        reg.save_fields(transient={"flower_contact_at": None, "flower_watering": False},
                        defaults=("flower_seeds", "houseplant", "flower_watering", "flower_contact_at"))
        reg.contribute("home.objects", lambda: [self.pot_object()], order=order.HomeObjects.FLOWERS)
        reg.contribute("home.scene_objects", self.home_scene_objects, order=order.HomeSceneObjects.FLOWERS)
        reg.contribute("home.scene", self.draw_home_pot, order=order.HomeScene.FLOWERS)
        reg.contribute("inventory.items", self.inventory_items, order=order.InventoryItems.FLOWERS)
        reg.contribute("shop.buy_items", self.shop_buy_items, order=order.ShopBuyItems.FLOWERS)
        reg.shop_item("flower_seed", self.buy_seed, market_price=False)
        reg.contribute("harvest.bonus", self.harvest_bonus, order=order.HarvestBonus.FLOWERS)

    def config(self):
        return self.engine.config.get('flowers', {})

    def reset(self):
        e = self.engine
        e.flower_seeds = 0
        e.houseplant = self.empty_houseplant()
        e.flower_watering = False
        e.flower_contact_at = None

    @staticmethod
    def empty_houseplant():
        return dict(species=None, stage='empty', growth=0, watered=False,
                    water_seconds=0.0, dry_days=0, bloom_days=0, bloom_cycles=0)

    def stop_contact(self):
        e = self.engine
        e.flower_contact_at = None
        e.flower_watering = False

    def public_state(self):
        e = self.engine
        p = e.houseplant
        contact = (e.current_page == 'flower_detail' and e.flower_watering
                   and not e.paused and not e.day_ended and e.sleep_until is None
                   and e.flower_contact_at is not None
                   and time.monotonic()-e.flower_contact_at < self.config().get('contact_gap_seconds', .5))
        return dict(stage=p['stage'], species=p['species'], watered=p['watered'],
                    water_progress=min(1, p['water_seconds']/self.config().get('watering_seconds', 3)),
                    watering=e.flower_watering, contact=bool(contact))

    def description(self):
        p = self.engine.houseplant
        if p['stage'] == 'empty': return 'Flower pot. Empty. Select to plant.'
        if p['stage'] == 'withered': return 'Flower pot. Withered. Empty the pot.'
        return 'Flower pot. '+p['stage'].capitalize()+'. '+('Watered.' if p['watered'] else 'Needs water.')

    def pot_object(self, detail=False):
        if not detail:
            return dict(
                id='houseplant', type='flower_pot',
                x=50, y=6, width=12, height=10,
                hit_width=10, hit_height=8,
                label='Flower pot',
                tts=self.description(),
                action='flower:open'
            )
        return dict(
            id='houseplant', type='flower_pot',
            x=30, y=26, width=36, height=24,
            hit_width=36, hit_height=24,
            label='Flower pot',
            tts=self.description(),
            action=''
        )

    def page_objects(self):
        p = self.engine.houseplant
        buttons = [('empty', 'Empty pot', 'tool')]
        if p['stage'] == 'empty': buttons = [('plant','Plant morning glory','plant')]
        elif p['stage'] != 'withered': buttons.insert(0, ('water','Water','water'))
        result = [dict(id='flower_'+action, type='care_button', care_kind=kind,
                       x=8+14*i, y=6, width=12,height=10,hit_width=12,hit_height=10,
                       label=label,tts=label+'.',action='flower:'+action)
                  for i,(action,label,kind) in enumerate(buttons)]
        return result+[self.pot_object(True), self.engine.back_arrow('flower_back','Home','return_scene')]

    def action(self, action, obj):
        e = self.engine
        if e.day_ended: return e.night_only_response()
        if action == 'open':
            self.stop_contact()
            e.set_page('flower_detail')
        elif e.current_page != 'flower_detail': return e.response()
        elif action == 'plant':
            if e.houseplant['stage'] != 'empty': return e.response()
            if e.flower_seeds <= 0: return e.response(tts='Buy morning glory seeds at the shop.')
            e.flower_seeds -= 1
            e.houseplant = self.empty_houseplant()
            e.houseplant.update(species='morning_glory',stage='sprout')
        elif action == 'empty':
            self.stop_contact()
            e.houseplant = self.empty_houseplant()
        elif action == 'water':
            if e.houseplant['stage'] in ('empty','withered'): return e.response()
            if e.houseplant['watered']: return e.response(tts='Already watered.')
            e.flower_watering = True
            e.flower_contact_at = None
            return e.response(tts='Keep your hand over the pot to water.')
        e.clear_hover()
        e.render()
        return e.response(tts=self.description())

    def pointer(self, x, y):
        """Pointer move/drag on the flower page while watering; otherwise the core handler runs."""
        if self.engine.flower_watering:
            return self.water_at(x, y)
        return None

    def water_at(self, x, y):
        e = self.engine
        e.last_pointer = (x,y)
        now = time.monotonic()
        eligible = (e.flower_watering and not e.paused and not e.day_ended
                    and e.sleep_until is None and e.houseplant['stage'] not in ('empty','withered'))
        # This target is the same bottom silhouette used by draw_pot.
        inside = (int(round(x)), int(round(y))) in self.pot_dots(True)
        previous = e.flower_contact_at
        e.flower_contact_at = now if eligible and inside else None
        if eligible and inside and previous is not None:
            delta = now-previous
            if 0 <= delta <= self.config().get('contact_gap_seconds', .5):
                e.houseplant['water_seconds'] += delta
            if e.houseplant['water_seconds'] >= self.config().get('watering_seconds', 3):
                e.houseplant.update(watered=True,dry_days=0)
                self.stop_contact()
                e.render()
                return e.response(tts='Flower pot watered.', sound_events=[{'kind':'correct','activity':'flower','count':1}])
        return e.response()

    def advance(self):
        self.stop_contact()
        p, cfg = self.engine.houseplant, self.config()
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

    def harvest_bonus(self):
        return self.config().get('harvest_bonus',1) if self.engine.houseplant['stage']=='flower' else 0

    def buy_seed(self, item_id):
        if item_id != "morning_glory": return None
        e = self.engine
        price = int(self.config().get('seed_price',150))
        if e.resource('coin') < price: return e.response(tts=f'Not enough gold. Morning glory seeds cost {price} gold.',sfx='error')
        e.add_resource('coin', -price)
        e.flower_seeds += 1
        e.render()
        return e.response(tts='Bought morning glory seeds.',sound_events=[{'kind':'one_shot','sound':'coin'}])

    def shop_buy_items(self):
        return [("flower_seed", "morning_glory", "Morning glory seeds", self.engine.flower_seeds, int(self.config().get("seed_price",150)))]

    def inventory_items(self):
        return [dict(id='seed_morning_glory', label='Morning glory seeds', count=self.engine.flower_seeds, kind='seed', seed_id='morning_glory', action='')]

    def icon_pattern(self, obj):
        stage = self.engine.houseplant.get('stage', 'empty')
        return FLOWER_STAGE_PATTERNS.get(stage, FLOWER_STAGE_PATTERNS['empty'])

    # ---- home scene ----

    def scene_bounds(self):
        stage = self.engine.houseplant.get('stage', 'empty')
        bounds = {
            'empty':    (12, 36, 7, 3, 9, 4),
            'sprout':   (12, 34, 7, 6, 9, 7),
            'withered': (12, 34, 9, 6, 11, 7),
            'stem':     (12, 33, 9, 9, 11, 10),
            'flower':   (12, 31, 11, 12, 13, 12)
        }
        return bounds.get(stage, bounds['empty'])

    def home_scene_objects(self):
        fx, fy, fw, fh, fhw, fhh = self.scene_bounds()
        return [dict(id='home_scene_flower', type='home_hitbox', skip_grid=True,
                     x=fx, y=fy, width=fw, height=fh, hit_width=fhw, hit_height=fhh,
                     label='Flower pot', tts=self.description(), action='flower:open')]

    def draw_home_pot(self):
        e = self.engine
        pad = e.dotpad
        stage = e.houseplant.get('stage', 'empty')
        pot_cx = 12

        for x in range(pot_cx - 3, pot_cx + 4):
            pad.set_dot(x, 35, 1)
        for x in range(pot_cx - 2, pot_cx + 3):
            pad.set_dot(x, 36, 1)
            pad.set_dot(x, 37, 1)
        pad.set_dot(pot_cx, 36, 0)

        if stage == 'sprout':
            pad.set_dot(pot_cx, 34, 1)
            pad.set_dot(pot_cx, 33, 1)
            pad.set_dot(pot_cx - 1, 32, 1)
            pad.set_dot(pot_cx - 2, 32, 1)
            pad.set_dot(pot_cx + 1, 32, 1)
            pad.set_dot(pot_cx + 2, 32, 1)

        elif stage == 'withered':
            pad.set_dot(pot_cx, 34, 1)
            pad.set_dot(pot_cx + 1, 33, 1)
            pad.set_dot(pot_cx + 2, 33, 1)
            pad.set_dot(pot_cx + 3, 34, 1)
            pad.set_dot(pot_cx - 1, 33, 1)
            pad.set_dot(pot_cx - 2, 34, 1)

        elif stage == 'stem':
            for px, py in [
                (pot_cx, 34), (pot_cx, 33), (pot_cx - 1, 32),
                (pot_cx, 31), (pot_cx + 1, 30), (pot_cx, 29),
                (pot_cx - 2, 32), (pot_cx - 3, 32), (pot_cx - 3, 31),
                (pot_cx + 2, 30), (pot_cx + 3, 30), (pot_cx + 3, 29),
            ]:
                pad.set_dot(px, py, 1)

        elif stage == 'flower':
            for px, py in [
                (pot_cx, 34), (pot_cx, 33), (pot_cx - 1, 32),
                (pot_cx, 31), (pot_cx + 1, 30), (pot_cx, 29),
                (pot_cx - 2, 32), (pot_cx - 3, 32), (pot_cx - 3, 31), (pot_cx - 2, 31),
                (pot_cx + 2, 30), (pot_cx + 3, 30), (pot_cx + 3, 29), (pot_cx + 2, 29),
            ]:
                pad.set_dot(px, py, 1)

            e.draw_solid_pattern(pot_cx, 27, (
                '.11111.',
                '1100011',
                '.11111.',
            ))

    # ---- detail page drawing ----

    @staticmethod
    def pot_dots(detail=False):
        """The visible pot and watering hit area share exactly the same pixels."""
        cx = 30 if detail else 15
        half = 10 if detail else 8
        dots = set()
        for y in range(32, 38):
            extent = half if y < 34 else half-2-(y-34)//2
            for x in range(cx-extent, cx+extent+1):
                dots.add((x,y))
        return dots

    def draw_pot(self, obj):
        detail = obj['width'] > 26
        cx = int(obj['x'])
        stage = self.engine.houseplant['stage']
        pad = self.engine.dotpad

        # 화분 본체 (물주기 판정 영역과 동일하게 유지)
        for x, y in self.pot_dots(detail):
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
