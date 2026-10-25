# Shop

The shop counter (sell, buy, calendar), paged buy and sell lists, weekly market prices, and payment.

| Item | Value |
|---|---|
| Code | `feature.py` (`Shop`) |
| Pages | `shop_choice` (counter scene, icon grid, location text, braille "shop" panel), `shop_buy`, `shop_sell` (twelve rows per page, page bar or braille "buy"/"sell" panel) |
| Actions (after the night guard) | `open_shop`, `return_shop_choice`, `shop_mode:<buy|sell>`, `shop_page:<±1>`, `buy:<kind>:<item>`, `sell:<kind>:<item>` |
| Object types | `shop_npc`, `shop_choice`, `shop_item` (icons, hover sounds), `shop_hitbox` (scene targets) |
| Owned engine attributes (save format) | `shop_page` (`shop_page_count` is a derived cache set in the engine `__init__`, not saved) |
| Shared attributes written | `resources["coin"]` (via `add_resource`), `current_page` (via `set_page`), `current_location` (opening the shop moves you to town); nothing else |
| Slots declared | `shop.buy_items` (`order.ShopBuyItems`), `shop.sell_items` (`order.ShopSellItems`) |
| Events | `reset` (`Reset.SHOP`); runs `close_dialogue` when opened |
| Engine API provided | `open_shop()`, `buy_shop_item(kind, item)`, `sell_shop_item(kind, item)` (tests, tools) |
| Engine API used | `market_price` (village); `consume_sale` (core effects) |
| Config | `config/game.json` → `seeds.*.seed_price/crop_price`, `fertilizer.*`, `shop.fertilizer_price`, `recipes.*.sell_price`; page names `pages.shop_*` |
| Client (web) | `web/features/shop/client.js` (counter task text) |
| Tests | `tests/python/audio/test_sound_events.py` (coin sounds, rejections), `tests/python/audio/test_team_audio.py` |
| Notes | The calendar button on the counter carries the village's `open_calendar` action. Core layout still positions arrows whose action starts with `shop_page:` and the keypad prefers paging arrows (`shop_page:`, `inventory_page:`). |
