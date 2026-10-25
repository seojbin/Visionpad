class DotPad:

    def __init__(self, width=60, height=40):
        self.width = width
        self.height = height
        self.clear()

    def clear(self):
        self.matrix = [
            [0 for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def set_dot(self, x, y, value=1):
        x = int(round(x))
        y = int(round(y))

        if 0 <= x < self.width and 0 <= y < self.height:
            self.matrix[y][x] = value

    def draw_line(self, x1, y1, x2, y2):
        x1 = int(round(x1))
        y1 = int(round(y1))
        x2 = int(round(x2))
        y2 = int(round(y2))

        dx = abs(x2 - x1)
        dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        error = dx + dy

        while True:
            self.set_dot(x1, y1)

            if x1 == x2 and y1 == y2:
                break

            e2 = 2 * error

            if e2 >= dy:
                error += dy
                x1 += sx

            if e2 <= dx:
                error += dx
                y1 += sy

    def draw_box(self, center_x, center_y, width, height):
        x1 = int(round(center_x - width / 2))
        x2 = int(round(center_x + width / 2))
        y1 = int(round(center_y - height / 2))
        y2 = int(round(center_y + height / 2))

        self.draw_line(x1, y1, x2, y1)
        self.draw_line(x2, y1, x2, y2)
        self.draw_line(x2, y2, x1, y2)
        self.draw_line(x1, y2, x1, y1)

    def draw_hollow_triangle(self, x, y, direction, size=2):
        # Integer 45-degree edges: symmetric outline, no rasterized 2:1 slope.
        x, y = int(round(x)), int(round(y))
        radius = max(2, min(4, int(round(size))))
        if direction not in ("left", "right", "up", "down"):
            return
        for row in range(-radius, radius + 1):
            for col in range(radius + 1):
                if col != 0 and col != radius - abs(row):
                    continue
                dx, dy = col - radius // 2, row
                if direction == "left":
                    dx = -dx
                elif direction == "up":
                    dx, dy = dy, -dx
                elif direction == "down":
                    dx, dy = dy, dx
                self.set_dot(x + dx, y + dy)

    def draw_arrow(self, x, y, direction, size=2):
        """모든 방향 표시는 막대기 없는 비어 있는 삼각형으로 그린다."""
        self.draw_hollow_triangle(x, y, direction, size)

    def to_list(self):
        return self.matrix
