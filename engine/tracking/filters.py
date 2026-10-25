class EMAFilter2D:

    def __init__(self, alpha=0.35):
        self.alpha = float(alpha)
        self.value = None


    def reset(self):
        self.value = None


    def update(self, point):
        if point is None:
            return None

        x = float(point[0])
        y = float(point[1])

        if self.value is None:
            self.value = (x, y)
            return self.value

        old_x, old_y = self.value
        a = self.alpha

        self.value = (
            old_x * (1.0 - a) + x * a,
            old_y * (1.0 - a) + y * a
        )

        return self.value
