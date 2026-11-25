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


class SymbolTable(dict):
    """Canonical symbols; a retired name resolves to the symbol that replaced it.

    Iterating lists only the canonical vocabulary (the icon lab catalogs it); indexing or .get()
    with an old name ("rowan", "chest", "nav_up", ...) returns the replacing symbol's rows.
    """
    def __init__(self, symbols, aliases):
        super().__init__(symbols)
        self.aliases = dict(aliases)
        unknown = set(self.aliases.values()) - set(symbols)
        if unknown:
            raise ValueError(f"Aliases point at unknown symbols: {sorted(unknown)}")

    def canonical(self, name):
        return name if dict.__contains__(self, name) else self.aliases.get(name, name)

    def __missing__(self, name):
        if name in self.aliases:
            return dict.__getitem__(self, self.aliases[name])
        raise KeyError(name)

    def __contains__(self, name):
        return dict.__contains__(self, name) or name in self.aliases

    def get(self, name, default=None):
        return self[name] if name in self else default


SYMBOLS = {
    # Items
    'seed':    ('010',
                '111',
                '010'),
    'crop':    ('10001',
                '01010',
                '00100',
                '00100',
                '01110'),
    'fish':    ('0111001',
                '1000110',
                '1000100',
                '1000110',
                '0111001'),
    'mineral': ('00100',
                '01010',
                '10001',
                '01010',
                '00100'),
    'tool':    ('11111',
                '00100',
                '00100',
                '00100'),
    'water':   ('00100',
                '01010',
                '10001',
                '10001',
                '01110'),
    'coin':    ('01110',
                '10001',
                '10101',
                '10001',
                '01110'),
    # Open basket ("U"): the shop row shows gold, bag, tool and page together, and closed outlines
    # of different form are the pairs readers confuse most (Gill & James 1973).
    'bag':     ('1000001',
                '1000001',
                '1000001',
                '0100010',
                '0011100'),
    # Places and people
    # Head, neck and shoulders joined into one shape: with a gap under the head it was felt as two objects.
    'person':  ('01110',
                '01110',
                '00100',
                '11111',
                '10001'),
    'bed':     ('1000000',
                '1110000',
                '1111111',
                '1000001'),
    'pot':     ('0011100',
                '1111111',
                '0100010',
                '0100010',
                '0111110'),
    'page':    ('11110',
                '10011',
                '10001',
                '10001',
                '11111'),
    # Direction and state (small solid signs)
    'arrow_up':    ('00100',
                    '01110',
                    '11111'),
    'arrow_down':  ('11111',
                    '01110',
                    '00100'),
    'arrow_right': ('100',
                    '110',
                    '111',
                    '110',
                    '100'),
    'check':   ('000001',
                '000011',
                '100110',
                '111100',
                '011000'),
    # No symbol: the frame alone (ordinary items, unknown kinds).
    'material': (),
}

# Retired symbol names -> the symbol that replaced them (23 names became 14 symbols plus "material").
SYMBOL_ALIASES = {
    'rowan': 'person', 'npc': 'person', 'shop_npc': 'bag',
    'chest': 'page', 'calendar': 'page', 'save': 'page', 'research': 'page',
    'stove': 'pot', 'tools': 'tool',
    'harvest': 'crop', 'plant': 'seed',
    'sell': 'coin', 'buy': 'bag',
    'nav_up': 'arrow_up', 'nav_down': 'arrow_down', 'start': 'arrow_right',
}


@dataclass(frozen=True)
class IconSpec:
    frame: str = 'rectangle'
    symbol: str = 'material'
    pattern: tuple = ()


class IconRenderer:
    """One thin frame plus one filled semantic symbol; optional selection/progress overlays."""
    TYPES = frozenset(('save_slot',))

    # Shared symbol vocabulary (tactile design rules in README.md, sources there).
    # Symbols shown together differ in structure class, not only in outline shape (Gill & James 1973):
    #   solid: seed, arrows | open lines: crop, tool, bed, check, bag | closed: mineral, water, page, pot
    #   closed + feature: fish (tail), coin (centre pin), person (solid head on open shoulders)
    # 14 symbols, at most 7x5 pins so a lowered pin always separates them from the frame.
    # Small signs (arrows, the person's head, the tool head) may be solid; anything wider is an
    # outline with a lowered interior. Old names (bed's "chest", "rowan", "nav_up" ...) are aliases.
    PATTERNS = SymbolTable(SYMBOLS, SYMBOL_ALIASES)

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
            self.pattern(obj['x'], obj['y'], self.PATTERNS.get(symbol, ()))

    def draw(self, obj):
        if obj.get('type') not in self.types: return False
        skip = self.engine.registry.icon_skips.get(obj.get('type'))
        if skip and skip(obj):
            return False
        spec = self.spec(obj)
        self.frame(obj, spec.frame)
        if spec.frame == 'double_rectangle':
            return True
        rows = spec.pattern or self.PATTERNS.get(spec.symbol, ())
        self.pattern(obj['x'], obj['y'], rows)
        return True


class IconLayout:
    """Page policy over the same twelve virtual slots."""
    PAGES = frozenset(('load_game',))

    def __init__(self, grid=None):
        self.grid = grid or IconGrid()

    def arrange(self, page, objects, width, height, types=IconRenderer.TYPES, layout_order=None, grid_pages=(),
                only=None):
        objects = [dict(o) for o in objects]
        if page not in self.PAGES and page not in grid_pages: return objects
        chosen = [o for o in objects if o.get('type') in types
                  and not o.get('skip_grid')
                  and (only is None or o.get('type') in only)]
        if page in ('home', 'town'):
            order = {
                **(layout_order or {})
            }
            chosen.sort(key=lambda o: order.get(o['type'], 9))
        placed = self.grid.place(chosen, width, height)
        by_id = {o['id']: o for o in placed}
        return [by_id.get(o.get('id'), o) for o in objects]