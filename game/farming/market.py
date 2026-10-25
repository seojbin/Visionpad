"""Farming items in the inventory and the shop: seeds, fertilizer and crops."""


class FarmMarket:
    def inventory_items(self):
        e = self.engine
        entries = []
        for seed_id, seed_config in e.config.get("seeds", {}).items():
            entries.append({"id": f"seed_{seed_id}", "label": f"{seed_config.get('label', seed_id)} seeds", "count": int(e.resources["seeds"].get(seed_id, 0)), "kind": "seed", "seed_id": seed_id, "action": ""})
        for seed_id, seed_config in e.config.get("seeds", {}).items():
            entries.append({"id": f"crop_{seed_id}", "label": f"{seed_config.get('label', seed_id)} crops", "count": int(e.resources["crops"].get(seed_id, 0)), "kind": "crop", "seed_id": seed_id, "action": ""})
        return entries

    def fertilizer_price(self):
        e = self.engine
        cfg = e.config.get("fertilizer", {})
        return int(cfg.get("shop_price", cfg.get("price", e.config.get("shop", {}).get("fertilizer_price", 12))))

    def shop_buy_rows(self):
        e = self.engine
        entries = [("seed", seed_id, f"{e.get_seed_label(seed_id)} seeds", e.resources["seeds"].get(seed_id, 0),
                    int(seed.get("seed_price", max(1, round(int(seed.get("crop_price", 1)) * .8)))))
                   for seed_id, seed in e.config.get("seeds", {}).items()]
        entries.append(("fertilizer", "fertilizer", "Fertilizer", e.resources["fertilizer"], self.fertilizer_price()))
        return entries

    def shop_sell_rows(self):
        e = self.engine
        return [("crop", key, f"{e.get_seed_label(key)} crops", e.resources["crops"].get(key, 0), int(seed.get("crop_price", 1)))
                for key, seed in e.config.get("seeds", {}).items() if e.resources["crops"].get(key, 0) > 0]

    def buy_item(self, kind, item_id):
        e = self.engine
        if kind == "seed":
            seed = e.get_seed_config(item_id)
            if not seed:
                return e.response(tts="Seed not sold here.", sfx="error")
            price = int(seed.get("seed_price", max(1, round(int(seed.get("crop_price", 1)) * 0.8))))
            label = f"{e.get_seed_label(item_id)} seeds"
        else:
            price = self.fertilizer_price()
            label = "Fertilizer"
        price = e.market_price(price, kind, "buy")
        if int(e.resources.get("coin", 0)) < price:
            return e.response(tts=f"Not enough gold. {label} costs {price} gold.", sfx="error")
        e.add_resource("coin", -price)
        if kind == "seed":
            e.resources["seeds"][item_id] = int(e.resources["seeds"].get(item_id, 0)) + 1
        else:
            e.resources["fertilizer"] = int(e.resources.get("fertilizer", 0)) + 1
        e.clear_hover()
        e.render()
        return e.response(tts=f"{label} bought. Gold left: {e.resources['coin']} gold", sfx="shop_buy", sound_events=[{"kind": "one_shot", "sound": "coin"}] if price > 0 else [])

    def sell_crop(self, item_id):
        e = self.engine
        count = int(e.resources["crops"].get(item_id, 0))
        if count <= 0:
            return e.response(tts="No crop to sell.", sfx="error")
        price = int(e.get_seed_config(item_id).get("crop_price", 1))
        label = f"{e.get_seed_label(item_id)} crops"
        e.resources["crops"][item_id] = count - 1
        return price, label
