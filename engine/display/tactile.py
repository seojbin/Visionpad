"""Tactile drawing rules shared by every page, and a checker for them.

The rules follow published tactile-graphics guidance (sources in README.md, "Tactile design rules"):

* Separation. A symbol never touches another symbol, a frame or a line: at least one lowered pin
  (about 2.5 mm on the Dot Pad) surrounds it. Lines stop short of symbols instead of running into them.
* Outline, not fill. Large shapes are drawn as a raised outline with a lowered interior. Only small
  point symbols (arrows, markers, small category signs) may be solid.
* Few symbols. The shared vocabulary is small and every symbol means one thing everywhere.

`outline_rows()` turns a solid pattern into its outline. `audit()` checks a rendered matrix against
the separation and fill rules; `engine/tools/tactile_audit.py` and the shared tests use it.
"""

# One lowered pin between a symbol and anything else (BANA 2010 asks for about 1/8 inch, ~3 mm;
# one Dot Pad pin pitch is ~2.5 mm, so one empty pin is the minimum and two are preferred).
MIN_GAP = 1
# A solid block larger than this (in pins per side) counts as a "filled" area and should be an outline.
MAX_SOLID_SIDE = 4
# A selectable shape of at least 8x8 pins raising more than this share of its box reads as "filled",
# even with a few lowered pins carved into it (the old engraved furniture and shop building).
MAX_FILL_RATIO = 0.5
LARGE_AREA = 64  # 8x8 pins: smaller point symbols (a 5x5 person, a 7x5 icon symbol) may be solid
# Different symbol drawings on one page (BANA 2010 §3.2.2: no more than five types of point symbols).
MAX_SYMBOLS_PER_PAGE = 5


def outline_rows(rows, keep=()):
    """Raised outline of a solid pattern: keep a raised pin only if a 4-neighbour is lowered or outside.

    `keep` lists (column, row) positions that stay raised even inside the shape (for example an eye).
    Lowered pins inside the original pattern (eyes, doors) keep their own outline, so details survive.
    """
    rows = [str(r) for r in rows]
    if not rows:
        return tuple()
    height, width = len(rows), max(len(r) for r in rows)
    grid = [r.ljust(width, '0') for r in rows]

    def raised(x, y):
        return 0 <= y < height and 0 <= x < width and grid[y][x] == '1'

    keep = set(keep)
    result = []
    for y in range(height):
        line = []
        for x in range(width):
            if not raised(x, y):
                line.append('0')
            elif (x, y) in keep or not all(raised(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                line.append('1')
            else:
                line.append('0')
        result.append(''.join(line))
    return tuple(result)


def close_gaps(rows):
    """Fill one-pin carved lines inside a silhouette (a lowered pin between two raised ones).

    Used before fur_rows() on drawings whose detail was carved into a solid shape: carved lines
    would otherwise break the body into strips too narrow for a texture.
    """
    rows = [str(r) for r in rows]
    height, width = len(rows), max(len(r) for r in rows) if rows else 0
    grid = [r.ljust(width, '0') for r in rows]

    def raised(x, y):
        return 0 <= y < height and 0 <= x < width and grid[y][x] == '1'

    return tuple(''.join('1' if c == '1' or (raised(x - 1, y) and raised(x + 1, y))
                         or (raised(x, y - 1) and raised(x, y + 1)) else '0'
                         for x, c in enumerate(row)) for y, row in enumerate(grid))


THIN_PART = 5


def fur_rows(rows, spacing=2, min_run=3, mask=None):
    """A solid silhouette drawn for stroking: solid limbs, a one-pin outline and a line texture inside.

    Based on pin-display studies (sources in README.md, "Tactile design rules"):

    * Thin parts (legs, tail, ears; up to `THIN_PART` = 5 pins across) stay solid. Small filled parts were recognised
      better than outlined ones (Mascle 2020), and outlining a thin leg turns it into two lines.
    * Wide parts get a raised outline one pin wide, then a lowered channel one pin wide, so the texture
      never merges with the edge (APH Monarch guidance; Prescher et al. 2017).
    * Inside, horizontal raised lines with one lowered row between them (`spacing` = 2): a uniform
      line texture, the kind that was recognised best on pin displays, felt as ridges when stroked.
      Runs shorter than `min_run` pins are dropped: isolated single pins read as eyes or braille
      (Bhatnagar et al. 2023), which is why the earlier sparse-dot texture looked like a face.
    * `mask` (rows like `rows`) limits the texture to part of the shape, e.g. the body, so the head
      stays an empty outline and is not striped.
    """
    rows = [str(r) for r in rows]
    if not rows:
        return tuple()
    height, width = len(rows), max(len(r) for r in rows)
    grid = [r.ljust(width, '0') for r in rows]

    def inside(x, y):
        return 0 <= y < height and 0 <= x < width and grid[y][x] == '1'

    def deep(x, y, radius):
        return all(inside(x + dx, y + dy) for dx in range(-radius, radius + 1)
                   for dy in range(-radius, radius + 1) if abs(dx) + abs(dy) <= radius)

    def in_mask(x, y):
        return mask is None or (y < len(mask) and x < len(mask[y]) and mask[y][x] == '1')

    # A pin belongs to a thin part when the run of raised pins through it, across or down, is at most
    # THIN_PART pins long (legs, ears, tails, a sheep's five-pin legs); everything else is a wide part.
    def run(x, y, dx, dy):
        n = 1
        for sign in (1, -1):
            k = 1
            while inside(x + sign * k * dx, y + sign * k * dy):
                n += 1
                k += 1
        return n

    wide = {(x, y) for y in range(height) for x in range(width)
            if inside(x, y) and min(run(x, y, 1, 0), run(x, y, 0, 1)) > THIN_PART}
    out = [['0'] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            if not inside(x, y):
                continue
            if (x, y) not in wide or not deep(x, y, 1):
                out[y][x] = '1'                       # thin part, or the outline of a wide part
            elif deep(x, y, 2) and y % spacing == 0 and in_mask(x, y):
                out[y][x] = '1'                       # texture line (one lowered pin from the outline)
    # Drop texture runs that are too short to be felt as a line.
    for y in range(height):
        x = 0
        while x < width:
            if out[y][x] == '1' and (x, y) in wide and deep(x, y, 2):
                end = x
                while end < width and out[y][end] == '1' and deep(end, y, 2):
                    end += 1
                if end - x < min_run:
                    for k in range(x, end):
                        out[y][k] = '0'
                x = end
            else:
                x += 1
    return tuple(''.join(r) for r in out)


def largest_solid_square(matrix):
    """Side of the largest fully raised square anywhere in the matrix."""
    if not matrix:
        return 0
    height, width = len(matrix), len(matrix[0])
    best = 0
    previous = [0] * (width + 1)
    for y in range(height):
        current = [0] * (width + 1)
        for x in range(width):
            if matrix[y][x]:
                current[x + 1] = 1 + min(previous[x + 1], previous[x], current[x])
                best = max(best, current[x + 1])
        previous = current
    return best


def solid_blocks(matrix, side=MAX_SOLID_SIDE + 1):
    """Top-left corners of fully raised side x side blocks (overlapping corners merged per block)."""
    height, width = len(matrix), len(matrix[0]) if matrix else 0
    found = []
    for y in range(height - side + 1):
        for x in range(width - side + 1):
            if all(matrix[y + dy][x + dx] for dy in range(side) for dx in range(side)):
                if not any(abs(x - fx) < side and abs(y - fy) < side for fx, fy in found):
                    found.append((x, y))
    return found


def components(matrix):
    """8-connected groups of raised pins: {(x, y): component index}, [bounding boxes]."""
    height, width = len(matrix), len(matrix[0]) if matrix else 0
    label, boxes = {}, []
    for sy in range(height):
        for sx in range(width):
            if not matrix[sy][sx] or (sx, sy) in label:
                continue
            index = len(boxes)
            box = [sx, sy, sx, sy]
            stack = [(sx, sy)]
            label[(sx, sy)] = index
            while stack:
                x, y = stack.pop()
                box[0], box[1], box[2], box[3] = min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and matrix[ny][nx] and (nx, ny) not in label:
                            label[(nx, ny)] = index
                            stack.append((nx, ny))
            boxes.append(tuple(box))
    return label, boxes


def object_box(obj):
    """(left, top, right, bottom) of an object's drawn area, inclusive."""
    x, y = round(obj['x']), round(obj['y'])
    w = int(obj.get('width') or obj.get('hit_width') or 1)
    h = int(obj.get('height') or obj.get('hit_height') or 1)
    left, top = x - w // 2, y - h // 2
    return left, top, left + w - 1, top + h - 1


def isolation_problems(matrix, obj, slack=1):
    """Raised groups at an object's centre that run outside its box: the object touches something else.

    An object is isolated when every raised group it is made of stays inside its box (plus `slack`
    pins for rounding). A road, frame or neighbour that touches the object joins its group and makes
    that group spill far outside the box.
    """
    label, boxes = components(matrix)
    left, top, right, bottom = object_box(obj)
    width, height = right - left + 1, bottom - top + 1
    # The object's own groups: anything raised in its central half (outlines: its whole box).
    inner = (left + width // 4, top + height // 4, right - width // 4, bottom - height // 4)
    mine = {label[(x, y)] for y in range(inner[1], inner[3] + 1) for x in range(inner[0], inner[2] + 1)
            if (x, y) in label}
    if not mine:
        mine = {label[(x, y)] for y in range(top, bottom + 1) for x in range(left, right + 1) if (x, y) in label}
    problems = []
    for index in sorted(mine):
        bx1, by1, bx2, by2 = boxes[index]
        if bx1 < left - slack or by1 < top - slack or bx2 > right + slack or by2 > bottom + slack:
            problems.append(f"{obj.get('id')}: touches a line or symbol reaching {boxes[index]} (own box {left, top, right, bottom})")
    return problems


def fill_ratio(matrix, obj):
    """Share of raised pins inside an object's box, not counting its outermost ring (the outline)."""
    left, top, right, bottom = object_box(obj)
    left, top, right, bottom = left + 1, top + 1, right - 1, bottom - 1
    height, width = len(matrix), len(matrix[0]) if matrix else 0
    cells = [(x, y) for y in range(max(0, top), min(height, bottom + 1))
             for x in range(max(0, left), min(width, right + 1))]
    return sum(matrix[y][x] for x, y in cells) / len(cells) if cells else 0.0


class SymbolTrace:
    """Records which drawing call raised each pin while a page renders.

    Every call that draws a symbol (an icon pattern, a solid scene figure, an arrow, a filled marker)
    gets its own tag; all other pins (lines, frames, walls, roads) are tagged 'line'. After rendering,
    `contacts()` lists symbols whose pins sit next to (or on top of) pins from another drawing: a symbol
    touching a wall, a frame, a road or another symbol, whatever the object boxes say.

        with SymbolTrace(engine) as trace:
            engine.render()
        problems = trace.contacts(engine.dotpad.to_list())
    """

    SYMBOL_METHODS = ("draw_icon_pattern", "draw_solid_pattern", "draw_triangle", "draw_filled_square")
    PAD_SYMBOL_METHODS = ("draw_hollow_triangle",)

    def __init__(self, engine):
        self.engine = engine
        self.owner = {}       # (x, y) -> tag of the drawing that last raised it
        self.overlaps = []    # (tag, (x, y), previous tag): a symbol drawn over another drawing's pin
        self.places = {}      # tag -> (method, x, y) for messages
        self._stack = []
        self._count = 0
        self._saved = []

    def __enter__(self):
        pad = self.engine.dotpad
        original_set = pad.set_dot

        def set_dot(x, y, value=1):
            original_set(x, y, value)
            key = (int(round(x)), int(round(y)))
            tag = self._stack[-1] if self._stack else "line"
            if value:
                previous = self.owner.get(key)
                if previous is not None and previous != tag and tag != "line" \
                        and 0 <= key[1] < pad.height and 0 <= key[0] < pad.width and pad.matrix[key[1]][key[0]]:
                    self.overlaps.append((tag, key, previous))
                self.owner[key] = tag
            else:
                self.owner.pop(key, None)

        def wrap(target, name):
            original = getattr(target, name)

            def traced(x, y, *args, **kwargs):
                if self._stack and not self._stack[-1].startswith("object "):
                    return original(x, y, *args, **kwargs)   # part of an outer symbol call
                self._count += 1
                tag = f"{name}#{self._count}"
                self.places[tag] = (name, x, y)
                self._stack.append(tag)
                try:
                    return original(x, y, *args, **kwargs)
                finally:
                    self._stack.pop()
            setattr(target, name, traced)
            self._saved.append((target, name))

        pad.set_dot = set_dot
        self._saved.append((pad, "set_dot"))
        for name in self.SYMBOL_METHODS:
            wrap(self.engine, name)
        for name in self.PAD_SYMBOL_METHODS:
            wrap(pad, name)

        # Each object's own drawing (its renderer or its icon frame) is one more tag, so an object's
        # lines touching a road or another object count as well; symbols inside keep their own tags.
        def per_object(function):
            def traced(obj, *args, **kwargs):
                if self._stack:
                    return function(obj, *args, **kwargs)
                tag = f"object {obj.get('id') or obj.get('type')}"
                self.places[tag] = (tag, obj.get("x"), obj.get("y"))
                self._objects.append(tag)
                self._stack.append(tag)
                try:
                    return function(obj, *args, **kwargs)
                finally:
                    self._stack.pop()
            return traced

        self._objects = []
        registry = self.engine.registry
        self._renderers = registry.renderers
        registry.renderers = {kind: per_object(fn) for kind, fn in registry.renderers.items()}
        icons = self.engine.icons
        icons.draw = per_object(icons.draw)
        self._saved.append((icons, "draw"))
        return self

    def __exit__(self, *exc):
        self.engine.registry.renderers = self._renderers
        for target, name in self._saved:
            try:
                delattr(target, name)    # remove the instance attribute; the class method shows again
            except AttributeError:
                pass
        return False

    def _where(self, tag):
        name, x, y = self.places.get(tag, (tag, "?", "?"))
        return f"{name} at ({x}, {y})"

    def contacts(self, matrix):
        """Symbols that touch another drawing (8-neighbour contact) or were drawn over one."""
        height, width = len(matrix), len(matrix[0]) if matrix else 0
        touching = {}
        for (x, y), tag in self.owner.items():
            if tag == "line" or not (0 <= x < width and 0 <= y < height) or not matrix[y][x]:
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if (dx or dy) and 0 <= nx < width and 0 <= ny < height and matrix[ny][nx]:
                        other = self.owner.get((nx, ny), "line")
                        if other != tag:
                            touching.setdefault((tag, other), (nx, ny))
        problems = []
        seen = set()
        for (tag, other), point in sorted(touching.items(), key=lambda item: item[0]):
            pair = frozenset((tag, other))
            if pair in seen:
                continue
            seen.add(pair)
            what = "a line or frame" if other == "line" else self._where(other)
            problems.append(f"{self._where(tag)} touches {what} at {point}")
        for tag, point, previous in self.overlaps:
            if self.owner.get(point) == tag:
                what = "a line or frame" if previous == "line" else self._where(previous)
                problems.append(f"{self._where(tag)} is drawn over {what} at {point}")
        return problems


def audit(matrix, objects, isolated_types=(), allow_solid=False, fill_types=None):
    """Problems on one rendered page: filled areas, objects of `isolated_types` that touch others, and
    large objects of `fill_types` (default: `isolated_types`) drawn filled instead of as an outline."""
    fill_types = isolated_types if fill_types is None else fill_types
    problems = []
    # Objects marked filled_by_design (the woolly sheep, whose wool is the thing sheared) may be solid.
    exempt = [object_box(o) for o in objects if o.get('filled_by_design') and o.get('x') is not None]

    def exempted(x, y):
        return any(l - 1 <= x <= r + 1 and t - 1 <= y <= b + 1 for l, t, r, b in exempt)

    if not allow_solid:
        for x, y in solid_blocks(matrix):
            if not exempted(x, y):
                problems.append(f"filled area at ({x}, {y}) larger than {MAX_SOLID_SIDE}x{MAX_SOLID_SIDE}")
    for obj in objects:
        if obj.get('type') not in isolated_types or obj.get('x') is None:
            continue
        problems.extend(isolation_problems(matrix, obj))
        left, top, right, bottom = object_box(obj)
        if not allow_solid and not obj.get('filled_by_design') and obj.get('type') in fill_types and (right - left + 1) * (bottom - top + 1) >= LARGE_AREA:
            ratio = fill_ratio(matrix, obj)
            if ratio > MAX_FILL_RATIO:
                problems.append(f"{obj.get('id')}: {ratio:.0%} of its interior is raised; draw it as an outline with a lowered interior")
    return problems
