"""Helpers for engine state that many features write.

Each helper does exactly what the inline code did before the split, including
raising KeyError for unknown resource keys.
"""


class SharedState:
    def set_page(self, page):
        self.current_page = page

    def resource(self, key, item=None):
        return self.resources[key] if item is None else self.resources[key][item]

    def add_resource(self, key, amount, item=None):
        if item is None:
            self.resources[key] += amount
        else:
            self.resources[key][item] += amount
