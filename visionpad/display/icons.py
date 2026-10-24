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
    TYPES = frozenset(('bed','chest','stove',
        'save_slot','seed','resource','care_button',
        'watering_can',
        'fertilizer'))

    PATTERNS = {
        'seed': ('01110','11111','01110'),
        'crop': ('00100','01110','11111','11111','01110'),
        'fish': ('0011000','0111101','1111111','0111101','0011000'),
        'mineral': ('00100','01110','11111','01110','00100'),
        'tool': ('11111','11111','00100','00100','00100'),
        'material': ('11111','11111','11111'),
        'food': ('0111110','1111111','0111110'),
        'coin': ('01110','11111','11111','01110'),
        'bed': ('1100000','1100000','1111111','1111111','1111111'),
        'chest': ('0111110','1111111','1111111','1111111','1111111'),
        'stove': ('0010100','0111110','1111111','1111111','0111110'),
        'shop_npc': ('0011100','0111110','1111111','0111110','0111110'),
        'rowan': ('0011100','0011100','0111110','1111111','1111111'),
        'calendar': ('10101','11111','11111','11111','11111'),
        'save': ('11110','11111','11111','11111','11111'),
        'water': ('00100','01110','11111','11111','01110'),
        'harvest': ('10101','11111','11111','01110','00100'),
        'start': ('01000','01100','01110','01100','01000'),
        'sell': ('0111110','1111000','0111110','0001111','0111110'),
        'buy': ('1111100','1111110','1111100','1111110','1111100'),
        'check': ('000001','000011','100110','111100','011000'),
        'nav_up': ('0001000','0011100','0111110','1111111','0011100'),
        'nav_down': ('0011100','1111111','0111110','0011100','0001000'),
    }

    ALIASES = dict.fromkeys(('stone','copper','iron','diamond'), 'mineral') | dict.fromkeys(('pickaxe','fertilizer','fishing_rod'), 'tool')

    def __init__(self, engine):
        self.engine = engine
        self.dotpad = engine.dotpad

    @property
    def types(self):
        """Object types drawn as icons: the built-in set plus feature-registered icons."""
        return self.TYPES | self.engine.registry.icon_patterns.keys()

    def category(self, kind):
        aliased = self.engine.registry.icon_aliases.get(kind)
        return aliased if aliased else self.ALIASES.get(kind, kind or 'material')

    def spec(self, obj):
        kind = obj.get('type')
        symbol = kind
        frame = 'rectangle'
        pattern = ()
        registry = self.engine.registry
        if kind in registry.icon_patterns:
            if kind in registry.icon_symbols:
                symbol = registry.icon_symbols[kind](obj)
            if registry.icon_patterns[kind]:
                pattern = registry.icon_patterns[kind](obj)
        elif kind == 'resource': symbol = self.category(obj.get('resource_kind'))
        elif kind == 'care_button': symbol = {'plant':'seed','fertilizer':'tool'}.get(obj.get('care_kind'),obj.get('care_kind'))
        elif kind == 'watering_can': symbol = 'water'
        elif kind == 'fertilizer': symbol = 'tool'
        elif kind == 'save_slot': symbol = 'save'
        if symbol == 'food': frame = 'double_rectangle'
        # Rowan도 다른 아이콘과 동일하게 1칸 테두리(rectangle) 적용
        return IconSpec(frame, symbol, pattern)

    def frame(self, obj, shape='rectangle'):
        """Rowan 포함 모든 일반 버튼을 외곽 1줄 테두리(11x9)로 동일하게 렌더링."""
        if shape == 'ellipse': shape = 'double_rectangle'
        x, y = round(obj['x']), round(obj['y'])
        rx = max(2, int(obj.get('width', 12)) // 2 - 1)
        ry = max(2, int(obj.get('height', 10)) // 2 - 1)

        if shape in ('rectangle', 'quest_rectangle', 'double_rectangle'):
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
        if obj.get('type') not in self.types: return False
        skip = self.engine.registry.icon_skips.get(obj.get('type'))
        if skip and skip(obj):
            return False
        spec = self.spec(obj)
        self.frame(obj, spec.frame)
        if spec.frame == 'double_rectangle':
            return True
        rows = spec.pattern or self.PATTERNS.get(spec.symbol, self.PATTERNS['material'])
        self.pattern(obj['x'], obj['y'], rows)
        return True


class IconLayout:
    """Page policy over the same twelve virtual slots."""
    PAGES = frozenset(('home','seed_select',
        'load_game'))

    def __init__(self, grid=None):
        self.grid = grid or IconGrid()

    def arrange(self, page, objects, width, height, types=IconRenderer.TYPES, layout_order=None, grid_pages=()):
        objects = [dict(o) for o in objects]
        if page not in self.PAGES and page not in grid_pages and page != 'plot_detail': return objects
        chosen = [o for o in objects if o.get('type') in types
                  and not o.get('skip_grid')
                  and (page != 'plot_detail' or o.get('type') == 'care_button')]
        if page in ('home', 'town'):
            order = {
                'bed': 0, 'chest': 1, 'stove': 2,
                **(layout_order or {})
            }
            chosen.sort(key=lambda o: order.get(o['type'], 9))
        placed = self.grid.place(chosen, width, height)
        by_id = {o['id']: o for o in placed}
        return [by_id.get(o.get('id'), o) for o in objects]