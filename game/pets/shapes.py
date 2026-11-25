"""Cat and dog silhouettes (36 x 24 pins) built from simple shapes, so every pose keeps the same
distinguishing features. Tactile design rules and sources: root README, "Tactile design rules".

Recognition by touch is poor for raised-line pictures of similar animals, so the two species differ in
as many ways as possible (BANA 2010 §8.6.10) and in canonical side view, facing right:

* cat: round head, two tall pointed ears, short face, slim legs, long tail curling upward
* dog: long body, long rectangular snout, one floppy ear hanging below the head, thick legs, short raised tail

The grids are solid silhouettes ("1" inside the animal); the feature draws them with
engine.display.tactile.fur_rows: solid legs, tail and ears, a one-pin outline, and horizontal line
texture inside the body so stroking is felt as a surface.
"""
import math

W, H = 36, 24


class Canvas:
    def __init__(self):
        self.grid = [[0] * W for _ in range(H)]
        self.body = None   # Canvas holding only the body, where the stroking texture goes

    def body_ellipse(self, cx, cy, rx, ry):
        """The body: part of the silhouette and the only area that gets the stroking texture."""
        self.ellipse(cx, cy, rx, ry)
        self.body = Canvas()
        self.body.ellipse(cx, cy, rx, ry)

    def dot(self, x, y):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H:
            self.grid[y][x] = 1

    def ellipse(self, cx, cy, rx, ry):
        for y in range(H):
            for x in range(W):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.grid[y][x] = 1

    def rect(self, x1, y1, x2, y2):
        for y in range(y1, y2 + 1):
            for x in range(x1, x2 + 1):
                self.dot(x, y)

    def triangle(self, a, b, c):
        (ax, ay), (bx, by), (cx, cy) = a, b, c

        def side(px, py, x1, y1, x2, y2):
            return (px - x2) * (y1 - y2) - (x1 - x2) * (py - y2)

        for y in range(H):
            for x in range(W):
                d1, d2, d3 = side(x, y, ax, ay, bx, by), side(x, y, bx, by, cx, cy), side(x, y, cx, cy, ax, ay)
                if not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0)):
                    self.grid[y][x] = 1

    def stroke(self, points, width=2):
        """Thick polyline: discs of diameter `width` along each segment."""
        r = width / 2
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            steps = max(1, int(math.hypot(x2 - x1, y2 - y1) * 3))
            for i in range(steps + 1):
                t = i / steps
                px, py = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
                for y in range(int(py - r) - 1, int(py + r) + 2):
                    for x in range(int(px - r) - 1, int(px + r) + 2):
                        if (x - px) ** 2 + (y - py) ** 2 <= r * r + 0.25:
                            self.dot(x, y)

    def clear(self, points):
        for x, y in points:
            x, y = int(round(x)), int(round(y))
            if 0 <= x < W and 0 <= y < H:
                self.grid[y][x] = 0

    def rows(self):
        return tuple(''.join('1' if v else '0' for v in row) for row in self.grid)


def legs(c, xs, top, bottom, width):
    for x in xs:
        c.rect(x, top, x + width - 1, bottom)


# ---- cat ----
# Proportions follow the original drawings (long, heavy body; head set directly on the front of the
# body, no neck). Only the parts that tell the species apart are exaggerated (TactIcons guideline:
# exaggerate identifying features; Mascle 2020: cat ears were the feature kept in tactile pictograms).

def cat_head(c, cx, cy):
    c.ellipse(cx, cy, 4.0, 3.6)
    # Two tall pointed ears, 3 pins wide at the base, with a lowered notch between them.
    c.triangle((cx - 4.0, cy - 1.0), (cx - 2.6, cy - 7.0), (cx - 0.6, cy - 2.6))
    c.triangle((cx + 0.6, cy - 2.6), (cx + 2.6, cy - 7.0), (cx + 4.0, cy - 1.0))
    c.clear([(cx, cy - 4), (cx, cy - 5)])


def cat(pose):
    c = Canvas()
    if pose in ('standing', 'petting', 'eating'):
        c.body_ellipse(16, 13, 11, 5)              # long body, rows 8-18
        legs(c, (6, 10, 20, 24), 16, 23, 3)        # four legs, 3 pins wide, one lowered pin apart
        if pose == 'eating':
            cat_head(c, 29, 16)                    # head lowered to the bowl, still on the body
        else:
            cat_head(c, 29, 9)
        tail = [(6, 11), (3, 8), (2, 4), (4, 1)] if pose != 'petting' else [(6, 11), (4, 6), (4, 2), (6, 0)]
        c.stroke(tail, 3)
    elif pose == 'sitting':
        c.body_ellipse(17, 15, 7.5, 7.5)           # upright body
        c.rect(21, 17, 23, 23)                     # front leg
        c.rect(10, 20, 20, 23)                     # haunch on the floor
        cat_head(c, 23, 8)
        c.stroke([(10, 21), (5, 22), (2, 19), (3, 15)], 3)   # tail curled round the feet
    else:  # sleeping, unwell: lying down
        c.body_ellipse(15, 17, 10, 5.8)            # curled up: a round body, head resting in front
        cat_head(c, 27, 16)
        c.stroke([(6, 20), (2, 19), (1, 15), (3, 12)], 3)    # tail curling up behind
    return c.rows(), c.body.rows()


# ---- dog ----

def dog_head(c, cx, cy):
    c.ellipse(cx, cy, 3.6, 3.4)
    c.rect(int(cx + 1), int(cy - 1), int(cx + 7), int(cy + 2))     # long snout
    # Drooping ear: a solid lobe hanging from the top of the head, with a lowered line between it and
    # the head so its edge can be felt (TactIcons: exaggerate the dog's ears).
    c.stroke([(cx - 1, cy - 3), (cx - 3, cy), (cx - 3.4, cy + 4)], 3)
    c.clear([(cx - 1, cy - 1), (cx - 1, cy), (cx - 1, cy + 1), (cx - 1.5, cy + 2), (cx - 2, cy + 3)])


def dog(pose):
    c = Canvas()
    if pose in ('standing', 'petting', 'eating'):
        c.body_ellipse(16, 13, 11.5, 5.2)
        legs(c, (5, 10, 19, 24), 16, 23, 4)        # thick legs
        if pose == 'eating':
            dog_head(c, 27, 17)
        else:
            dog_head(c, 27, 8)
        tail = [(5, 11), (2, 6)] if pose != 'petting' else [(5, 11), (2, 8), (1, 4)]
        c.stroke(tail, 3)
    elif pose == 'sitting':
        c.body_ellipse(16, 15, 7.5, 7.5)
        c.rect(20, 17, 22, 23)
        c.rect(9, 20, 19, 23)
        dog_head(c, 21, 7)
        c.stroke([(9, 19), (4, 16)], 3)
    else:
        c.body_ellipse(14, 17, 10.5, 5.8)          # lying down, head and snout resting forward
        dog_head(c, 26, 18)
        c.stroke([(4, 17), (0, 14)], 3)
    return c.rows(), c.body.rows()


POSES = ('standing', 'sitting', 'eating', 'petting', 'sleeping', 'unwell')
_BUILT = {'cat': {p: cat(p) for p in POSES}, 'dog': {p: dog(p) for p in POSES}}
DETAIL = {species: {p: rows for p, (rows, _) in poses.items()} for species, poses in _BUILT.items()}
# Where the stroking texture goes (the body only; head, ears, legs and tail stay plain).
TEXTURE = {species: {p: body for p, (_, body) in poses.items()} for species, poses in _BUILT.items()}


def drawing(species, pose, facing_left=False):
    """The large drawing as shown: solid limbs, outlined body with line texture (tactile.fur_rows)."""
    from engine.display.tactile import fur_rows
    rows = fur_rows(DETAIL[species][pose], mask=TEXTURE[species][pose])
    return tuple(r[::-1] for r in rows) if facing_left else rows


if __name__ == '__main__':
    for species, poses in DETAIL.items():
        for pose, rows in poses.items():
            print(species, pose)
            for r in rows:
                print(r.replace('0', '.').replace('1', '#'))
