# Prize draw

Shop → General goods → first item, Prize draw: 200 gold, one reward per purchase. There is no empty outcome. Fixed draw price ignores weekly/food discounts and does not consume limited discount uses. Results are awarded immediately and saved as the last result. The result voice starts no earlier than 1 second after roulette.mp3 starts. A separate wheel beside the shopkeeper buys a draw directly using the same price and action. Repeated intentional purchases are separate paid draws.

| Reward | Probability | Quantity |
|---|---:|---:|
| Plant nutrient | 12% | 1 |
| Special feed | 12% | 1 |
| Gold tool kit | 10% | 1; pickaxe/rod equally likely |
| Pet voucher | 6% | 1; dog/cat equally likely |
| Flower seed | 6% | 1; morning glory/sunflower/orchid equally likely |
| Diamond | 1% | 1 |
| Fertilizer | 20% | 3 |
| Crop seeds | 33% | 3 of one crop type |

Direct fertilizer and flower-seed purchase is removed. Normal crop seeds and shared animal feed remain purchasable. Medicine is guaranteed stock, 30 gold before market discounts. Vouchers redeem for a pet or sell for exactly 300 gold. Full households do not consume vouchers. Use supplies from inventory; special feed and medicine first open pet selection.

Plant nutrient applies to living plants only: clears dry/bloom aging counters and prevents wilting for six day transitions. It does not revive dead plants or instantly grow sprouts. One existing flower pot can hold any of the three flower species; all share the existing growth/watering rules and harvest effect for this test build. Morning-glory artwork is preserved, the other flower heads are distinct tactile patterns and their seed cards reuse existing images.

Gold kits require the corresponding tool, reset accumulated wear and divide effective wear by four. The existing break-probability formulas still apply; this is not a guarantee of an exact lifetime. Enhancement cannot stack, persists in saves, and disappears with the broken tool. Failed use never consumes the kit.

| Area | Implementation |
|---|---|
| Code | game/roulette/feature.py |
| Pages | none; existing shop and inventory |
| Actions | prize:<item>, buy:roulette:draw, buy:pet_medicine:medicine, sell:pet_voucher:<item> |
| Object types | existing shop_item and resource |
| Owned engine attributes | roulette_goods, gold_tools, roulette_last_result, roulette_queue |
| Shared attributes written/read | resources, flower seed stock through Flowers.add_seed, houseplant counters, pickaxe/rod wear; pets through Pets.adopt |
| Events | reset |
| Slots | shop.buy_items, shop.sell_items, inventory.items |
| State keys | roulette: last_result, gold_tools |
| Saves | Supplies, enhancements, last result and five upcoming rewards persist in the normal save slot; older saves receive a five-reward queue using their saved random state |
| Engine API provided/used | Provided: none. Used: resource/add_resource, market_price, get_seed_label, render, response, clear_hover, set_page |
| Config | engine/config/game.json → roulette: price, weights, seed_quantity, fertilizer_quantity, medicine_price, voucher_sell_price, nutrient_days, gold_durability_multiplier, result_delay_ms |
| Client (web) | core/game-audio.js registers roulette.mp3 in the existing one-shot channel |
| Tests | game/roulette/tests/test_roulette.py, game/pets/tests/test_audio.cjs |

The five upcoming category/item pairs are prepared in advance. A paid draw consumes the first and appends one new weighted draw. Failed purchases do not advance the queue. Loading restores the queue and random state from that slot; it intentionally rewinds the draw sequence too. The queue is not included in public browser state. No separate prize-sequence file is created.

The browser warms visible speech labels and the initial home prompts in the background. Cached speech avoids repeated synthesis and decoding; a new, uncached line still requires server synthesis. Background requests have lower priority than speech actions. Result voice cancellation and quest protection continue to use GameSpeech.
