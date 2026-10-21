"""Shared tactile slots and frame/symbol composition (3 rows by 4 columns)."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class IconGrid:
    rows: int = 3
    columns: int = 4
    width: int = 12
    height: int = 10

    def place(self, objects, screen_width=60, screen_height=40, used_columns=None):
        """Return copies; a restricted grid uses the left columns, never resizes cells."""
        columns = self.columns if used_columns is None else used_columns
        if not 1 <= columns <= self.columns:
            raise ValueError('Invalid active column count')
        if len(objects) > self.rows * columns:
            raise ValueError('Icon page exceeds grid capacity; paginate its items first')
        pitch_x = (screen_width - 4) // self.columns
        pitch_y = (screen_height - 1) // self.rows
        if pitch_x < self.width + 2 or pitch_y < self.height + 2:
            raise ValueError('Display is too small for separated icon frames')
        result = []
        for index, original in enumerate(objects):
            row, col = divmod(index, columns)
            obj = dict(original)
            obj.update(x=2+self.width//2+col*pitch_x,
                       y=1+self.height//2+row*pitch_y,
                       width=self.width, height=self.height,
                       hit_width=self.width-2, hit_height=self.height-2,
                       grid_row=row, grid_column=col, grid_slot=row*self.columns+col)
            result.append(obj)
        return result


@dataclass(frozen=True)
class IconSpec:
    frame: str = 'rectangle'
    symbol: str = 'material'
    pattern: tuple = ()


class IconRenderer:
    """One thin frame plus one filled semantic symbol; optional selection/progress overlays."""
    TYPES = frozenset(('bed','chest','stove','shop_npc','rowan','calendar_day',
        'calendar_button','save_slot','plot','seed','resource','research','care_button',
        'recipe','ingredient','cooking_start','shop_choice','shop_item','watering_can',
        'fertilizer','flower_pot','nav_up','nav_down'))

    # 내부를 채워 형태별로 확실히 구분되는 솔리드 아이콘 (침대/물주기 구분감 유지)
    PATTERNS = {
        'seed': ('01110','11111','01110'),
        'crop': ('00100','01110','11111','11111','01110'),
        'fish': ('0011000','0111101','1111111','0111101','0011000'),
        'mineral': ('00100','01110','11111','01110','00100'),
        'tool': ('11111','11111','00100','00100','00100'),
        'material': ('11111','11111','11111'),
        'food': ('0111110','1111111','0111110'),
        'coin': ('01110','11111','11111','01110'),
        # 침대: 좌측 베개/헤드보드 돌출 + 매트리스 채움 유지
        'bed': ('1100000','1100000','1111111','1111111','1111111'),
        # 연구 상자: 채워진 상자 + 상단 탭
        'chest': ('0111110','1111111','1111111','1111111','1111111'),
        # 주방(스토브): 냄비/불꽃이 올라온 채움 실루엣
        'stove': ('0010100','0111110','1111111','1111111','0111110'),
        # 상점: 삼각형 지붕 처마 + 채워진 건물
        'shop_npc': ('0011100','0111110','1111111','0111110','0111110'),
        # 로완(NPC): 머리 + 채워진 상체
        'rowan': ('0011100','0011100','0111110','1111111','1111111'),
        'calendar': ('10101','11111','11111','11111','11111'),
        'save': ('11110','11111','11111','11111','11111'),
        # 물주기: 물방울/물통 채움 형태 유지
        'water': ('00100','01110','11111','11111','01110'),
        'harvest': ('10101','11111','11111','01110','00100'),
        'start': ('01000','01100','01110','01100','01000'),
        'sell': ('0111110','1111000','0111110','0001111','0111110'),
        'buy': ('1111100','1111110','1111100','1111110','1111100'),
        'check': ('000001','000011','100110','111100','011000'),
        # 광산(상행) / 낚시터(하행) 이동 버튼 아이콘
        'nav_up': ('0001000','0011100','0111110','1111111','0011100'),
        'nav_down': ('0011100','1111111','0111110','0011100','0001000'),
    }

    # 집 상단 바의 소형 나팔꽃 아이콘 (성장 단계에 따라 잎과 꽃이 늘어나는 형태)
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

    ALIASES = dict.fromkeys(('stone','copper','iron','diamond'), 'mineral') | dict.fromkeys(('pickaxe','fertilizer','fishing_rod'), 'tool')

    def __init__(self, engine):
        self.engine = engine
        self.dotpad = engine.dotpad

    @classmethod
    def category(cls, kind):
        return 'seed' if kind == 'flower_seed' else cls.ALIASES.get(kind, kind or 'material')

    def spec(self, obj):
        kind = obj.get('type')
        symbol = kind
        frame = 'rectangle'
        pattern = ()
        if kind == 'flower_pot':
            stage = self.engine.houseplant.get('stage', 'empty')
            pattern = self.FLOWER_STAGE_PATTERNS.get(stage, self.FLOWER_STAGE_PATTERNS['empty'])
        elif kind == 'resource': symbol = self.category(obj.get('resource_kind'))
        elif kind == 'shop_item': symbol = self.category(obj.get('shop_kind'))
        elif kind == 'recipe': symbol = 'food'
        elif kind == 'ingredient': symbol = 'check' if obj.get('selected') else self.category(obj.get('item_kind','crop'))
        elif kind == 'care_button': symbol = {'plant':'seed','fertilizer':'tool'}.get(obj.get('care_kind'),obj.get('care_kind'))
        elif kind == 'watering_can': symbol = 'water'
        elif kind == 'fertilizer': symbol = 'tool'
        elif kind == 'shop_choice': symbol = obj.get('choice')
        elif kind in ('calendar_day','calendar_button'): symbol = 'calendar'
        elif kind == 'save_slot': symbol = 'save'
        elif kind == 'cooking_start': symbol = 'start'
        elif kind == 'research':
            key = obj.get('research_kind')
            symbol = {'seed_return':'seed','field_expand':'tool','mineral_luck':'mineral'}.get(key,'chest')
        if symbol == 'food': frame = 'double_rectangle'
        elif kind == 'rowan' and obj.get('quest_available'): frame = 'quest_rectangle'
        elif symbol == 'coin': frame = 'rectangle'
        return IconSpec(frame, symbol, pattern)

    def frame(self, obj, shape='rectangle'):
        """외곽 1줄을 제거해 1줄 두께의 작고 얇은 프레임(11x9)으로 렌더링."""
        if shape == 'ellipse': shape = 'double_rectangle'
        x, y = round(obj['x']), round(obj['y'])
        rx = max(2, int(obj.get('width', 12)) // 2 - 1)
        ry = max(2, int(obj.get('height', 10)) // 2 - 1)

        if shape == 'quest_rectangle':
            self.dotpad.draw_box(x, y, 2 * rx, 2 * ry)
            self.dotpad.draw_box(x, y, 2 * (rx - 1), 2 * (ry - 1))
            return
        if shape in ('rectangle', 'double_rectangle'):
            insets = (0, 2) if shape == 'double_rectangle' else (0,)
            for inset in insets:
                w = max(2, 2 * (rx - inset))
                h = max(2, 2 * (ry - inset))
                self.dotpad.draw_box(x, y, w, h)
            return
        self.dotpad.draw_box(x, y, 2 * rx, 2 * ry)

    def pattern(self, x, y, rows):
        self.engine.draw_icon_pattern(x, y, rows)

    def catalog(self, obj, kind):
        symbol = self.category(kind)
        self.frame(obj, 'double_rectangle' if symbol == 'food' else 'rectangle')
        if symbol != 'food':
            self.pattern(obj['x'], obj['y'], self.PATTERNS.get(symbol, self.PATTERNS['material']))

    def draw(self, obj):
        if obj.get('type') not in self.TYPES: return False
        if obj.get('type') == 'flower_pot' and obj.get('width', 12) > 12:
            return False
        spec = self.spec(obj)
        self.frame(obj, spec.frame)
        if spec.frame == 'double_rectangle':
            return True
        if obj['type'] == 'plot':
            state = self.engine.farm_plots.get(obj['id'], self.engine.new_plot_state())
            if state.get('seed_id'):
                days = max(1, self.engine.get_seed_config(state['seed_id']).get('growth_days', 3))
                ratio = 1 if state.get('mature') else min(1, max(0, state['growth'] / days))
                rx = max(2, obj['width'] // 2 - 1)
                ry = max(2, obj['height'] // 2 - 1)
                count = math.ceil((2 * ry - 1) * ratio)
                for y in range(obj['y'] + ry - count, obj['y'] + ry):
                    for x in range(obj['x'] - rx + 1, obj['x'] + rx):
                        self.dotpad.set_dot(x, y)
        else:
            rows = spec.pattern or self.PATTERNS.get(spec.symbol, self.PATTERNS['material'])
            if spec.frame == 'quest_rectangle' and spec.symbol == 'rowan':
                rows = ('00100', '01110', '11111')
            self.pattern(obj['x'], obj['y'], rows)
        return True


class IconLayout:
    """Page policy over the same twelve virtual slots."""
    PAGES = frozenset(('home','town','farm','inventory','research','seed_select',
        'recipe_select','ingredient_select','shop_choice','shop_buy','shop_sell',
        'load_game','shop_calendar','rowan_dialogue','rowan_submit'))

    def __init__(self, grid=None):
        self.grid = grid or IconGrid()

    def arrange(self, page, objects, width, height):
        objects = [dict(o) for o in objects]
        if page not in self.PAGES and page != 'plot_detail': return objects
        chosen = [o for o in objects if o.get('type') in IconRenderer.TYPES
                  and not o.get('skip_grid')
                  and (page != 'plot_detail' or o.get('type') == 'care_button')]
        if page in ('home', 'town'):
            order = {
                'bed': 0, 'chest': 1, 'stove': 2, 'flower_pot': 3,
                'shop_npc': 0, 'rowan': 1, 'nav_up': 2, 'nav_down': 3
            }
            chosen.sort(key=lambda o: order.get(o['type'], 9))
        placed = self.grid.place(chosen, width, height, used_columns=2 if page == 'farm' else None)
        by_id = {o['id']: o for o in placed}
        return [by_id.get(o.get('id'), o) for o in objects]