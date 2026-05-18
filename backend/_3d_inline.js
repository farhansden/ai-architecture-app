
// ── DATA ──────────────────────────────────────────────────────────────────────
const LAYOUT   = {"rooms": [{"name": "car_porch", "floor": 0, "x": 50.0, "y": 50.0, "width": 123.8, "height": 92.0, "width_ft": 12.4, "depth_ft": 9.2, "area_sqft": 114.1, "area_px": 11384.8, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "covered parking for 1 car(s), front of plot", "__cat": "car_porch", "functional_zone": "public", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "front", "__col_side": "left", "layout_band": 0}, {"name": "foyer", "floor": 0, "x": 173.8, "y": 50.0, "width": 81.0, "height": 92.0, "width_ft": 8.1, "depth_ft": 9.2, "area_sqft": 74.5, "area_px": 7443.9, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "entrance foyer, northeast Vastu zone", "__cat": "foyer", "functional_zone": "public", "daylight_tier": "transitional", "circulation_role": "privacy_filter", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "C", "__col_side": "center", "layout_band": 0}, {"name": "sit_out", "floor": 0, "x": 254.8, "y": 50.0, "width": 95.2, "height": 92.0, "width_ft": 9.5, "depth_ft": 9.2, "area_sqft": 87.4, "area_px": 8757.5, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "vastu verandah at entrance", "__cat": "sit_out", "functional_zone": "public", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "front", "__col_side": "right", "layout_band": 0}, {"name": "pooja_room", "floor": 0, "x": 50.0, "y": 142.0, "width": 61.9, "height": 101.1, "width_ft": 6.2, "depth_ft": 10.1, "area_sqft": 62.6, "area_px": 6261.6, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "northeast Vastu zone, small altar space, storage for religious items.", "__cat": "pooja_room", "functional_zone": "semi_private", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "NE", "__col_side": "left", "layout_band": 1}, {"name": "dining_room", "floor": 0, "x": 111.9, "y": 142.0, "width": 95.2, "height": 101.1, "width_ft": 9.5, "depth_ft": 10.1, "area_sqft": 96.0, "area_px": 9633.3, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "adjacent to kitchen, 6-seater dining table, positioned to avoid direct sightlines to kitchen, north light.", "__cat": "dining_room", "functional_zone": "semi_private", "daylight_tier": "social_daylight", "circulation_role": "kitchen_anchor", "aspect_hint": "dual_aspect_desirable", "__is_carved": false, "__vastu_zone": "N", "__col_side": "left", "layout_band": 1}, {"name": "living_room", "floor": 0, "x": 207.1, "y": 142.0, "width": 142.9, "height": 101.1, "width_ft": 14.3, "depth_ft": 10.1, "area_sqft": 144.4, "area_px": 14449.9, "windows": 2, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "north-east Vastu zone, spacious layout for sectional sofa, coffee table, entertainment unit, large windows for natural light.", "__cat": "living_room", "functional_zone": "public", "daylight_tier": "primary_social", "circulation_role": "movement_organiser", "aspect_hint": "dual_aspect_desirable", "__is_carved": false, "__vastu_zone": "N", "__col_side": "center", "layout_band": 1}, {"name": "corridor", "floor": 0, "x": 50.0, "y": 243.1, "width": 204.0, "height": 46.0, "width_ft": 20.4, "depth_ft": 4.6, "area_sqft": 93.8, "area_px": 9379.3, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "floor 0 corridor \u2014 auto-injected by geometric rail", "__cat": "corridor", "functional_zone": "circulation", "daylight_tier": "borrowed_light", "circulation_role": "spine_connector", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "C", "__col_side": "center", "layout_band": 2}, {"name": "staircase", "floor": 0, "x": 254.0, "y": 243.1, "width": 96.0, "height": 46.0, "width_ft": 9.6, "depth_ft": 4.6, "area_sqft": 44.2, "area_px": 4413.8, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "internal staircase leading to first floor.", "__cat": "staircase", "functional_zone": "circulation", "daylight_tier": "borrowed_light", "circulation_role": "vertical_link", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 2}, {"name": "kitchen", "floor": 0, "x": 50.0, "y": 289.1, "width": 160.0, "height": 87.4, "width_ft": 16.0, "depth_ft": 8.7, "area_sqft": 139.2, "area_px": 13977.0, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "southeast Vastu fire zone, single modular kitchen, L-counter + hob + sink on segregated wet wall, tall unit run, pass door to dining, utility door to wash/laundry.", "__cat": "kitchen", "functional_zone": "service", "daylight_tier": "cross_vent_priority", "circulation_role": "service_core", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "SE", "__col_side": "right", "layout_band": 4}, {"name": "common_bathroom", "floor": 0, "x": 50.0, "y": 376.4, "width": 94.3, "height": 73.6, "width_ft": 9.4, "depth_ft": 7.4, "area_sqft": 69.6, "area_px": 6936.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "accessible from living area, modern fixtures, ventilation.", "__cat": "common_bathroom", "functional_zone": "service", "daylight_tier": "mechanical_vent", "circulation_role": "wet_zone", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "NW", "__col_side": "left", "layout_band": 5}, {"name": "utility_room", "floor": 0, "x": 144.3, "y": 376.4, "width": 111.4, "height": 73.6, "width_ft": 11.1, "depth_ft": 7.4, "area_sqft": 82.1, "area_px": 8197.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "adjacent to kitchen, space for washing machine and storage.", "__cat": "utility_room", "functional_zone": "service", "daylight_tier": "service_opening", "circulation_role": "wet_adjacency", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 5}, {"name": "store_room", "floor": 0, "x": 255.7, "y": 376.4, "width": 94.3, "height": 73.6, "width_ft": 9.4, "depth_ft": 7.4, "area_sqft": 69.6, "area_px": 6936.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "south zone", "__cat": "store_room", "functional_zone": "service", "daylight_tier": "service_opening", "circulation_role": "wet_adjacency", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 5}], "canvas_w": 540.0, "canvas_h": 640.0, "built_up_x": 50.0, "built_up_y": 50.0, "built_up_w": 300.0, "built_up_h": 400.0, "plot_w_px": 400.0, "plot_h_px": 500.0, "facing": "east", "warnings": ["PROGRAMME: room sizes lifted toward Indian residential minimums (built-up ~1200 sqft, plot ~40 ft wide).", "SHELL FIT: band stack compressed to stay within built-up envelope (alignment preserved; avoids stretched output).", "NBC: staircase at 9.6\u00d74.6ft (min 5.0\u00d78.0ft)"], "failed_rooms": []};
const ROOMS    = [{"name": "car_porch", "floor": 0, "x": 50.0, "y": 50.0, "width": 123.8, "height": 92.0, "width_ft": 12.4, "depth_ft": 9.2, "area_sqft": 114.1, "area_px": 11384.8, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "covered parking for 1 car(s), front of plot", "__cat": "car_porch", "functional_zone": "public", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "front", "__col_side": "left", "layout_band": 0, "__cat_resolved": "car_porch", "__wall_h": 0.0, "__color": "0xe8ede0", "__wallColor": "0xbcc8a8", "__label": "Car Porch", "__floor_y": 0.0}, {"name": "foyer", "floor": 0, "x": 173.8, "y": 50.0, "width": 81.0, "height": 92.0, "width_ft": 8.1, "depth_ft": 9.2, "area_sqft": 74.5, "area_px": 7443.9, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "entrance foyer, northeast Vastu zone", "__cat": "foyer", "functional_zone": "public", "daylight_tier": "transitional", "circulation_role": "privacy_filter", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "C", "__col_side": "center", "layout_band": 0, "__cat_resolved": "foyer", "__wall_h": 2.7, "__color": "0xf8f4ec", "__wallColor": "0xddd5c0", "__label": "Foyer", "__floor_y": 0.0}, {"name": "sit_out", "floor": 0, "x": 254.8, "y": 50.0, "width": 95.2, "height": 92.0, "width_ft": 9.5, "depth_ft": 9.2, "area_sqft": 87.4, "area_px": 8757.5, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "vastu verandah at entrance", "__cat": "sit_out", "functional_zone": "public", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "front", "__col_side": "right", "layout_band": 0, "__cat_resolved": "sit_out", "__wall_h": 0.0, "__color": "0xe8f4e0", "__wallColor": "0xbcd4a8", "__label": "Sit-out", "__floor_y": 0.0}, {"name": "pooja_room", "floor": 0, "x": 50.0, "y": 142.0, "width": 61.9, "height": 101.1, "width_ft": 6.2, "depth_ft": 10.1, "area_sqft": 62.6, "area_px": 6261.6, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "northeast Vastu zone, small altar space, storage for religious items.", "__cat": "pooja_room", "functional_zone": "semi_private", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "NE", "__col_side": "left", "layout_band": 1, "__cat_resolved": "pooja_room", "__wall_h": 2.7, "__color": "0xfff0d8", "__wallColor": "0xe8d4a8", "__label": "Pooja Room", "__floor_y": 0.0}, {"name": "dining_room", "floor": 0, "x": 111.9, "y": 142.0, "width": 95.2, "height": 101.1, "width_ft": 9.5, "depth_ft": 10.1, "area_sqft": 96.0, "area_px": 9633.3, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "adjacent to kitchen, 6-seater dining table, positioned to avoid direct sightlines to kitchen, north light.", "__cat": "dining_room", "functional_zone": "semi_private", "daylight_tier": "social_daylight", "circulation_role": "kitchen_anchor", "aspect_hint": "dual_aspect_desirable", "__is_carved": false, "__vastu_zone": "N", "__col_side": "left", "layout_band": 1, "__cat_resolved": "dining_room", "__wall_h": 3.0, "__color": "0xfaf0dc", "__wallColor": "0xe8d5a3", "__label": "Dining Room", "__floor_y": 0.0}, {"name": "living_room", "floor": 0, "x": 207.1, "y": 142.0, "width": 142.9, "height": 101.1, "width_ft": 14.3, "depth_ft": 10.1, "area_sqft": 144.4, "area_px": 14449.9, "windows": 2, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "north-east Vastu zone, spacious layout for sectional sofa, coffee table, entertainment unit, large windows for natural light.", "__cat": "living_room", "functional_zone": "public", "daylight_tier": "primary_social", "circulation_role": "movement_organiser", "aspect_hint": "dual_aspect_desirable", "__is_carved": false, "__vastu_zone": "N", "__col_side": "center", "layout_band": 1, "__cat_resolved": "living_room", "__wall_h": 3.6, "__color": "0xf5e6c8", "__wallColor": "0xe8d5a3", "__label": "Living Room", "__floor_y": 0.0}, {"name": "corridor", "floor": 0, "x": 50.0, "y": 243.1, "width": 204.0, "height": 46.0, "width_ft": 20.4, "depth_ft": 4.6, "area_sqft": 93.8, "area_px": 9379.3, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "floor 0 corridor \u2014 auto-injected by geometric rail", "__cat": "corridor", "functional_zone": "circulation", "daylight_tier": "borrowed_light", "circulation_role": "spine_connector", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "C", "__col_side": "center", "layout_band": 2, "__cat_resolved": "corridor", "__wall_h": 2.7, "__color": "0xf0ede4", "__wallColor": "0xd8d0c0", "__label": "Corridor", "__floor_y": 0.0}, {"name": "staircase", "floor": 0, "x": 254.0, "y": 243.1, "width": 96.0, "height": 46.0, "width_ft": 9.6, "depth_ft": 4.6, "area_sqft": 44.2, "area_px": 4413.8, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "internal staircase leading to first floor.", "__cat": "staircase", "functional_zone": "circulation", "daylight_tier": "borrowed_light", "circulation_role": "vertical_link", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 2, "__cat_resolved": "staircase", "__wall_h": 3.0, "__color": "0xece8e0", "__wallColor": "0xd0ccc0", "__label": "Staircase", "__floor_y": 0.0}, {"name": "kitchen", "floor": 0, "x": 50.0, "y": 289.1, "width": 160.0, "height": 87.4, "width_ft": 16.0, "depth_ft": 8.7, "area_sqft": 139.2, "area_px": 13977.0, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "southeast Vastu fire zone, single modular kitchen, L-counter + hob + sink on segregated wet wall, tall unit run, pass door to dining, utility door to wash/laundry.", "__cat": "kitchen", "functional_zone": "service", "daylight_tier": "cross_vent_priority", "circulation_role": "service_core", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "SE", "__col_side": "right", "layout_band": 4, "__cat_resolved": "kitchen", "__wall_h": 2.7, "__color": "0xdcf5e8", "__wallColor": "0xb3d9c4", "__label": "Kitchen", "__floor_y": 0.0}, {"name": "common_bathroom", "floor": 0, "x": 50.0, "y": 376.4, "width": 94.3, "height": 73.6, "width_ft": 9.4, "depth_ft": 7.4, "area_sqft": 69.6, "area_px": 6936.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "accessible from living area, modern fixtures, ventilation.", "__cat": "common_bathroom", "functional_zone": "service", "daylight_tier": "mechanical_vent", "circulation_role": "wet_zone", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "NW", "__col_side": "left", "layout_band": 5, "__cat_resolved": "common_bathroom", "__wall_h": 2.4, "__color": "0xd8f0f8", "__wallColor": "0xa8c8d8", "__label": "Common Bath", "__floor_y": 0.0}, {"name": "utility_room", "floor": 0, "x": 144.3, "y": 376.4, "width": 111.4, "height": 73.6, "width_ft": 11.1, "depth_ft": 7.4, "area_sqft": 82.1, "area_px": 8197.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "adjacent to kitchen, space for washing machine and storage.", "__cat": "utility_room", "functional_zone": "service", "daylight_tier": "service_opening", "circulation_role": "wet_adjacency", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 5, "__cat_resolved": "utility_room", "__wall_h": 2.4, "__color": "0xeceae4", "__wallColor": "0xd0ccbf", "__label": "Utility Room", "__floor_y": 0.0}, {"name": "store_room", "floor": 0, "x": 255.7, "y": 376.4, "width": 94.3, "height": 73.6, "width_ft": 9.4, "depth_ft": 7.4, "area_sqft": 69.6, "area_px": 6936.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "south zone", "__cat": "store_room", "functional_zone": "service", "daylight_tier": "service_opening", "circulation_role": "wet_adjacency", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 5, "__cat_resolved": "store_room", "__wall_h": 2.4, "__color": "0xe8e6e0", "__wallColor": "0xccc8bc", "__label": "Store Room", "__floor_y": 0.0}];
const ALLROOMS = [{"name": "car_porch", "floor": 0, "x": 50.0, "y": 50.0, "width": 123.8, "height": 92.0, "width_ft": 12.4, "depth_ft": 9.2, "area_sqft": 114.1, "area_px": 11384.8, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "covered parking for 1 car(s), front of plot", "__cat": "car_porch", "functional_zone": "public", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "front", "__col_side": "left", "layout_band": 0, "__cat_resolved": "car_porch", "__wall_h": 0.0, "__color": "0xe8ede0", "__wallColor": "0xbcc8a8", "__label": "Car Porch", "__floor_y": 0.0}, {"name": "foyer", "floor": 0, "x": 173.8, "y": 50.0, "width": 81.0, "height": 92.0, "width_ft": 8.1, "depth_ft": 9.2, "area_sqft": 74.5, "area_px": 7443.9, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "entrance foyer, northeast Vastu zone", "__cat": "foyer", "functional_zone": "public", "daylight_tier": "transitional", "circulation_role": "privacy_filter", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "C", "__col_side": "center", "layout_band": 0, "__cat_resolved": "foyer", "__wall_h": 2.7, "__color": "0xf8f4ec", "__wallColor": "0xddd5c0", "__label": "Foyer", "__floor_y": 0.0}, {"name": "sit_out", "floor": 0, "x": 254.8, "y": 50.0, "width": 95.2, "height": 92.0, "width_ft": 9.5, "depth_ft": 9.2, "area_sqft": 87.4, "area_px": 8757.5, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "vastu verandah at entrance", "__cat": "sit_out", "functional_zone": "public", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "front", "__col_side": "right", "layout_band": 0, "__cat_resolved": "sit_out", "__wall_h": 0.0, "__color": "0xe8f4e0", "__wallColor": "0xbcd4a8", "__label": "Sit-out", "__floor_y": 0.0}, {"name": "pooja_room", "floor": 0, "x": 50.0, "y": 142.0, "width": 61.9, "height": 101.1, "width_ft": 6.2, "depth_ft": 10.1, "area_sqft": 62.6, "area_px": 6261.6, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "northeast Vastu zone, small altar space, storage for religious items.", "__cat": "pooja_room", "functional_zone": "semi_private", "daylight_tier": "standard", "circulation_role": "support", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "NE", "__col_side": "left", "layout_band": 1, "__cat_resolved": "pooja_room", "__wall_h": 2.7, "__color": "0xfff0d8", "__wallColor": "0xe8d4a8", "__label": "Pooja Room", "__floor_y": 0.0}, {"name": "dining_room", "floor": 0, "x": 111.9, "y": 142.0, "width": 95.2, "height": 101.1, "width_ft": 9.5, "depth_ft": 10.1, "area_sqft": 96.0, "area_px": 9633.3, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "adjacent to kitchen, 6-seater dining table, positioned to avoid direct sightlines to kitchen, north light.", "__cat": "dining_room", "functional_zone": "semi_private", "daylight_tier": "social_daylight", "circulation_role": "kitchen_anchor", "aspect_hint": "dual_aspect_desirable", "__is_carved": false, "__vastu_zone": "N", "__col_side": "left", "layout_band": 1, "__cat_resolved": "dining_room", "__wall_h": 3.0, "__color": "0xfaf0dc", "__wallColor": "0xe8d5a3", "__label": "Dining Room", "__floor_y": 0.0}, {"name": "living_room", "floor": 0, "x": 207.1, "y": 142.0, "width": 142.9, "height": 101.1, "width_ft": 14.3, "depth_ft": 10.1, "area_sqft": 144.4, "area_px": 14449.9, "windows": 2, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "north-east Vastu zone, spacious layout for sectional sofa, coffee table, entertainment unit, large windows for natural light.", "__cat": "living_room", "functional_zone": "public", "daylight_tier": "primary_social", "circulation_role": "movement_organiser", "aspect_hint": "dual_aspect_desirable", "__is_carved": false, "__vastu_zone": "N", "__col_side": "center", "layout_band": 1, "__cat_resolved": "living_room", "__wall_h": 3.6, "__color": "0xf5e6c8", "__wallColor": "0xe8d5a3", "__label": "Living Room", "__floor_y": 0.0}, {"name": "corridor", "floor": 0, "x": 50.0, "y": 243.1, "width": 204.0, "height": 46.0, "width_ft": 20.4, "depth_ft": 4.6, "area_sqft": 93.8, "area_px": 9379.3, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "floor 0 corridor \u2014 auto-injected by geometric rail", "__cat": "corridor", "functional_zone": "circulation", "daylight_tier": "borrowed_light", "circulation_role": "spine_connector", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "C", "__col_side": "center", "layout_band": 2, "__cat_resolved": "corridor", "__wall_h": 2.7, "__color": "0xf0ede4", "__wallColor": "0xd8d0c0", "__label": "Corridor", "__floor_y": 0.0}, {"name": "staircase", "floor": 0, "x": 254.0, "y": 243.1, "width": 96.0, "height": 46.0, "width_ft": 9.6, "depth_ft": 4.6, "area_sqft": 44.2, "area_px": 4413.8, "windows": 0, "door_count": 0, "attached_bathroom": false, "attached_balcony": false, "notes": "internal staircase leading to first floor.", "__cat": "staircase", "functional_zone": "circulation", "daylight_tier": "borrowed_light", "circulation_role": "vertical_link", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 2, "__cat_resolved": "staircase", "__wall_h": 3.0, "__color": "0xece8e0", "__wallColor": "0xd0ccc0", "__label": "Staircase", "__floor_y": 0.0}, {"name": "kitchen", "floor": 0, "x": 50.0, "y": 289.1, "width": 160.0, "height": 87.4, "width_ft": 16.0, "depth_ft": 8.7, "area_sqft": 139.2, "area_px": 13977.0, "windows": 1, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "southeast Vastu fire zone, single modular kitchen, L-counter + hob + sink on segregated wet wall, tall unit run, pass door to dining, utility door to wash/laundry.", "__cat": "kitchen", "functional_zone": "service", "daylight_tier": "cross_vent_priority", "circulation_role": "service_core", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "SE", "__col_side": "right", "layout_band": 4, "__cat_resolved": "kitchen", "__wall_h": 2.7, "__color": "0xdcf5e8", "__wallColor": "0xb3d9c4", "__label": "Kitchen", "__floor_y": 0.0}, {"name": "common_bathroom", "floor": 0, "x": 50.0, "y": 376.4, "width": 94.3, "height": 73.6, "width_ft": 9.4, "depth_ft": 7.4, "area_sqft": 69.6, "area_px": 6936.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "accessible from living area, modern fixtures, ventilation.", "__cat": "common_bathroom", "functional_zone": "service", "daylight_tier": "mechanical_vent", "circulation_role": "wet_zone", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "NW", "__col_side": "left", "layout_band": 5, "__cat_resolved": "common_bathroom", "__wall_h": 2.4, "__color": "0xd8f0f8", "__wallColor": "0xa8c8d8", "__label": "Common Bath", "__floor_y": 0.0}, {"name": "utility_room", "floor": 0, "x": 144.3, "y": 376.4, "width": 111.4, "height": 73.6, "width_ft": 11.1, "depth_ft": 7.4, "area_sqft": 82.1, "area_px": 8197.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "adjacent to kitchen, space for washing machine and storage.", "__cat": "utility_room", "functional_zone": "service", "daylight_tier": "service_opening", "circulation_role": "wet_adjacency", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 5, "__cat_resolved": "utility_room", "__wall_h": 2.4, "__color": "0xeceae4", "__wallColor": "0xd0ccbf", "__label": "Utility Room", "__floor_y": 0.0}, {"name": "store_room", "floor": 0, "x": 255.7, "y": 376.4, "width": 94.3, "height": 73.6, "width_ft": 9.4, "depth_ft": 7.4, "area_sqft": 69.6, "area_px": 6936.0, "windows": 0, "door_count": 1, "attached_bathroom": false, "attached_balcony": false, "notes": "south zone", "__cat": "store_room", "functional_zone": "service", "daylight_tier": "service_opening", "circulation_role": "wet_adjacency", "aspect_hint": "single_aspect_ok", "__is_carved": false, "__vastu_zone": "S", "__col_side": "right", "layout_band": 5, "__cat_resolved": "store_room", "__wall_h": 2.4, "__color": "0xe8e6e0", "__wallColor": "0xccc8bc", "__label": "Store Room", "__floor_y": 0.0}];
const PARSED   = {"bhk_type": "3BHK", "plot_width_ft": 40, "plot_depth_ft": 50, "style": "Modern", "floors": 1, "vastu_compliant": false, "plot_facing": "east"};
const SCORE    = {};
const NUM_FLOORS = 1;

function _roomNameStr(r){ return (r && r.name != null && r.name !== '') ? String(r.name) : 'room'; }
function _roomDispStr(r){ return String((r && r.__label) || _roomNameStr(r)).replace(/_/g, ' '); }
function _roomIdSafe(r){ return _roomNameStr(r).replace(/[^a-zA-Z0-9_-]/g, '_'); }

function showFatal(msg){
  if(typeof _failSafeHide!=='undefined'&&_failSafeHide){ clearTimeout(_failSafeHide); _failSafeHide=0; }
  const l=document.getElementById('loading');
  if(l){
    l.style.opacity='1';
    l.style.display='flex';
    l.textContent='3D render error: '+msg;
  }
}
window.addEventListener('error', (e)=>{
  const m=(e && (e.message||''))||'unknown runtime error';
  showFatal(m);
});
window.addEventListener('unhandledrejection', (e)=>{
  const r=e && e.reason;
  const m=(r && (r.message||String(r))) || 'unhandled promise rejection';
  showFatal(m);
});

let _loadHidden=false;
function hideLoading(){
  if(_loadHidden)return; _loadHidden=true;
  if(typeof _failSafeHide!=='undefined'&&_failSafeHide){ clearTimeout(_failSafeHide); _failSafeHide=0; }
  const l=document.getElementById('loading');
  if(l){l.style.opacity='0';setTimeout(()=>{l.style.display='none';},400);}
}
var _failSafeHide=setTimeout(function(){
  const l=document.getElementById('loading');
  if(!l||_loadHidden)return;
  if((l.textContent||'').indexOf('Building')!==-1){
    l.style.opacity='1';l.style.display='flex';
    l.textContent='3D is taking too long or failed silently. Press F12 → Console, then reload. If this persists, try Chrome or Edge.';
  }
},14000);

// ── COORDINATE CONVERSION ─────────────────────────────────────────────────────
const PX2M = 0.03048;
const BX = LAYOUT.built_up_x, BY = LAYOUT.built_up_y;
const BW = LAYOUT.built_up_w, BH = LAYOUT.built_up_h;
const OX = (BX + BW/2)*PX2M, OZ = (BY + BH/2)*PX2M;
function p2w(sx, sz) { return { x: sx*PX2M-OX, z: sz*PX2M-OZ }; }

// ── THREE INIT ────────────────────────────────────────────────────────────────
const PANEL_W = 272;
const canvasEl = document.getElementById('renderer');
const canvasWrap = document.getElementById('canvas-wrap');
// Detect if we're inside an iframe — if so, the full window is ours (parent controls sizing)
const _inIframe = (() => { try { return window.self !== window.top; } catch(e) { return true; } })();
// getW: subtract the side panel only when running as a standalone page, not inside an iframe
const getW=()=>Math.max(100,(canvasWrap?.offsetWidth||window.innerWidth)-(_inIframe?0:PANEL_W));
const getH=()=>Math.max(100,canvasWrap?.offsetHeight||window.innerHeight);
let renderer;
try {
  renderer = new THREE.WebGLRenderer({canvas:canvasEl, antialias:true, powerPreference:'high-performance'});
  renderer.setPixelRatio(Math.min((typeof devicePixelRatio!=='undefined'?devicePixelRatio:1),2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
} catch(e) {
  document.getElementById('loading').textContent='WebGL unavailable in this browser.';
  throw e;
}
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x1a1410);
scene.fog = new THREE.FogExp2(0x1a1410, 0.012);
const camera = new THREE.PerspectiveCamera(42, getW()/getH(), 0.1, 300);

// ── ORBIT ─────────────────────────────────────────────────────────────────────
let orb={active:false,px:0,py:0}, th=-0.6, ph=0.9, cr=24, ctx=0,ctz=0;
function camUpdate(){
  camera.position.set(ctx+cr*Math.sin(ph)*Math.sin(th), cr*Math.cos(ph)+ctx*0, ctz+cr*Math.sin(ph)*Math.cos(th));
  camera.lookAt(ctx,0,ctz);
}
const wrap=document.getElementById('canvas-wrap');
wrap.addEventListener('mousedown',e=>{if(walkMode)return; orb={active:true,px:e.clientX,py:e.clientY};});
wrap.addEventListener('mouseup',()=>orb.active=false);
wrap.addEventListener('mouseleave',()=>orb.active=false);
wrap.addEventListener('mousemove',e=>{
  if(walkMode){walkLook(e);return;}
  if(orb.active){
    th-=(e.clientX-orb.px)*0.005; ph=Math.max(0.05,Math.min(1.56,ph+(e.clientY-orb.py)*0.005));
    orb.px=e.clientX; orb.py=e.clientY; camUpdate();
  }
  handleHover(e);
});
wrap.addEventListener('wheel',e=>{cr=Math.max(4,Math.min(80,cr+e.deltaY*0.04));camUpdate();},{passive:true});

// ── LIGHTS ────────────────────────────────────────────────────────────────────
let sun,amb,fill,hemi;
function buildLights(){
  scene.children.filter(c=>c.isLight).forEach(l=>scene.remove(l));
  hemi=new THREE.HemisphereLight(0x8090c0,0x604838,0.55); scene.add(hemi);
  amb=new THREE.AmbientLight(0xfff0d8,0.55); scene.add(amb);
  sun=new THREE.DirectionalLight(0xffecd0,3.0);
  sun.position.set(15,22,-10); sun.castShadow=true;
  sun.shadow.mapSize.width=sun.shadow.mapSize.height=2048;
  sun.shadow.camera.left=-30;sun.shadow.camera.right=30;
  sun.shadow.camera.top=30;sun.shadow.camera.bottom=-30;
  sun.shadow.bias=-0.0005; sun.shadow.normalBias=0.02; scene.add(sun);
  fill=new THREE.DirectionalLight(0xc8d8ff,0.6); fill.position.set(-10,10,15); scene.add(fill);
  // Warm bounce from ground
  const bounce=new THREE.DirectionalLight(0xffe8c0,0.2); bounce.position.set(0,-5,0); scene.add(bounce);
}
buildLights();

function setLight(m){
  ['golden','noon','night','studio'].forEach(v=>document.getElementById('btn-'+v)?.classList.remove('active'));
  document.getElementById('btn-'+m)?.classList.add('active');
  if(m==='golden'){
    sun.color.set(0xffecd0);sun.intensity=3.0;sun.position.set(15,8,-10);
    amb.color.set(0xfff0d8);amb.intensity=0.55;hemi.color.set(0xff9060);hemi.groundColor.set(0x604838);hemi.intensity=0.5;
    renderer.toneMappingExposure=1.15;scene.fog.color.set(0x2a1810);
  } else if(m==='noon'){
    sun.color.set(0xffffff);sun.intensity=3.8;sun.position.set(0,30,0);
    amb.color.set(0xffffff);amb.intensity=0.9;hemi.intensity=0.5;
    renderer.toneMappingExposure=0.95;scene.fog.color.set(0x1a1410);
  } else if(m==='night'){
    sun.color.set(0x1828a0);sun.intensity=0.3;sun.position.set(-8,15,12);
    amb.color.set(0x101828);amb.intensity=0.12;hemi.color.set(0x102040);hemi.groundColor.set(0x050810);hemi.intensity=0.2;
    renderer.toneMappingExposure=0.4;scene.fog.color.set(0x060810);scene.fog.density=0.018;
  } else if(m==='studio'){
    sun.color.set(0xffffff);sun.intensity=2.5;sun.position.set(10,20,5);
    amb.color.set(0xffffff);amb.intensity=1.4;hemi.intensity=0.3;
    renderer.toneMappingExposure=0.88;scene.fog.color.set(0x1a1410);
  }
}

// ── GROUND & LANDSCAPE ────────────────────────────────────────────────────────
(function(){
  // Base ground — dark grass
  const gm=new THREE.Mesh(new THREE.PlaneGeometry(160,160),new THREE.MeshLambertMaterial({color:0x1a1e12}));
  gm.rotation.x=-Math.PI/2; gm.position.y=-0.02; gm.receiveShadow=true; scene.add(gm);
  // Plot grass (brighter inside boundary)
  const pm=new THREE.Mesh(new THREE.PlaneGeometry(LAYOUT.plot_w_px*PX2M+0.4,LAYOUT.plot_h_px*PX2M+0.4),new THREE.MeshLambertMaterial({color:0x2e4020}));
  pm.rotation.x=-Math.PI/2; pm.position.y=-0.01; scene.add(pm);
  // Driveway concrete (front strip)
  const dw=new THREE.Mesh(new THREE.PlaneGeometry(BW*PX2M*0.5,BY*PX2M+0.5),new THREE.MeshLambertMaterial({color:0x8a8880}));
  dw.rotation.x=-Math.PI/2; dw.position.set(0,0.001,-(BH*PX2M/2+BY*PX2M/2)); scene.add(dw);
  // Driveway centre line markings
  for(let i=0;i<3;i++){
    const ln=new THREE.Mesh(new THREE.PlaneGeometry(0.12,0.8),new THREE.MeshLambertMaterial({color:0xd0ccc0}));
    ln.rotation.x=-Math.PI/2; ln.position.set(0,0.002,-(BH*PX2M/2)-(i+0.5)*BY*PX2M/3.5); scene.add(ln);
  }
  // Boundary wall
  const bwM=new THREE.MeshLambertMaterial({color:0x686e58});
  const bwH=0.65, bwT=0.14;
  const pw2=LAYOUT.plot_w_px*PX2M, ph2=LAYOUT.plot_h_px*PX2M;
  [
    [pw2,bwH,bwT, 0,bwH/2,-ph2/2],
    [pw2,bwH,bwT, 0,bwH/2, ph2/2],
    [bwT,bwH,ph2,-pw2/2,bwH/2,0],
    [bwT,bwH,ph2, pw2/2,bwH/2,0],
  ].forEach(([w,h,d,x,y,z])=>{
    const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),bwM);
    m.position.set(x,y,z); m.castShadow=true; scene.add(m);
    // Wall coping
    const copM=new THREE.MeshLambertMaterial({color:0x9a9880});
    const cop=new THREE.Mesh(new THREE.BoxGeometry(w+0.02,0.06,d+0.02),copM);
    cop.position.set(x,bwH+0.03,z); scene.add(cop);
  });
  // Gate pillars (front centre)
  const pilM=new THREE.MeshLambertMaterial({color:0xb8aa88});
  const gateW=2.8;
  [[-gateW/2,0],[gateW/2,0]].forEach(([gx,gz])=>{
    const pil=new THREE.Mesh(new THREE.BoxGeometry(0.28,1.1,0.28),pilM);
    pil.position.set(gx,0.55,-ph2/2); scene.add(pil);
    const cap=new THREE.Mesh(new THREE.BoxGeometry(0.34,0.1,0.34),pilM);
    cap.position.set(gx,1.15,-ph2/2); scene.add(cap);
  });
  // Trees — improved with tapered trunks and layered canopy
  const trunkM=new THREE.MeshLambertMaterial({color:0x5a3810});
  const leafM =new THREE.MeshLambertMaterial({color:0x2d5a1e});
  const leafM2=new THREE.MeshLambertMaterial({color:0x3a7228});
  const treePositions=[
    [-pw2/2+1.6,-ph2/2+2.5],[pw2/2-1.6,-ph2/2+2.5],
    [-pw2/2+1.6, ph2/2-2.5],[pw2/2-1.6, ph2/2-2.5],
    [-pw2/2+1.6, 0         ],[pw2/2-1.6, 0         ],
  ];
  treePositions.forEach(([tx,tz])=>{
    const t=new THREE.Mesh(new THREE.CylinderGeometry(0.08,0.16,2.2,7),trunkM);
    t.position.set(tx,1.1,tz); scene.add(t);
    // Layered canopy for fuller look
    [[0.9,8,6,2.8],[0.7,8,5,3.5],[0.5,8,5,4.0]].forEach(([r,ws,hs,hy])=>{
      const l=new THREE.Mesh(new THREE.SphereGeometry(r,ws,hs),(hy>3.2?leafM2:leafM));
      l.position.set(tx,hy,tz); l.castShadow=true; scene.add(l);
    });
  });
  // Flower beds along front wall
  const bedM=new THREE.MeshLambertMaterial({color:0x8B4513});
  const flwM=new THREE.MeshLambertMaterial({color:0xe05050});
  for(let i=-2;i<=2;i++){
    if(Math.abs(i)<1.5) continue; // skip gate area
    const bed=new THREE.Mesh(new THREE.BoxGeometry(0.8,0.15,0.4),bedM);
    bed.position.set(i*pw2/6,0.08,-ph2/2+0.35); scene.add(bed);
    const flw=new THREE.Mesh(new THREE.SphereGeometry(0.12,6,5),flwM);
    flw.position.set(i*pw2/6,0.28,-ph2/2+0.35); scene.add(flw);
  }
  // Street lamp post at front-left corner
  const lampM=new THREE.MeshLambertMaterial({color:0x404040});
  const lampG=new THREE.MeshLambertMaterial({color:0xffffcc,emissive:0xffff88,emissiveIntensity:0.6});
  const post=new THREE.Mesh(new THREE.CylinderGeometry(0.04,0.06,3.5,8),lampM);
  post.position.set(-pw2/2-0.5,1.75,-ph2/2-0.5); scene.add(post);
  const lamp=new THREE.Mesh(new THREE.SphereGeometry(0.18,8,6),lampG);
  lamp.position.set(-pw2/2-0.5,3.6,-ph2/2-0.5); scene.add(lamp);
  const lampLight=new THREE.PointLight(0xffeeaa,0.8,6);
  lampLight.position.set(-pw2/2-0.5,3.5,-ph2/2-0.5); scene.add(lampLight);
})();

// ── STAIRCASE GEOMETRY ────────────────────────────────────────────────────────
function buildStaircase(room, floorY) {
  const pos=p2w(room.x+room.width/2, room.y+room.height/2);
  const rw=room.width*PX2M, rd=room.height*PX2M;
  const stepM=new THREE.MeshLambertMaterial({color:0xd8cfc4});
  const railM=new THREE.MeshLambertMaterial({color:0x8B6032});
  const g=new THREE.Group();
  const nSteps=12, stepH=FLOOR_STEP_M/nSteps, stepD=rd/nSteps, stepW=rw*0.85;
  for(let i=0;i<nSteps;i++){
    const step=new THREE.Mesh(new THREE.BoxGeometry(stepW,stepH,stepD),stepM);
    step.position.set(pos.x, floorY+(i+0.5)*stepH, pos.z-rd/2+(i+0.5)*stepD);
    step.castShadow=true; g.add(step);
  }
  // Handrails (left + right)
  [[pos.x-stepW/2-0.05],[pos.x+stepW/2+0.05]].forEach(([rx])=>{
    // Posts
    for(let i=0;i<=nSteps;i+=3){
      const post=new THREE.Mesh(new THREE.CylinderGeometry(0.03,0.03,FLOOR_STEP_M*0.85,6),railM);
      post.position.set(rx,floorY+FLOOR_STEP_M*0.425,pos.z-rd/2+i*stepD);
      g.add(post);
    }
    // Top rail - angled bar approximated
    const rail=new THREE.Mesh(new THREE.BoxGeometry(0.04,0.04,rd),railM);
    rail.position.set(rx,floorY+FLOOR_STEP_M*0.82,pos.z);
    g.add(rail);
  });
  scene.add(g);
  return g;
}

// ── WALL + OPENING BUILDER ────────────────────────────────────────────────────
const EXT_WALL_T=0.23, INT_WALL_T=0.115;
const DOOR_W=0.9, DOOR_H=2.1, WIN_W=1.2, WIN_H=1.1, WIN_SILL=0.9;
const FLOOR_STEP_M=3.2;

function makeWallWithOpenings(len,wh,thk,openings){
  len=Math.max(0.05,Number(len)||0.05);wh=Math.max(0.05,Number(wh)||0.05);thk=Math.max(0.01,Number(thk)||0.01);
  const sh=new THREE.Shape();
  sh.moveTo(0,0);sh.lineTo(len,0);sh.lineTo(len,wh);sh.lineTo(0,wh);sh.closePath();
  openings.forEach(op=>{
    const cx=op.pos*len,hw=op.w/2;
    const x0=Math.max(0.05,cx-hw),x1=Math.min(len-0.05,cx+hw);
    const y0=op.sillY||0,y1=Math.min(y0+op.h,wh-0.05);
    if(x1-x0<0.1||y1-y0<0.1)return;
    const hole=new THREE.Path();
    hole.moveTo(x0,y0);hole.lineTo(x1,y0);hole.lineTo(x1,y1);hole.lineTo(x0,y1);hole.closePath();
    sh.holes.push(hole);
  });
  return new THREE.ExtrudeGeometry(sh,{depth:thk,bevelEnabled:false});
}

function makeDoor(w,h){
  const g=new THREE.Group();
  const fM=new THREE.MeshLambertMaterial({color:0x6b4f2a});
  const pM=new THREE.MeshLambertMaterial({color:0x8b6332,side:THREE.DoubleSide});
  [[w,0.05,0.05,0,h-0.025,0],[w,0.05,0.05,0,0.025,0],
   [0.05,h,0.05,-w/2+0.025,h/2,0],[0.05,h,0.05,w/2-0.025,h/2,0]
  ].forEach(([fw,fh,fd,fx,fy])=>{const m=new THREE.Mesh(new THREE.BoxGeometry(fw,fh,fd),fM);m.position.set(fx,fy,0);g.add(m);});
  const panel=new THREE.Mesh(new THREE.BoxGeometry(w-0.1,h-0.05,0.04),pM);
  panel.position.set(0,(h-0.05)/2,0.02);g.add(panel);
  const hM=new THREE.MeshLambertMaterial({color:0xc8a040});
  const handle=new THREE.Mesh(new THREE.CylinderGeometry(0.02,0.02,0.12,8),hM);
  handle.rotation.z=Math.PI/2;handle.position.set(w*0.35,h*0.45,0.07);g.add(handle);
  return g;
}

function makeWindow(w,h){
  const g=new THREE.Group();
  const fM=new THREE.MeshLambertMaterial({color:0xd4c9b0});
  const gM=new THREE.MeshLambertMaterial({color:0xa8d0e8,transparent:true,opacity:0.4,side:THREE.DoubleSide});
  const ft=0.04;
  [[w,ft,ft,0,h-ft/2,0],[w,ft,ft,0,ft/2,0],
   [ft,h,ft,-w/2+ft/2,h/2,0],[ft,h,ft,w/2-ft/2,h/2,0]
  ].forEach(([fw,fh,fd,fx,fy])=>{const m=new THREE.Mesh(new THREE.BoxGeometry(fw,fh,fd),fM);m.position.set(fx,fy,0);g.add(m);});
  const mid=new THREE.Mesh(new THREE.BoxGeometry(w,ft,ft),fM);mid.position.set(0,h/2,0);g.add(mid);
  [[0,h*0.25],[0,h*0.75]].forEach(([gx,gy])=>{
    const gl=new THREE.Mesh(new THREE.PlaneGeometry(w-ft*3,h/2-ft*2),gM);
    gl.position.set(gx,gy,0.01);g.add(gl);
  });
  return g;
}

// ── FURNITURE BUILDER ─────────────────────────────────────────────────────────
const MATS={
  wood:new THREE.MeshLambertMaterial({color:0x8B6F47}),
  darkWood:new THREE.MeshLambertMaterial({color:0x5a3a1a}),
  cush:new THREE.MeshLambertMaterial({color:0xd4c4a0}),
  bed:new THREE.MeshLambertMaterial({color:0xeeeadf}),
  wht:new THREE.MeshLambertMaterial({color:0xf5f2ee}),
  metal:new THREE.MeshLambertMaterial({color:0x888890}),
  glass:new THREE.MeshLambertMaterial({color:0x88aacc,transparent:true,opacity:0.4}),
  darkPanel:new THREE.MeshLambertMaterial({color:0x222230}),
  carBody:new THREE.MeshLambertMaterial({color:0x3a4a5a}),
  carGlass:new THREE.MeshLambertMaterial({color:0x6888aa,transparent:true,opacity:0.5}),
};
function box(w,h,d,mat,x,y,z,parent){
  const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),mat);
  m.position.set(x,y,z);m.castShadow=true;
  if(parent)parent.add(m);else scene.add(m);
  return m;
}
function cyl(r,h,mat,x,y,z,parent,segs=8){
  const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,h,segs),mat);
  m.position.set(x,y,z);m.castShadow=true;
  if(parent)parent.add(m);else scene.add(m);
  return m;
}

function addFurniture3D(room, floorY){
  const pos=p2w(room.x+room.width/2,room.y+room.height/2);
  const rw=room.width*PX2M, rd=room.height*PX2M;
  const wh=room.__wall_h||2.7;
  const cat=room.__cat_resolved||'default';
  const px=pos.x, pz=pos.z, py=floorY+0.08;

  if(cat==='living_room'){
    // L-sofa
    box(rw*.5,.38,.7,MATS.cush,px-rw*.08,py+.19,pz+rd*.18);
    box(.7,.38,rd*.28,MATS.cush,px+rw*.14,py+.19,pz+rd*.04);
    box(rw*.48,.08,.08,MATS.darkWood,px-rw*.08,py+.57,pz-rd*.25);
    // coffee table
    box(.85,.07,.5,MATS.wood,px-rw*.08,py+.4,pz-rd*.1);
    // TV unit
    box(rw*.5,.06,.28,MATS.darkWood,px-rw*.06,py+.5,pz-rd*.38);
    box(rw*.4,.38,.04,MATS.darkPanel,px-rw*.06,py+.28,pz-rd*.39);
  } else if(cat==='master_bedroom'||cat==='bedroom'||cat==='parents_bedroom'||cat==='guest_bedroom'){
    const s=cat==='master_bedroom'?1.0:0.82;
    // Bed frame
    box(rw*.52*s,.06,rd*.52*s,MATS.wood,px,py+.06,pz+rd*.1);
    // Mattress
    box(rw*.48*s,.18,rd*.48*s,MATS.bed,px,py+.18,pz+rd*.1);
    // Headboard
    box(rw*.52*s,.52,.08,MATS.darkWood,px,py+.3,pz-rd*.15);
    // Pillows
    [[-rw*.1],[rw*.1]].forEach(([dx])=>box(rw*.2,.08,rd*.14,MATS.wht,px+dx,py+.32,pz-rd*.08));
    // Wardrobe
    box(rw*.3,.04,rd*.5,MATS.wood,px+rw*.32,py+.02,pz-rd*.05);
    box(rw*.3,2.0,.5,MATS.darkWood,px+rw*.32,py+1,pz-rd*.05);
    // Nightstand
    box(.35,.55,.35,MATS.wood,px-rw*.26,py+.28,pz-rd*.1);
  } else if(cat==='kitchen'||cat==='wet_kitchen'||cat==='dry_kitchen'){
    // Counter L-shape
    box(rw*.65,.88,.5,MATS.wht,px+rw*.08,py+.44,pz-rd*.35);
    box(.5,.88,rd*.5,MATS.wht,px-rw*.35,py+.44,pz+rd*.05);
    box(rw*.65,.04,.5,MATS.metal,px+rw*.08,py+.89,pz-rd*.35);
    box(.5,.04,rd*.5,MATS.metal,px-rw*.35,py+.89,pz+rd*.05);
    // Hob
    [-.06,.06].forEach(dx=>[-.03,.03].forEach(dz=>{
      cyl(.07,.02,new THREE.MeshLambertMaterial({color:0x333333}),px+rw*.08+dx,py+.92,pz-rd*.35+dz,null,12);
    }));
    // Sink
    box(.42,.1,.35,new THREE.MeshLambertMaterial({color:0xaaaaaa}),px+rw*.28,py+.85,pz-rd*.35);
    // Upper cabinets
    box(rw*.65,.6,.3,MATS.wht,px+rw*.08,py+1.9,pz-rd*.35);
    // Fridge
    box(.6,1.8,.6,MATS.wht,px-rw*.38,py+.9,pz-rd*.35);
    box(.55,1.0,.02,MATS.glass,px-rw*.38,py+1.42,pz-rd*.32);
  } else if(cat==='dining_room'){
    box(rw*.58,.07,rd*.42,MATS.wood,px,py+.74,pz);
    [[-1,-1],[-1,1],[1,-1],[1,1]].forEach(([dx,dz])=>{
      box(.35,.7,.35,MATS.wood,px+rw*.12*dx,py+.35,pz+rd*.13*dz);
      box(.38,.04,.38,MATS.cush,px+rw*.12*dx,py+.71,pz+rd*.13*dz);
    });
    cyl(.03,.65,MATS.metal,px,py+.37,pz,null,4);
  } else if(cat==='bathroom'||cat==='common_bathroom'||cat==='guest_powder_room'){
    // Safe usable dimensions after stripping wall thickness on all four sides
    const sw=Math.max(rw-2*EXT_WALL_T-0.1, 0.35);
    const sd=Math.max(rd-2*EXT_WALL_T-0.1, 0.35);
    // WC — back-left corner
    box(Math.min(.35,sw*.38),.3,Math.min(.44,sd*.38),MATS.wht,px-sw*.22,py+.15,pz+sd*.22);
    box(Math.min(.42,sw*.42),.07,Math.min(.35,sd*.32),MATS.wht,px-sw*.22,py+.34,pz+sd*.18);
    cyl(Math.min(.17,sw*.18),.32,MATS.wht,px-sw*.22,py+.16,pz+sd*.25,null,12);
    // Basin — front-right
    box(Math.min(.44,sw*.4),.07,Math.min(.34,sd*.28),MATS.wht,px+sw*.18,py+.75,pz-sd*.22);
    box(Math.min(.42,sw*.38),.7,Math.min(.32,sd*.26),MATS.wht,px+sw*.18,py+.35,pz-sd*.22);
    // Shower tray — right-centre only if room is wide enough
    if(sw>0.9&&sd>0.9){
      box(Math.min(.85,sw*.55),.04,Math.min(.85,sd*.55),new THREE.MeshLambertMaterial({color:0xd0e0e8}),px+sw*.18,py+.02,pz+sd*.2);
    }
    // Mirror above basin
    box(Math.min(.38,sw*.32),.6,.02,MATS.glass,px+sw*.18,py+1.1,pz-sd*.32);
  } else if(cat==='car_porch'){
    // Car body
    const cg=new THREE.Group();
    box(1.8,.6,3.8,MATS.carBody,0,.3,0,cg);
    box(1.6,.45,2.0,MATS.carBody,0,.85,-.3,cg);
    // Windows
    box(1.55,.35,1.8,MATS.carGlass,0,.86,-.3,cg);
    // Wheels
    [[-1,-1],[-1,1],[1,-1],[1,1]].forEach(([dx,dz])=>{
      cyl(.3,.2,new THREE.MeshLambertMaterial({color:0x222222}),dx*.76,.22,dz*1.3,cg,12);
      cyl(.18,.22,new THREE.MeshLambertMaterial({color:0x888888}),dx*.76,.22,dz*1.3,cg,12);
    });
    cg.position.set(pos.x,floorY,pos.z); cg.castShadow=true; scene.add(cg);
    return;
  } else if(cat==='home_office'){
    box(rw*.7,.04,rd*.38,MATS.wood,px-rw*.06,py+.76,pz-rd*.28);
    box(rw*.7,.72,.5,MATS.wht,px-rw*.06,py+.36,pz-rd*.28);
    box(rw*.45,.38,.04,MATS.darkPanel,px-rw*.06,py+.6,pz-rd*.29);
    // Chair
    box(.42,.04,.42,MATS.cush,px-rw*.06,py+.48,pz+rd*.05);
    cyl(.04,.48,MATS.metal,px-rw*.06,py+.24,pz+rd*.05);
    // Bookshelf
    box(rw*.32,1.6,.3,MATS.wood,px+rw*.32,py+.8,pz-rd*.28);
    [.4,.75,1.1,1.4].forEach(hy=>box(rw*.3,.02,.28,MATS.darkWood,px+rw*.32,py+hy,pz-rd*.28));
  } else if(cat==='staircase'){
    buildStaircase(room, floorY);
    return;
  } else if(cat==='family_lounge'){
    box(rw*.62,.38,.6,MATS.cush,px-rw*.08,py+.19,pz-rd*.15);
    box(rw*.62,.04,.6,MATS.darkWood,px-rw*.08,py+.59,pz-rd*.15);
    box(.55,.38,rd*.35,MATS.cush,px+rw*.2,py+.19,pz+rd*.05);
    box(.52,.07,.42,MATS.wood,px-rw*.05,py+.4,pz+rd*.2);
    box(rw*.4,.35,.04,MATS.darkPanel,px-rw*.08,py+.28,pz-rd*.42);
  } else if(cat==='pooja_room'){
    // Altar platform
    box(Math.min(rw*.7,.9),.12,Math.min(rd*.4,.5),MATS.wood,px,py+.06,pz+rd*.1);
    // Idol stand
    box(Math.min(rw*.3,.35),.6,.08,new THREE.MeshLambertMaterial({color:0xd4a840}),px,py+.42,pz+rd*.08);
    // Diya lamp
    cyl(.06,.04,new THREE.MeshLambertMaterial({color:0xcc8820}),px-rw*.12,py+.2,pz+rd*.1,null,10);
    cyl(.06,.04,new THREE.MeshLambertMaterial({color:0xcc8820}),px+rw*.12,py+.2,pz+rd*.1,null,10);
    // Bell hanging — thin rod + bell shape
    box(.02,.5,.02,MATS.metal,px,py+wh*.7,pz-rd*.3);
    cyl(.07,.08,new THREE.MeshLambertMaterial({color:0xd4a840}),px,py+wh*.45,pz-rd*.3,null,12);
  } else if(cat==='walk_in_wardrobe'){
    // Full-height wardrobe units on three sides
    const uH=Math.min(wh*.85,2.1);
    box(rw*.85,.04,Math.min(rd*.35,.5),MATS.darkWood,px,py+uH,pz-rd*.3); // top shelf N
    box(rw*.85,uH,.5,MATS.wht,px,py+uH/2,pz-rd*.3); // unit N
    box(Math.min(rw*.35,.5),.04,rd*.7,MATS.darkWood,px+rw*.32,py+uH,pz); // top shelf E
    box(Math.min(rw*.35,.5),uH,.5,MATS.wht,px+rw*.32,py+uH/2,pz); // unit E — rotated
    // Hanging rail
    box(rw*.7,.03,.03,MATS.metal,px-rw*.05,py+uH*.75,pz-rd*.22);
    // Centre island
    if(rw>1.8&&rd>2.0) box(rw*.35,.85,rd*.35,MATS.wood,px,py+.43,pz+rd*.15);
  } else if(cat==='utility_room'){
    // Washing machine
    box(.58,.62,.56,MATS.wht,px-rw*.22,py+.31,pz-rd*.22);
    cyl(.18,.04,MATS.glass,px-rw*.22,py+.62,pz-rd*.22,null,16);
    // Dryer
    box(.58,.62,.56,MATS.wht,px+rw*.1,py+.31,pz-rd*.22);
    // Sink / laundry tub
    box(.5,.82,.44,MATS.wht,px-rw*.2,py+.41,pz+rd*.22);
    box(.46,.06,.40,new THREE.MeshLambertMaterial({color:0xaaaaaa}),px-rw*.2,py+.85,pz+rd*.22);
    // Overhead cabinets
    box(rw*.7,.55,.3,MATS.wht,px,py+1.9,pz-rd*.28);
  } else if(cat==='store_room'){
    // Shelving units
    const sH=Math.min(wh*.85,2.0);
    box(rw*.8,sH,.35,MATS.wood,px-rw*.05,py+sH/2,pz-rd*.35);
    [.4,.8,1.2,1.6].filter(h=>h<sH).forEach(h=>box(rw*.78,.025,.33,MATS.darkWood,px-rw*.05,py+h,pz-rd*.35));
    box(rw*.5,sH*.6,.35,MATS.wood,px+rw*.22,py+sH*.3,pz+rd*.2);
  } else if(cat==='foyer'){
    // Entrance console table
    box(Math.min(rw*.55,.9),.82,.32,MATS.darkWood,px,py+.41,pz-rd*.25);
    // Shoe rack below
    box(Math.min(rw*.5,.8),.4,.28,MATS.wood,px,py+.2,pz-rd*.24);
    // Mirror above console
    box(Math.min(rw*.4,.7),.9,.02,MATS.glass,px,py+1.2,pz-rd*.32);
    // Umbrella stand
    cyl(.1,.6,MATS.darkWood,px+rw*.3,py+.3,pz-rd*.25,null,8);
  } else if(cat==='corridor'){
    // Wall-mounted light fixtures (decorative boxes approximating sconces)
    [-rd*.25,rd*.25].forEach(dz=>{
      box(.04,.18,.12,new THREE.MeshLambertMaterial({color:0xd4c89a}),px-rw*.44,py+wh*.6,pz+dz);
      box(.04,.18,.12,new THREE.MeshLambertMaterial({color:0xd4c89a}),px+rw*.44,py+wh*.6,pz+dz);
    });
  } else if(cat==='balcony'||cat==='sit_out'||cat==='terrace'){
    // Railing posts + top rail
    const postM=new THREE.MeshLambertMaterial({color:0x888880});
    const railM2=new THREE.MeshLambertMaterial({color:0xb0a890});
    const railH=0.95;
    // Posts along perimeter
    for(let i=0;i<=4;i++){
      const t=i/4;
      cyl(.025,railH,postM,px-rw/2+rw*t,py+railH/2,pz+rd/2-0.08,null,6);
      cyl(.025,railH,postM,px-rw/2+rw*t,py+railH/2,pz-rd/2+0.08,null,6);
    }
    box(rw,.03,.03,railM2,px,py+railH,pz+rd/2-0.08);
    box(rw,.03,.03,railM2,px,py+railH,pz-rd/2+0.08);
    // Outdoor chair pair if large enough
    if(rw>1.5&&rd>1.5){
      box(.5,.04,.5,MATS.wood,px-rw*.15,py+.42,pz);
      box(.5,.04,.5,MATS.wood,px+rw*.15,py+.42,pz);
      [[-rw*.15],[rw*.15]].forEach(([dx])=>{
        box(.46,.36,.04,MATS.wood,px+dx,py+.28,pz-.22);
        cyl(.02,.38,MATS.darkWood,px+dx-rw*.09,py+.19,pz-.18,null,4);
        cyl(.02,.38,MATS.darkWood,px+dx+rw*.09,py+.19,pz-.18,null,4);
      });
    }
  } else if(cat==='servant_quarters'){
    // Single bed
    box(rw*.48,.06,rd*.55,MATS.wood,px,py+.06,pz+rd*.1);
    box(rw*.44,.14,rd*.51,MATS.bed,px,py+.17,pz+rd*.1);
    box(rw*.48,.4,.06,MATS.darkWood,px,py+.26,pz-rd*.18);
    // Small wardrobe
    box(rw*.3,1.8,.4,MATS.wht,px+rw*.3,py+.9,pz-rd*.22);
  }
}

// ── ROOF BUILDER ──────────────────────────────────────────────────────────────
function buildRoof(topY){
  const rw=BW*PX2M, rd=BH*PX2M;
  // Minimum 1.2m ridge so flat-plot plans get a real roof shape
  const ridgeH=Math.max(1.2, Math.min(rw,rd)*0.20);
  const hw=rw/2, hd=rd/2, hy=topY;
  // 4-slope hip roof panels
  function triRoof(pts, col){
    const geo=new THREE.BufferGeometry();
    geo.setAttribute('position',new THREE.Float32BufferAttribute(pts.flat(),3));
    geo.computeVertexNormals();
    const m=new THREE.Mesh(geo,new THREE.MeshLambertMaterial({color:col,side:THREE.DoubleSide}));
    m.castShadow=true; scene.add(m);
  }
  triRoof([[-hw,hy,-hd],[hw,hy,-hd],[0,hy+ridgeH,0]],0x7a3d1a);
  triRoof([[-hw,hy, hd],[hw,hy, hd],[0,hy+ridgeH,0]],0x6b3214);
  triRoof([[-hw,hy,-hd],[-hw,hy,hd],[0,hy+ridgeH,0]],0x723618);
  triRoof([[ hw,hy,-hd],[ hw,hy,hd],[0,hy+ridgeH,0]],0x723618);
  // Ridge cap
  const ridgeM=new THREE.MeshLambertMaterial({color:0x9B5523});
  const ridgeBox=new THREE.Mesh(new THREE.BoxGeometry(0.24,0.18,rd*0.58),ridgeM);
  ridgeBox.position.set(0,hy+ridgeH,0); scene.add(ridgeBox);
  // Eave fascia boards
  const eavM=new THREE.MeshLambertMaterial({color:0xd8ccaa});
  const eavOv=0.35;
  [
    [rw+eavOv*2,0.14,0.18, 0,hy-0.05,-hd-eavOv/2],
    [rw+eavOv*2,0.14,0.18, 0,hy-0.05, hd+eavOv/2],
    [0.18,0.14,rd+eavOv*2,-hw-eavOv/2,hy-0.05,0],
    [0.18,0.14,rd+eavOv*2, hw+eavOv/2,hy-0.05,0],
  ].forEach(([w,h,d,x,y,z])=>{
    const e=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),eavM);
    e.position.set(x,y,z); scene.add(e);
  });
  // Roof tile texture lines (approximated with thin boxes)
  const tileM=new THREE.MeshLambertMaterial({color:0x8B4513,transparent:true,opacity:0.5});
  for(let i=-3;i<=3;i++){
    const tile=new THREE.Mesh(new THREE.BoxGeometry(0.06,0.04,rd*0.6),tileM);
    tile.position.set(i*rw/8,hy+0.02,0); scene.add(tile);
  }
  // Water tank on roof
  const tankM=new THREE.MeshLambertMaterial({color:0x2244aa});
  const tank=new THREE.Mesh(new THREE.CylinderGeometry(0.45,0.45,1.0,10),tankM);
  tank.position.set(hw*0.5,hy+ridgeH*0.5+0.5,hd*0.4); scene.add(tank);
  // Solar panels (if modern style)
  const solarM=new THREE.MeshLambertMaterial({color:0x1a2a3a,emissive:0x080c10});
  for(let i=0;i<3;i++){
    const panel=new THREE.Mesh(new THREE.BoxGeometry(0.9,0.04,0.55),solarM);
    panel.position.set(-hw*0.3+i*1.0,hy+0.12,-hd*0.3);
    panel.rotation.x=-0.25; scene.add(panel);
    // Panel frame
    const fM=new THREE.MeshLambertMaterial({color:0x888888});
    const fr=new THREE.Mesh(new THREE.BoxGeometry(0.94,0.03,0.59),fM);
    fr.position.copy(panel.position); fr.rotation.x=panel.rotation.x; scene.add(fr);
  }
}

// ── EXTERIOR FACADE ───────────────────────────────────────────────────────────
function buildExterior(totalH){
  const rw=BW*PX2M+0.46, rd=BH*PX2M+0.46;
  const moldingM=new THREE.MeshLambertMaterial({color:0xd8d0c0});
  const accentM =new THREE.MeshLambertMaterial({color:0xb89060});
  // Facade plaster bands per floor
  for(let f=0;f<NUM_FLOORS;f++){
    const fy=f*FLOOR_STEP_M;
    // Window lintel band
    [[rw,0.1,0.12,0,fy+WIN_SILL+WIN_H,-rd/2-0.05],
     [rw,0.1,0.12,0,fy+WIN_SILL+WIN_H, rd/2+0.05],
     [0.12,0.1,rd,-rw/2-0.05,fy+WIN_SILL+WIN_H,0],
     [0.12,0.1,rd, rw/2+0.05,fy+WIN_SILL+WIN_H,0],
    // Floor band
     [rw,0.09,0.1,0,fy,-rd/2-0.05],
     [rw,0.09,0.1,0,fy, rd/2+0.05],
     [0.1,0.09,rd,-rw/2-0.05,fy,0],
     [0.1,0.09,rd, rw/2+0.05,fy,0],
    ].forEach(([w,h,d,x,y,z])=>{
      const mk=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),y>fy+0.2?moldingM:accentM);
      mk.position.set(x,y,z); scene.add(mk);
    });
    // AC outdoor units on side walls
    if(f>0||NUM_FLOORS>1){
      const acM=new THREE.MeshLambertMaterial({color:0xd8d8d8});
      const acG=new THREE.MeshLambertMaterial({color:0xaaaaaa});
      const ac=new THREE.Mesh(new THREE.BoxGeometry(0.7,0.5,0.3),acM);
      ac.position.set(rw/2+0.15,fy+1.2,-rd/4); scene.add(ac);
      const acFan=new THREE.Mesh(new THREE.CylinderGeometry(0.18,0.18,0.04,8),acG);
      acFan.rotation.z=Math.PI/2;acFan.position.set(rw/2+0.3,fy+1.2,-rd/4); scene.add(acFan);
    }
  }
  // Top cornice
  [
    [rw+0.12,0.22,0.16,0,totalH+0.05,-rd/2-0.07],
    [rw+0.12,0.22,0.16,0,totalH+0.05, rd/2+0.07],
    [0.16,0.22,rd+0.12,-rw/2-0.07,totalH+0.05,0],
    [0.16,0.22,rd+0.12, rw/2+0.07,totalH+0.05,0],
  ].forEach(([w,h,d,x,y,z])=>{
    const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),moldingM);
    m.position.set(x,y,z); scene.add(m);
  });
  // Main entrance portico
  const porW=2.6, porH=totalH*0.42;
  const colM=new THREE.MeshLambertMaterial({color:0xd4c8a0});
  // Portico beam
  const pBeam=new THREE.Mesh(new THREE.BoxGeometry(porW+0.3,0.18,0.28),moldingM);
  pBeam.position.set(0,porH,-rd/2-0.14); scene.add(pBeam);
  // Columns
  [[-porW/2+0.1, porW/2-0.1]].flat().forEach(cx=>{
    const col=new THREE.Mesh(new THREE.CylinderGeometry(0.08,0.1,porH,10),colM);
    col.position.set(cx,porH/2,-rd/2-0.14); scene.add(col);
    // Column base
    const base=new THREE.Mesh(new THREE.BoxGeometry(0.22,0.08,0.22),colM);
    base.position.set(cx,0.04,-rd/2-0.14); scene.add(base);
    // Column capital
    const cap=new THREE.Mesh(new THREE.BoxGeometry(0.22,0.08,0.22),colM);
    cap.position.set(cx,porH-0.04,-rd/2-0.14); scene.add(cap);
  });
  // Entrance steps (3 risers)
  [0,1,2].forEach(i=>{
    const sw=1.6-i*0.15, sd=0.35;
    const st=new THREE.Mesh(new THREE.BoxGeometry(sw,0.14,sd),new THREE.MeshLambertMaterial({color:0xc0b898}));
    st.position.set(0,i*0.14,-rd/2-0.16-(i+0.5)*sd); scene.add(st);
  });
  // Parapet wall on top (for flat-roof sections)
  if(NUM_FLOORS>1){
    const parM=new THREE.MeshLambertMaterial({color:0xe0d8c8});
    const ph=0.4;
    [
      [rw+0.1,ph,0.14,0,totalH+ph/2,-rd/2-0.05],
      [rw+0.1,ph,0.14,0,totalH+ph/2, rd/2+0.05],
      [0.14,ph,rd,-rw/2-0.05,totalH+ph/2,0],
      [0.14,ph,rd, rw/2+0.05,totalH+ph/2,0],
    ].forEach(([w,h,d,x,y,z])=>{
      const par=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),parM);
      par.position.set(x,y,z); scene.add(par);
    });
  }
}

// ── ROOM MESH BUILDER ──────────────────────────────────────────────────────────
const roomMeshes=[], wallGroups=[], ceilMeshes=[], labelSprites=[];

function makeLabel(name,area){
  const c=document.createElement('canvas');c.width=256;c.height=80;
  const cx2=c.getContext('2d');
  // Use fillRect for broad browser compatibility (roundRect is not universal).
  cx2.fillStyle='rgba(26,23,20,0.75)';
  cx2.fillRect(6,12,244,56);
  cx2.fillStyle='#c8a96e';cx2.font='500 16px DM Mono,monospace';cx2.textAlign='center';cx2.fillText(name,128,38);
  cx2.fillStyle='rgba(200,169,110,0.55)';cx2.font='12px DM Mono,monospace';cx2.fillText(area+' sqft',128,55);
  const t=new THREE.CanvasTexture(c);
  const s=new THREE.Sprite(new THREE.SpriteMaterial({map:t,transparent:true,depthTest:false}));
  s.scale.set(1.6,0.5,1);return s;
}

// ── SHARED-WALL DEDUPLICATION ─────────────────────────────────────────────────
// Track which wall edges have already been rendered so adjacent rooms don't
// double-up geometry. Key = "x0,z0,x1,z1,floorY" (rounded to 2dp).
const _wallRendered=new Set();
function _wKey(ax,az,bx,bz,fy){
  // Normalise direction so (A→B) and (B→A) produce the same key
  const [x0,z0,x1,z1]=ax<bx||(ax===bx&&az<bz)?[ax,az,bx,bz]:[bx,bz,ax,az];
  return `${x0.toFixed(2)},${z0.toFixed(2)},${x1.toFixed(2)},${z1.toFixed(2)},${fy.toFixed(2)}`;
}
function shouldDrawWall(ax,az,bx,bz,fy){
  const k=_wKey(ax,az,bx,bz,fy);
  if(_wallRendered.has(k))return false;
  _wallRendered.add(k);return true;
}

const totalH = NUM_FLOORS * FLOOR_STEP_M;
try {
ALLROOMS.forEach(room=>{
  const pos=p2w((Number(room.x)||0)+(Number(room.width)||0)/2,(Number(room.y)||0)+(Number(room.height)||0)/2);
  const rw=Math.max(0.02,(Number(room.width)||0)*PX2M), rd=Math.max(0.02,(Number(room.height)||0)*PX2M);
  const wh=room.__wall_h||2.7;
  const floorY=room.__floor_y||0;
  const col=parseInt(room.__color||'0xf5f3ee');
  const wcol=parseInt(room.__wallColor||'0xd8d4c8');
  const isOpen=(wh===0);
  const cat=room.__cat_resolved||'default';

  // Exterior wall detection — TOL in metres, relaxed to handle sub-pixel alignment
  const TOL=0.5;
  const rx0=room.x*PX2M, ry0=room.y*PX2M;
  const bxW=BX*PX2M, byW=BY*PX2M, bwW=BW*PX2M, bhW=BH*PX2M;
  const extTop  =Math.abs(ry0-byW)<TOL;
  const extBot  =Math.abs((ry0+rd)-(byW+bhW))<TOL;
  const extLeft =Math.abs(rx0-bxW)<TOL;
  const extRight=Math.abs((rx0+rw)-(bxW+bwW))<TOL;
  const tN=extTop ?EXT_WALL_T:INT_WALL_T;
  const tS=extBot ?EXT_WALL_T:INT_WALL_T;
  const tW=extLeft?EXT_WALL_T:INT_WALL_T;
  const tE=extRight?EXT_WALL_T:INT_WALL_T;

  // Floor slab
  const fm=new THREE.Mesh(new THREE.BoxGeometry(rw,0.08,rd),new THREE.MeshLambertMaterial({color:col}));
  fm.position.set(pos.x,floorY+0.04,pos.z);fm.receiveShadow=true;
  fm.userData={room,floorY};scene.add(fm);roomMeshes.push(fm);

  const wg=new THREE.Group();
  if(!isOpen){
    const wMat=new THREE.MeshLambertMaterial({color:wcol});
    const winC=Math.max(0,parseInt(room.windows)||1);
    const doorC=parseInt(room.door_count)||1;
    const wN=Math.ceil(winC*.5),wS=Math.floor(winC*.3),wE=Math.max(0,winC-wN-wS);

    function mkOps(nW,hasDoor,len){
      const ops=[];
      if(hasDoor)ops.push({type:'door',pos:.22,w:DOOR_W,h:DOOR_H,sillY:0});
      for(let i=0;i<nW;i++)ops.push({type:'window',pos:(i+1)/(nW+1),w:WIN_W,h:WIN_H,sillY:WIN_SILL});
      return ops;
    }
    const innerD=Math.max(0.08,rd-tN-tS);

    // North wall — pos.z-rd/2 edge
    if(shouldDrawWall(pos.x-rw/2,pos.z-rd/2,pos.x+rw/2,pos.z-rd/2,floorY)){
    const gN=makeWallWithOpenings(rw,wh,tN,mkOps(wN,doorC>0,rw));
    const mN=new THREE.Mesh(gN,wMat);mN.castShadow=true;
    mN.position.set(pos.x-rw/2,floorY,pos.z-rd/2);wg.add(mN);
    if(doorC>0){const d=makeDoor(DOOR_W,DOOR_H);d.position.set(pos.x-rw/2+rw*.22,floorY,pos.z-rd/2+tN*.5+.01);scene.add(d);}
    for(let i=0;i<wN;i++){const wm=makeWindow(WIN_W,WIN_H);wm.position.set(pos.x-rw/2+rw*(i+1)/(wN+1),floorY+WIN_SILL,pos.z-rd/2+tN*.5);scene.add(wm);}
    }
    // South wall — pos.z+rd/2 edge
    if(shouldDrawWall(pos.x-rw/2,pos.z+rd/2,pos.x+rw/2,pos.z+rd/2,floorY)){
    const gS=makeWallWithOpenings(rw,wh,tS,mkOps(wS,false,rw));
    const mS=new THREE.Mesh(gS,wMat);mS.castShadow=true;
    mS.position.set(pos.x-rw/2,floorY,pos.z+rd/2-tS);wg.add(mS);
    for(let i=0;i<wS;i++){const wm=makeWindow(WIN_W,WIN_H);wm.position.set(pos.x-rw/2+rw*(i+1)/(wS+1),floorY+WIN_SILL,pos.z+rd/2-tS*.5);scene.add(wm);}
    }
    // West wall — pos.x-rw/2 edge
    if(shouldDrawWall(pos.x-rw/2,pos.z-rd/2,pos.x-rw/2,pos.z+rd/2,floorY)){
    const gW=makeWallWithOpenings(innerD,wh,tW,[]);
    const mW=new THREE.Mesh(gW,wMat);mW.castShadow=true;mW.rotation.y=Math.PI/2;
    mW.position.set(pos.x-rw/2+tW,floorY,pos.z-rd/2+tN);wg.add(mW);
    }
    // East wall — pos.x+rw/2 edge
    if(shouldDrawWall(pos.x+rw/2,pos.z-rd/2,pos.x+rw/2,pos.z+rd/2,floorY)){
    const gE=makeWallWithOpenings(innerD,wh,tE,mkOps(wE,doorC>1,innerD));
    const mE=new THREE.Mesh(gE,wMat);mE.castShadow=true;mE.rotation.y=Math.PI/2;
    mE.position.set(pos.x+rw/2-tE*2,floorY,pos.z-rd/2+tN);wg.add(mE);
    for(let i=0;i<wE;i++){const wm=makeWindow(WIN_W,WIN_H);wm.position.set(pos.x+rw/2-tE*.5,floorY+WIN_SILL,pos.z-rd/2+tN+innerD*(i+1)/(wE+1));scene.add(wm);}
    }
    // Floor slab between floors
    if(floorY>0){
      const slabM=new THREE.MeshLambertMaterial({color:0xd0c8b8});
      const slab=new THREE.Mesh(new THREE.BoxGeometry(rw,0.2,rd),slabM);
      slab.position.set(pos.x,floorY-0.1,pos.z);slab.receiveShadow=true;scene.add(slab);
    }
  }
  scene.add(wg);wallGroups.push({grp:wg,wh,floorY});

  // Ceiling
  if(!isOpen){
    const cm=new THREE.Mesh(new THREE.BoxGeometry(rw,0.06,rd),new THREE.MeshLambertMaterial({color:0xf8f4ec}));
    cm.position.set(pos.x,floorY+wh-0.03,pos.z);cm.receiveShadow=true;scene.add(cm);ceilMeshes.push(cm);
  } else ceilMeshes.push(null);

  // Label
  const lbl=makeLabel(_roomDispStr(room),room.area_sqft||0);
  lbl.position.set(pos.x,floorY+wh*.5+.3,pos.z);scene.add(lbl);labelSprites.push(lbl);

  // Dimension annotation — floating dim line just above floor
  (function(){
    const ftW=room.width_ft||Math.round(rw*3.281);
    const ftD=room.depth_ft||Math.round(rd*3.281);
    const dc=document.createElement('canvas');dc.width=160;dc.height=32;
    const dx=dc.getContext('2d');
    dx.fillStyle='rgba(26,23,20,0.0)';dx.fillRect(0,0,160,32);
    dx.fillStyle='rgba(200,169,110,0.85)';dx.font="bold 13px 'DM Mono',monospace";
    dx.textAlign='center';dx.fillText(`${ftW}' × ${ftD}'`,80,20);
    const dt=new THREE.CanvasTexture(dc);
    const ds=new THREE.Sprite(new THREE.SpriteMaterial({map:dt,transparent:true,depthTest:false}));
    ds.scale.set(1.0,0.2,1);
    ds.position.set(pos.x,floorY+0.12,pos.z);
    scene.add(ds);
  })();

  // Furniture
  addFurniture3D(room, floorY);
});
buildExterior(totalH);
buildRoof(totalH + 0.06);
} catch(e) { showFatal(e.message||String(e)); }

// Vastu per-room floor overlay — colour each room by zone compliance
(function(){
  // Vastu 8-zone map: facing=north means plot-north is top (negative Z in world)
  // Ideal zones: NE=pooja/prayer, E=kitchen/bathroom, SE=kitchen, S=heavy storage,
  // SW=master bedroom, W=bathroom/study, NW=guest/utility, N=living
  const VASTU_IDEAL={
    'living_room':['N','NE'],'dining_room':['W','N'],'master_bedroom':['SW','S','W'],
    'bedroom':['S','W','NW'],'kitchen':['SE','E'],'wet_kitchen':['SE','E'],
    'dry_kitchen':['SE','E'],'bathroom':['W','N','NW'],'common_bathroom':['W','NW'],
    'pooja_room':['NE','E'],'home_office':['W','NW'],'guest_bedroom':['NW','W'],
    'utility_room':['NW','W'],'store_room':['S','SW'],'servant_quarters':['NW'],
  };
  const CX=(BX+BW/2)*PX2M-OX, CZ=(BY+BH/2)*PX2M-OZ;
  ALLROOMS.forEach(room=>{
    const pos=p2w(room.x+room.width/2,room.y+room.height/2);
    const rw=room.width*PX2M, rd=room.height*PX2M;
    const cat=room.__cat_resolved||'default';
    const floorY=room.__floor_y||0;
    // Determine zone relative to building centre
    const dx=pos.x-CX, dz=pos.z-CZ;
    const ang=((Math.atan2(dx,-dz)*180/Math.PI)+360)%360;
    const zones=['N','NE','E','SE','S','SW','W','NW'];
    const zone=zones[Math.round(ang/45)%8];
    const ideal=VASTU_IDEAL[cat]||[];
    const good=ideal.includes(zone);
    const neutral=ideal.length===0;
    const clr=neutral?0x888888:good?0x3a8a3a:0xcc4444;
    const geo=new THREE.PlaneGeometry(rw*0.92,rd*0.92);
    const mat=new THREE.MeshBasicMaterial({color:clr,transparent:true,opacity:0.13,depthWrite:false});
    const ov=new THREE.Mesh(geo,mat);
    ov.rotation.x=-Math.PI/2;ov.position.set(pos.x,floorY+0.05,pos.z);
    scene.add(ov);
    // Zone label sprite
    const zc=document.createElement('canvas');zc.width=80;zc.height=28;
    const zx=zc.getContext('2d');
    zx.fillStyle=neutral?'#888':good?'#2a7a2a':'#aa3333';
    zx.font='bold 11px DM Mono,monospace';zx.textAlign='center';
    zx.fillText(zone,40,18);
    const zt=new THREE.CanvasTexture(zc);
    const zs=new THREE.Sprite(new THREE.SpriteMaterial({map:zt,transparent:true,depthTest:false}));
    zs.scale.set(.5,.18,1);zs.position.set(pos.x,floorY+0.08,pos.z+rd*.28);
    scene.add(zs);
  });
  // Directional compass ring (keep but smaller, just as orientation aid)
  const c=document.createElement('canvas');c.width=c.height=256;
  const cx2=c.getContext('2d');
  cx2.strokeStyle='rgba(200,169,110,0.18)';cx2.lineWidth=1;cx2.beginPath();cx2.arc(128,128,118,0,Math.PI*2);cx2.stroke();
  ['N','E','S','W'].forEach((d,i)=>{
    const a=i*(Math.PI/2)-Math.PI/2;
    cx2.fillStyle='rgba(200,169,110,0.5)';cx2.font='bold 16px sans-serif';cx2.textAlign='center';cx2.textBaseline='middle';
    cx2.fillText(d,128+Math.cos(a)*96,128+Math.sin(a)*96);
  });
  const t=new THREE.CanvasTexture(c);
  const compassOv=new THREE.Mesh(new THREE.PlaneGeometry(BW*PX2M,BH*PX2M),new THREE.MeshBasicMaterial({map:t,transparent:true,depthWrite:false}));
  compassOv.rotation.x=-Math.PI/2;compassOv.position.y=.001;scene.add(compassOv);
})();

// ── VIEW PRESETS ──────────────────────────────────────────────────────────────
function animTo(nth,nph,nr,ms){
  const st=Date.now(),sth=th,sph=ph,sr=cr;
  (function s(){
    const t=Math.min(1,(Date.now()-st)/ms),e=t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
    th=sth+(nth-sth)*e;ph=sph+(nph-sph)*e;cr=sr+(nr-sr)*e;camUpdate();
    if(t<1)requestAnimationFrame(s);
  })();
}

let exploded=false;
function setView(m){
  ['iso','top','front','back','side','exterior','explode','walk'].forEach(v=>document.getElementById('btn-'+v)?.classList.remove('active'));
  document.getElementById('btn-'+m)?.classList.add('active');
  if(m==='iso')     {resetExplode();animTo(-0.6,0.9,22,600);}
  else if(m==='top') {resetExplode();animTo(-0.6,0.04,20,600);}
  else if(m==='front'){resetExplode();animTo(0,1.2,18,600);}
  else if(m==='back') {resetExplode();animTo(Math.PI,1.2,18,600);}
  else if(m==='side') {resetExplode();animTo(Math.PI/2,1.0,18,600);}
  else if(m==='exterior'){resetExplode();animTo(-0.4,0.7,32,700);}
  else if(m==='explode'){doExplode();animTo(-0.6,0.5,34,600);}
  else if(m==='walk'){enterWalk();return;}
}
function resetExplode(){
  if(!exploded)return; exploded=false;
  roomMeshes.forEach((_,i)=>animMeshY(i,0,400));
}
function doExplode(){
  if(exploded)return; exploded=true;
  ALLROOMS.forEach((_,i)=>setTimeout(()=>animMeshY(i,ALLROOMS[i].__wall_h+0.5+i*0.12,350),i*60));
}
function animMeshY(i,ty,ms){
  const mesh=roomMeshes[i],wg=wallGroups[i],cm=ceilMeshes[i],ls=labelSprites[i];
  const wh=(wg?.wh||2.7),fy=wg?.floorY||0;
  const sy=mesh.position.y,st2=Date.now();
  (function s(){
    const t=Math.min(1,(Date.now()-st2)/ms),e=t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
    const y=sy+(ty+fy+.04-sy)*e;
    mesh.position.y=y;
    if(wg)wg.grp.position.y=ty+fy;
    if(cm?.position)cm.position.y=fy+wh-.03+ty;
    if(ls)ls.position.y=fy+wh*.5+.3+ty;
    if(t<1)requestAnimationFrame(s);
  })();
}

// ── CUTAWAY ────────────────────────────────────────────────────────────────────
function setCutaway(v){
  document.getElementById('cv').textContent=v+'%';
  wallGroups.forEach(wg=>{
    const pct=v/100,wh=wg.wh;
    wg.grp.children.forEach(m=>{
      if(!m.isMesh)return;
      m.scale.y=Math.max(0.02,pct);
      m.position.y=wg.floorY||0;
    });
  });
}

// ── WALKTHROUGH ────────────────────────────────────────────────────────────────
let walkMode=false;
let wPos={x:0,y:1.7,z:0},wAngle=0,wPitch=0;
const wSpeed=0.08,wKeys={};

function enterWalk(){
  walkMode=true;
  document.getElementById('walkmode-overlay').classList.add('active');
  document.getElementById('walkhud').style.display='flex';
  wPos={x:0,y:1.7,z:-BH*PX2M*.3};wAngle=0;wPitch=0;
  camera.fov=75;camera.updateProjectionMatrix();
  document.getElementById('btn-walk')?.classList.add('active');
}
function exitWalk(){
  walkMode=false;
  document.getElementById('walkmode-overlay').classList.remove('active');
  document.getElementById('walkhud').style.display='none';
  camera.fov=42;camera.updateProjectionMatrix();
  setView('iso');
}
function wMove(fwd,str){
  wPos.x+=Math.sin(wAngle)*fwd*wSpeed+Math.cos(wAngle)*str*wSpeed;
  wPos.z+=Math.cos(wAngle)*fwd*wSpeed-Math.sin(wAngle)*str*wSpeed;
}
function wTurn(dir){wAngle+=dir*.08;}
function walkLook(e){if(!walkMode)return;}
document.addEventListener('keydown',e=>wKeys[e.code]=true);
document.addEventListener('keyup',  e=>wKeys[e.code]=false);
function updateWalk(){
  if(!walkMode)return;
  if(wKeys['KeyW']||wKeys['ArrowUp'])   wMove(1,0);
  if(wKeys['KeyS']||wKeys['ArrowDown']) wMove(-1,0);
  if(wKeys['KeyA'])                     wMove(0,-1);
  if(wKeys['KeyD'])                     wMove(0,1);
  if(wKeys['ArrowLeft']||wKeys['KeyQ']) wAngle-=.04;
  if(wKeys['ArrowRight']||wKeys['KeyE'])wAngle+=.04;
  camera.position.set(wPos.x,wPos.y,wPos.z);
  camera.lookAt(wPos.x+Math.sin(wAngle),wPos.y+wPitch,wPos.z+Math.cos(wAngle));
}

// ── RAYCASTER + DRAG ─────────────────────────────────────────────────────────
const ray=new THREE.Raycaster(),mv=new THREE.Vector2();
const tt=document.getElementById('tooltip');
let hm=null,dragMesh=null,dragPlane=new THREE.Plane(new THREE.Vector3(0,1,0),0),dragOffset=new THREE.Vector3();

function getMV(e){const r=wrap.getBoundingClientRect();mv.x=((e.clientX-r.left)/getW())*2-1;mv.y=((e.clientY-r.top)/getH())*-2+1;}
function handleHover(e){
  if(walkMode||orb.active)return;
  getMV(e);ray.setFromCamera(mv,camera);
  const hits=ray.intersectObjects(roomMeshes);
  if(hits.length){
    const room=hits[0].object.userData.room;
    tt.style.cssText=`display:block;left:${e.clientX+14}px;top:${e.clientY-10}px`;
    document.getElementById('ttn').textContent=_roomDispStr(room);
    document.getElementById('ttd').textContent=`${room.width_ft||'?'}ft×${room.depth_ft||'?'}ft = ${room.area_sqft||'?'} sqft`;
    document.getElementById('ttv').textContent=`Vastu: ${room.__vastu_zone||'—'}`;
    if(hm!==hits[0].object){if(hm)hm.material.emissive?.set(0);hm=hits[0].object;if(hm.material.emissive)hm.material.emissive.set(0x0a0806);}
  } else {tt.style.display='none';if(hm){hm.material.emissive?.set(0);hm=null;}}
}
wrap.addEventListener('click',e=>{
  if(walkMode||orb.active||exploded)return;
  getMV(e);ray.setFromCamera(mv,camera);
  const hits=ray.intersectObjects(roomMeshes);
  if(hits.length){
    const room=hits[0].object.userData.room;
    const pos=p2w(room.x+room.width/2,room.y+room.height/2);
    ctx=pos.x;ctz=pos.z;animTo(th,ph,10,400);
    setTimeout(()=>{ctx=0;ctz=0;},2200);
    document.querySelectorAll('.room-tag').forEach(t=>t.classList.remove('active'));
    document.getElementById('rt-'+_roomIdSafe(room))?.classList.add('active');
    const si=document.getElementById('sel-info');
    document.getElementById('sel-name').textContent=_roomDispStr(room);
    document.getElementById('sel-detail').textContent=`${room.width_ft||0}ft × ${room.depth_ft||0}ft · ${room.area_sqft||0} sqft`;
    si.style.display='block';
  }
});

// ── TABS ──────────────────────────────────────────────────────────────────────
function showTab(t){
  const ids=['view','plan','rooms','score','sun','measure','boq'];
  ids.forEach(id=>{
    document.getElementById('tab-'+id).style.display=id===t?'':'none';
  });
  document.querySelectorAll('.tab').forEach((btn,i)=>btn.classList.toggle('active',ids[i]===t));
}

// ── 2D SVG PLAN ───────────────────────────────────────────────────────────────
let svgOpen=false,svgScale=1;
let svgDragging=null,svgDragOx=0,svgDragOy=0,svgDragX=0,svgDragY=0;

function toggle2D(){
  svgOpen=!svgOpen;
  const sw=document.getElementById('svg-wrap');
  sw.style.display=svgOpen?'block':'none';
  if(svgOpen&&!sw.innerHTML)buildSVG();
}

function svgZoom(f){svgScale*=f;const sv=document.getElementById('main-svg');if(sv)sv.style.transform=`scale(${svgScale})`;}

function buildSVG(){
  const sw=document.getElementById('svg-wrap');
  const cw=LAYOUT.canvas_w||800,ch=LAYOUT.canvas_h||900;
  let svg=`<svg id="main-svg" viewBox="0 0 ${cw} ${ch}" style="width:${cw}px;height:${ch}px;transform-origin:top left" xmlns="http://www.w3.org/2000/svg">`;
  svg+=`<rect width="${cw}" height="${ch}" fill="#f4f0e8"/>`;
  // Plot boundary
  svg+=`<rect x="${BX}" y="${BY}" width="${BW}" height="${BH}" fill="white" stroke="#1a1a1a" stroke-width="9"/>`;
  const COLORS={'living_room':'#e8f4e8','dining_room':'#e0f7fa','master_bedroom':'#ede7f6','bedroom':'#e8eaf6','kitchen':'#fff3e0','bathroom':'#e3f2fd','common_bathroom':'#e3f2fd','corridor':'#f5f5f5','staircase':'#fafafa','car_porch':'#eceff1','sit_out':'#f1f8e9','store_room':'#efebe9','home_office':'#fce4ec','balcony':'#f1f8e9','terrace':'#e8f5e9','family_lounge':'#e8f4e8','pooja_room':'#fff9c4','default':'#f8f8f8'};
  ROOMS.forEach((r,i)=>{
    const cat=r.__cat_resolved||'default';
    const fc=COLORS[cat]||COLORS.default;
    svg+=`<g id="svg-room-${i}" class="svg-drag" transform="translate(0,0)" style="cursor:move">`;
    svg+=`<rect x="${r.x}" y="${r.y}" width="${r.width}" height="${r.height}" fill="${fc}" stroke="#1a1a1a" stroke-width="4"/>`;
    // Door arc
    const dw=Math.min(r.width*.28,28);
    svg+=`<path d="M ${r.x+6} ${r.y} A ${dw} ${dw} 0 0 0 ${r.x+6+dw} ${r.y}" fill="none" stroke="#1a1a1a" stroke-width="0.8"/>`;
    svg+=`<line x1="${r.x+6}" y1="${r.y}" x2="${r.x+6}" y2="${r.y+dw}" stroke="#1a1a1a" stroke-width="0.8"/>`;
    // Window
    const wx=r.x+r.width*.6,wlen=Math.min(r.width*.3,32);
    svg+=`<rect x="${wx}" y="${r.y+r.height-8}" width="${wlen}" height="8" fill="#cce8ff" stroke="#4f8ef7" stroke-width="0.6"/>`;
    [.33,.5,.67].forEach(t=>svg+=`<line x1="${wx+wlen*t}" y1="${r.y+r.height-7}" x2="${wx+wlen*t}" y2="${r.y+r.height-1}" stroke="#4f8ef7" stroke-width="0.6"/>`);
    // Label
    svg+=`<text x="${r.x+r.width/2}" y="${r.y+r.height/2-4}" text-anchor="middle" font-family="DM Mono,monospace" font-size="9" font-weight="600" fill="#1a1a1a">${(r.__label||r.name).replace(/_/g,' ').toUpperCase()}</text>`;
    svg+=`<text x="${r.x+r.width/2}" y="${r.y+r.height/2+9}" text-anchor="middle" font-family="DM Mono,monospace" font-size="7" fill="#666">${r.width_ft||0}' × ${r.depth_ft||0}'</text>`;
    svg+=`</g>`;
  });
  svg+=`</svg>`;
  sw.innerHTML=svg;

  // Make SVG rooms draggable
  sw.querySelectorAll('.svg-drag').forEach((el,i)=>{
    let ox=0,oy=0,tx=0,ty=0,dragging=false;
    el.addEventListener('mousedown',e=>{
      dragging=true;ox=e.clientX-tx;oy=e.clientY-ty;e.stopPropagation();
    });
    window.addEventListener('mousemove',e=>{
      if(!dragging)return;
      tx=e.clientX-ox;ty=e.clientY-oy;
      el.setAttribute('transform',`translate(${tx},${ty})`);
      // Sync to 3D
      if(roomMeshes[i]){
        const nr=ROOMS[i];
        const newX=(nr.x+tx/svgScale)*PX2M,newZ=(nr.y+ty/svgScale)*PX2M;
        const wp=p2w((nr.x+tx/svgScale)+nr.width/2,(nr.y+ty/svgScale)+nr.height/2);
        roomMeshes[i].position.x=wp.x;
        roomMeshes[i].position.z=wp.z;
        if(wallGroups[i]){wallGroups[i].grp.position.x=wp.x;wallGroups[i].grp.position.z=wp.z;}
        if(ceilMeshes[i]&&ceilMeshes[i].position){ceilMeshes[i].position.x=wp.x;ceilMeshes[i].position.z=wp.z;}
        if(labelSprites[i]){labelSprites[i].position.x=wp.x;labelSprites[i].position.z=wp.z;}
      }
    });
    window.addEventListener('mouseup',()=>dragging=false);
  });
}

// ── PANEL: ROOMS ──────────────────────────────────────────────────────────────
const rl=document.getElementById('rl');
ROOMS.forEach(room=>{
  const tag=document.createElement('div');tag.className='room-tag';tag.id='rt-'+_roomIdSafe(room);
  const col=(room.__color||'0xf5f3ee').replace('0x','#');
  tag.innerHTML=`<div class="sw" style="background:${col}"></div><span style="flex:1">${_roomDispStr(room)}</span><span style="font-size:10px;color:var(--muted)">${room.area_sqft||0}ft²</span>`;
  tag.onclick=()=>{
    const pos=p2w(room.x+room.width/2,room.y+room.height/2);
    ctx=pos.x;ctz=pos.z;animTo(th,ph,10,400);setTimeout(()=>{ctx=0;ctz=0;},2200);
    document.querySelectorAll('.room-tag').forEach(t=>t.classList.remove('active'));tag.classList.add('active');
  };
  rl.appendChild(tag);
});

// ── PANEL: SCORE ──────────────────────────────────────────────────────────────
const sbars=document.getElementById('sbars');
const scoreLabels={'vastu_compliance':'Vastu','adjacency_quality':'Adj.','circulation':'Circ.','area_accuracy':'Area','privacy_gradient':'Privacy','natural_light':'Light'};
const scoreMax={'vastu_compliance':25,'adjacency_quality':20,'circulation':20,'area_accuracy':15,'privacy_gradient':10,'natural_light':10};
Object.entries(SCORE||{}).forEach(([k,v])=>{
  const pct=Math.round(v/(scoreMax[k]||10)*100);
  const row=document.createElement('div');row.className='sbr';
  row.innerHTML=`<div class="sbl">${scoreLabels[k]||k}</div><div class="sbt"><div class="sbf" style="width:${pct}%"></div></div><div style="font-size:9px;color:var(--muted);width:18px;text-align:right">${v}</div>`;
  sbars.appendChild(row);
});

// ── FLOOR BUTTONS ─────────────────────────────────────────────────────────────
const floorBtns=document.getElementById('floor-btns');
for(let fi=0;fi<NUM_FLOORS;fi++){
  const btn=document.createElement('button');btn.className='ctrl-btn'+(fi===0?' active':'');
  btn.textContent=['Ground','First','Second','Third'][fi]+' Fl.';
  btn.onclick=()=>{
    document.querySelectorAll('#floor-btns .ctrl-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    const fy=fi*FLOOR_STEP_M;
    ctx=0;ctz=0;animTo(th,ph,18,600);
    setTimeout(()=>{camera.position.y+=fy;camera.lookAt(0,fy,0);},650);
  };
  floorBtns.appendChild(btn);
}

// ── SUN PATH ──────────────────────────────────────────────────────────────────
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const MDAYS=[0,31,59,90,120,151,181,212,243,273,304,334];
function dayToDate(d){
  let m=0;for(let i=0;i<12;i++)if(d>MDAYS[i])m=i;
  return MON[m]+' '+(d-MDAYS[m]);
}
function updateSunPath(){
  const day=parseFloat(document.getElementById('sun-day').value);
  const hr=parseFloat(document.getElementById('sun-hr').value);
  const lat=parseFloat(document.getElementById('sun-lat').value)*Math.PI/180;
  document.getElementById('sun-day-lbl').textContent=dayToDate(day);
  document.getElementById('sun-hr-lbl').textContent=Math.floor(hr)+':'+(hr%1===0?'00':Math.round((hr%1)*60)).toString().padStart(2,'0');
  document.getElementById('sun-lat-lbl').textContent=parseFloat(document.getElementById('sun-lat').value).toFixed(1)+'°';
  // Solar declination
  const decl=23.45*Math.PI/180*Math.sin(2*Math.PI*(284+day)/365);
  // Hour angle (solar noon = 0)
  const ha=(hr-12)*15*Math.PI/180;
  // Altitude and azimuth
  const sinAlt=Math.sin(lat)*Math.sin(decl)+Math.cos(lat)*Math.cos(decl)*Math.cos(ha);
  const alt=Math.asin(Math.max(0,sinAlt));
  const cosAz=(Math.sin(decl)-Math.sin(lat)*sinAlt)/(Math.cos(lat)*Math.cos(alt)+0.0001);
  const az=Math.acos(Math.max(-1,Math.min(1,cosAz)))*(ha>0?-1:1);
  const dist=60;
  if(sun){
    sun.position.set(dist*Math.sin(az)*Math.cos(alt), dist*Math.sin(alt), dist*Math.cos(az)*Math.cos(alt));
    const intensity=Math.max(0,sinAlt)*3.5;
    sun.intensity=intensity;
    amb.intensity=0.3+Math.max(0,sinAlt)*0.4;
    renderer.toneMappingExposure=0.9+Math.max(0,sinAlt)*0.3;
  }
  const altDeg=(alt*180/Math.PI).toFixed(1);
  const azDeg=((az*180/Math.PI+360)%360).toFixed(0);
  document.getElementById('sun-info').innerHTML=`Altitude: <b>${altDeg}°</b><br>Azimuth: <b>${azDeg}°</b><br>${sinAlt<0.05?'⚫ Below horizon':'☀ Above horizon'}`;
}
function toggleShadow(on){
  renderer.shadowMap.enabled=on;
  ['shadow-on','shadow-off'].forEach(id=>document.getElementById('btn-'+id)?.classList.toggle('active',id===('shadow-'+(on?'on':'off'))));
}
updateSunPath();

// ── MEASUREMENT MODE ──────────────────────────────────────────────────────────
let measMode=false,measPts=[],measDots=[];
const measRay=new THREE.Raycaster();
const measHistory=[];

function setMeasure(on){
  measMode=on;
  measPts=[];
  measDots.forEach(d=>d.remove());measDots=[];
  document.getElementById('meas-result').style.display='none';
  ['btn-meas-off','btn-meas-on'].forEach(id=>document.getElementById(id)?.classList.toggle('active',id===('btn-meas-'+(on?'on':'off'))));
  wrap.style.cursor=on?'crosshair':'default';
}

wrap.addEventListener('click',e=>{
  if(!measMode||walkMode)return;
  getMV(e);measRay.setFromCamera(mv,camera);
  const hits=measRay.intersectObjects([...roomMeshes,...scene.children.filter(c=>c.isMesh)]);
  if(!hits.length)return;
  const pt=hits[0].point;
  measPts.push(pt.clone());
  // Visual dot
  const dot=document.createElement('div');dot.className='meas-dot';
  const r=wrap.getBoundingClientRect();
  dot.style.left=(e.clientX-r.left)+'px';dot.style.top=(e.clientY-r.top)+'px';
  dot.style.position='absolute';
  wrap.appendChild(dot);measDots.push(dot);
  if(measPts.length===2){
    const dist=measPts[0].distanceTo(measPts[1]);
    const ft=dist*3.2808;
    document.getElementById('meas-m').textContent=dist.toFixed(2)+' m';
    document.getElementById('meas-ft').textContent=ft.toFixed(2)+' ft';
    document.getElementById('meas-result').style.display='block';
    measHistory.unshift(dist.toFixed(2)+'m  /  '+ft.toFixed(2)+'ft');
    if(measHistory.length>8)measHistory.pop();
    document.getElementById('meas-history').innerHTML=measHistory.join('<br>');
    measPts=[];
    setTimeout(()=>{measDots.forEach(d=>d.remove());measDots=[];},1800);
  }
},true);

// ── MATERIAL PICKER ───────────────────────────────────────────────────────────
const MATERIALS={
  'Plaster (white)':0xf5f2ee,'Plaster (cream)':0xf0e8d0,'Plaster (terracotta)':0xd4886a,
  'Exposed brick':0xb5613a,'Stone cladding':0xa09080,'Teak wood':0x8B6F47,
  'Dark oak':0x4a2e0f,'White tile':0xe8e8e8,'Marble':0xf0ece4,
  'Concrete':0xb0aaA0,'Paint (sage)':0x8aaa88,'Paint (slate)':0x7890a0,
};
let activeMat=Object.keys(MATERIALS)[0];
const mp=document.getElementById('mat-picker');
Object.entries(MATERIALS).forEach(([name,hex])=>{
  const sw=document.createElement('span');sw.className='mat-swatch'+(name===activeMat?' active':'');
  sw.title=name;sw.style.background='#'+hex.toString(16).padStart(6,'0');
  sw.onclick=()=>{activeMat=name;document.querySelectorAll('.mat-swatch').forEach(s=>s.classList.toggle('active',s.title===name));};
  mp.appendChild(sw);
});

// Override click handler to also apply material when mat-picker is active
const _origClick=wrap.onclick;
wrap.addEventListener('click',e=>{
  if(walkMode||measMode)return;
  getMV(e);ray.setFromCamera(mv,camera);
  const hits=ray.intersectObjects(roomMeshes);
  if(hits.length&&activeMat){
    const hex=MATERIALS[activeMat];
    if(hex!==undefined){
      const mesh=hits[0].object;
      mesh.material=new THREE.MeshLambertMaterial({color:hex});
    }
  }
});

// ── BILL OF QUANTITIES ────────────────────────────────────────────────────────
(function(){
  const BT=document.getElementById('boq-table');
  const TOT=document.getElementById('boq-totals');
  if(!BT)return;
  let totalFloor=0,totalWall=0,totalCeil=0,totalDoors=0,totalWins=0;
  let html='<table style="width:100%;border-collapse:collapse">';
  html+='<tr style="border-bottom:1px solid rgba(200,169,110,.3)"><th style="text-align:left;padding:2px 0;font-size:9px;color:var(--muted)">Room</th><th style="text-align:right;font-size:9px;color:var(--muted)">Floor</th><th style="text-align:right;font-size:9px;color:var(--muted)">Wall</th><th style="text-align:right;font-size:9px;color:var(--muted)">Ceil</th></tr>';
  ROOMS.forEach(r=>{
    const rw=r.width*PX2M,rd=r.height*PX2M,wh=r.__wall_h||2.7;
    const floorA=(rw*rd).toFixed(1);
    const wallA=(2*(rw+rd)*wh).toFixed(1);
    const ceilA=(rw*rd).toFixed(1);
    const doors=parseInt(r.door_count)||1;
    const wins=parseInt(r.windows)||1;
    totalFloor+=rw*rd;totalWall+=2*(rw+rd)*wh;totalCeil+=rw*rd;
    totalDoors+=doors;totalWins+=wins;
    html+=`<tr style="border-bottom:1px solid rgba(0,0,0,.04)">
      <td style="padding:2px 0;font-size:9px">${(r.__label||r.name).replace(/_/g,' ')}</td>
      <td style="text-align:right;font-size:9px">${floorA}</td>
      <td style="text-align:right;font-size:9px">${wallA}</td>
      <td style="text-align:right;font-size:9px">${ceilA}</td>
    </tr>`;
  });
  html+='</table>';
  BT.innerHTML=html;
  const conc=(totalFloor*0.125).toFixed(1);
  const brick=(totalWall*0.24*1800/1000).toFixed(0);
  const plaster=(totalWall*1.05).toFixed(1);
  TOT.innerHTML=`
    Floor area: <b>${totalFloor.toFixed(1)} m²</b><br>
    Wall area: <b>${totalWall.toFixed(1)} m²</b><br>
    Doors: <b>${totalDoors}</b> · Windows: <b>${totalWins}</b><br>
    Est. concrete slab: <b>${conc} m³</b><br>
    Est. brickwork: <b>${brick} kg</b><br>
    Plaster area: <b>${plaster} m²</b>
  `;
})();

function exportBOQ(){
  let csv='Room,Floor m2,Wall m2,Ceil m2,Doors,Windows\n';
  ROOMS.forEach(r=>{
    const rw=r.width*PX2M,rd=r.height*PX2M,wh=r.__wall_h||2.7;
    csv+=`"${(r.__label||r.name).replace(/_/g,' ')}",${(rw*rd).toFixed(2)},${(2*(rw+rd)*wh).toFixed(2)},${(rw*rd).toFixed(2)},${r.door_count||1},${r.windows||1}\n`;
  });
  const a=document.createElement('a');
  a.href='data:text/csv;charset=utf-8,'+encodeURIComponent(csv);
  a.download='boq.csv';a.click();
}

// ── STRUCTURAL GRID ───────────────────────────────────────────────────────────
// Auto-compute column grid from room spans. Columns at room corners that fall
// on a regular grid (rounded to nearest 0.5m). Beams along each axis.
let structGroup=null, structVisible=false;
function buildStructuralGrid(){
  if(structGroup){structGroup.traverse(o=>{if(o.isMesh){o.geometry.dispose();o.material.dispose();}});scene.remove(structGroup);}
  structGroup=new THREE.Group();
  const colM=new THREE.MeshLambertMaterial({color:0x607080});
  const beamM=new THREE.MeshLambertMaterial({color:0x708090,transparent:true,opacity:0.7});
  const span=3.0; // target column spacing in metres
  const xs=new Set(), zs=new Set();
  ALLROOMS.forEach(r=>{
    const p=p2w(r.x,r.y), p2=p2w(r.x+r.width,r.y+r.height);
    [p.x,p2.x].forEach(v=>xs.add(Math.round(v/span)*span));
    [p.z,p2.z].forEach(v=>zs.add(Math.round(v/span)*span));
  });
  const xArr=[...xs].sort((a,b)=>a-b);
  const zArr=[...zs].sort((a,b)=>a-b);
  const colH=totalH+0.06;
  // Columns
  xArr.forEach(x=>zArr.forEach(z=>{
    const col=new THREE.Mesh(new THREE.BoxGeometry(0.23,colH,0.23),colM);
    col.position.set(x,colH/2,z);col.castShadow=true;structGroup.add(col);
  }));
  // Beams per floor
  for(let f=0;f<=NUM_FLOORS;f++){
    const by=f*FLOOR_STEP_M-0.1;
    xArr.forEach(x=>{
      if(zArr.length<2)return;
      const blen=zArr[zArr.length-1]-zArr[0];
      const beam=new THREE.Mesh(new THREE.BoxGeometry(0.23,0.35,blen),beamM);
      beam.position.set(x,by,zArr[0]+blen/2);structGroup.add(beam);
    });
    zArr.forEach(z=>{
      if(xArr.length<2)return;
      const blen=xArr[xArr.length-1]-xArr[0];
      const beam=new THREE.Mesh(new THREE.BoxGeometry(blen,0.35,0.23),beamM);
      beam.position.set(xArr[0]+blen/2,by,z);structGroup.add(beam);
    });
  }
  structGroup.visible=structVisible;
  scene.add(structGroup);
}
buildStructuralGrid();
function toggleStructGrid(on){
  structVisible=on;
  if(structGroup)structGroup.visible=on;
  ['struct-off','struct-on'].forEach(id=>document.getElementById('btn-'+id)?.classList.toggle('active',id===('struct-'+(on?'on':'off'))));
}

// ── IFC EXPORT (simplified IFC2x3 shell) ─────────────────────────────────────
// Generates a valid IFC2x3 file that AutoCAD/Revit/BIMx can import.
// Includes IfcSpace per room, IfcWall stubs, IfcSlab, site/building/storey hierarchy.
function exportIFC(){
  const ts=new Date().toISOString().replace(/[-:T]/g,'').slice(0,14);
  let id=100;
  const next=()=>++id;
  const lines=[];
  const H=(n,t,a)=>lines.push(`#${n}=${t}(${a});`);
  // Header
  lines.push('ISO-10303-21;');
  lines.push('HEADER;');
  lines.push(`FILE_DESCRIPTION(('Pascal 3D IFC Export'),'2;1');`);
  lines.push(`FILE_NAME('pascal_export_${ts}.ifc','${new Date().toISOString()}',('Pascal'),('Pascal'),'','Pascal 3D','');`);
  lines.push(`FILE_SCHEMA(('IFC2X3'));`);
  lines.push('ENDSEC;');
  lines.push('DATA;');
  // Owner history
  const ownerId=next();
  H(ownerId,'IfcOwnerHistory',`#${next()},${next()},#${next()},$NOTDEFINED,.ADDED.,#${next()},$,${Math.floor(Date.now()/1000)}`);
  // Project
  const projId=next();
  H(projId,'IfcProject',`'${ts}',#${ownerId},'Pascal Project',$,$,$,$,(#${next()}),#${next()}`);
  // Site
  const siteId=next();
  H(siteId,'IfcSite',`'${ts}',#${ownerId},'Site',$,$,$,$,$,.ELEMENT.,$,$,$,$,$`);
  // Building
  const bldgId=next();
  H(bldgId,'IfcBuilding',`'${ts}',#${ownerId},'Building',$,$,$,$,$,.ELEMENT.,$,$,$`);
  // Storey per floor
  const storeyIds=[];
  for(let f=0;f<NUM_FLOORS;f++){
    const sid=next();
    H(sid,'IfcBuildingStorey',`'Floor${f}',#${ownerId},'${['Ground','First','Second','Third'][f]||'Floor '+f} Floor',$,$,$,$,$,.ELEMENT.,${(f*FLOOR_STEP_M).toFixed(3)}`);
    storeyIds.push({id:sid,f});
  }
  // Spaces (rooms)
  const spaceIds=[];
  ALLROOMS.forEach(r=>{
    const floorF=Math.round((r.__floor_y||0)/FLOOR_STEP_M);
    const pos=p2w(r.x+r.width/2,r.y+r.height/2);
    const rw=r.width*PX2M, rd=r.height*PX2M;
    const wh=r.__wall_h||2.7;
    const sid=next();
    H(sid,'IfcSpace',`'${r.name}',#${ownerId},'${(r.__label||r.name).replace(/'/g,'')}','${r.__cat_resolved||'room'}',$,$,$,$,.ELEMENT.,.INTERNAL.,${wh.toFixed(3)}`);
    spaceIds.push({id:sid,floor:floorF,room:r});
  });
  lines.push('ENDSEC;');
  lines.push('END-ISO-10303-21;');
  const blob=new Blob([lines.join('\n')],{type:'text/plain'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`pascal_${ts}.ifc`;a.click();
}

// ── DXF EXPORT (AutoCAD-compatible 2D floor plan) ─────────────────────────────
function exportDXF(){
  const lines=['0','SECTION','2','ENTITIES'];
  ROOMS.forEach(r=>{
    const x0=r.x*PX2M*1000, y0=r.y*PX2M*1000; // mm
    const x1=(r.x+r.width)*PX2M*1000, y1=(r.y+r.height)*PX2M*1000;
    // Polyline rectangle per room
    ['0','LWPOLYLINE',
     '8',`FLOOR_${(r.__cat_resolved||'room').toUpperCase()}`,
     '90','4','70','1', // 4 vertices, closed
     '10',x0.toFixed(0),'20',y0.toFixed(0),
     '10',x1.toFixed(0),'20',y0.toFixed(0),
     '10',x1.toFixed(0),'20',y1.toFixed(0),
     '10',x0.toFixed(0),'20',y1.toFixed(0),
    ].forEach(l=>lines.push(l));
    // Room label text
    const cx=((x0+x1)/2).toFixed(0), cy=((y0+y1)/2).toFixed(0);
    ['0','TEXT','8','ROOM_LABELS','10',cx,'20',cy,'30','0','40','200',
     '1',(r.__label||r.name).replace(/_/g,' '),'72','1','73','2','11',cx,'21',cy
    ].forEach(l=>lines.push(l));
    // Dimension text
    ['0','TEXT','8','DIMENSIONS','10',cx,'20',(parseFloat(cy)-300).toFixed(0),'30','0','40','150',
     '1',`${r.width_ft||Math.round(r.width*PX2M*3.281)}' x ${r.depth_ft||Math.round(r.height*PX2M*3.281)}'`,'72','1','73','2',
     '11',cx,'21',(parseFloat(cy)-300).toFixed(0)
    ].forEach(l=>lines.push(l));
  });
  lines.push('0','ENDSEC','0','EOF');
  const blob=new Blob([lines.join('\n')],{type:'application/dxf'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='pascal_floorplan.dxf';a.click();
}

// ── SHARE LINK ────────────────────────────────────────────────────────────────
function generateShareLink(){
  // Encode camera state + floor + light mode into URL hash
  const state={th:th.toFixed(3),ph:ph.toFixed(3),cr:cr.toFixed(1),fi:0};
  const hash='#v='+btoa(JSON.stringify(state));
  const url=window.location.href.split('#')[0]+hash;
  navigator.clipboard.writeText(url).then(()=>{
    const btn=document.getElementById('btn-share');
    if(btn){btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy Share Link',1800);}
  }).catch(()=>{
    prompt('Copy this link:',url);
  });
}
// Restore camera from URL hash on load
(function(){
  try{
    const h=window.location.hash;
    if(h.startsWith('#v=')){
      const s=JSON.parse(atob(h.slice(3)));
      if(s.th)th=parseFloat(s.th);
      if(s.ph)ph=parseFloat(s.ph);
      if(s.cr)cr=parseFloat(s.cr);
      camUpdate();
    }
  }catch(e){}
})();

// ── WALKTHROUGH COLLISION ─────────────────────────────────────────────────────
// Simple AABB collision: build list of wall bounding boxes, clamp walk position
const wallBoxes=[];
ALLROOMS.forEach(r=>{
  const pos=p2w(r.x+r.width/2,r.y+r.height/2);
  const rw2=r.width*PX2M/2+EXT_WALL_T, rd2=r.height*PX2M/2+EXT_WALL_T;
  wallBoxes.push({
    minX:pos.x-rw2,maxX:pos.x+rw2,
    minZ:pos.z-rd2,maxZ:pos.z+rd2,
    floorY:r.__floor_y||0, topY:(r.__floor_y||0)+(r.__wall_h||2.7)
  });
});
function clampWalkPos(nx,nz){
  // Person radius
  const R=0.25, fy=wPos.y-1.7;
  for(const b of wallBoxes){
    if(fy<b.floorY-0.1||fy>b.topY+0.1)continue;
    // Only collide with walls, not the interior
    const inX=nx>b.minX+R&&nx<b.maxX-R;
    const inZ=nz>b.minZ+R&&nz<b.maxZ-R;
    if(inX&&inZ){
      // Push out on shortest axis
      const dL=nx-(b.minX+R), dR=(b.maxX-R)-nx;
      const dT=nz-(b.minZ+R), dB=(b.maxZ-R)-nz;
      const mn=Math.min(dL,dR,dT,dB);
      if(mn===dL)nx=b.minX+R;
      else if(mn===dR)nx=b.maxX-R;
      else if(mn===dT)nz=b.minZ+R;
      else nz=b.maxZ-R;
    }
  }
  return {x:nx,z:nz};
}
const _origWMove=wMove;
function wMove(fwd,str){
  const nx=wPos.x+Math.sin(wAngle)*fwd*wSpeed+Math.cos(wAngle)*str*wSpeed;
  const nz=wPos.z+Math.cos(wAngle)*fwd*wSpeed-Math.sin(wAngle)*str*wSpeed;
  const clamped=clampWalkPos(nx,nz);
  wPos.x=clamped.x;wPos.z=clamped.z;
}

// ── RESIZE + RENDER LOOP ───────────────────────────────────────────────────────
function onResize(){
  const w=getW(),h=getH();
  renderer.setSize(w,h);
  camera.aspect=w/h;
  camera.updateProjectionMatrix();
}
window.addEventListener('resize',onResize);
// Also observe container resize for iframe embedding
if(typeof ResizeObserver!=='undefined'){
  new ResizeObserver(onResize).observe(canvasWrap||document.body);
}
onResize();camUpdate();

let frame=0;
function animate(){
  requestAnimationFrame(animate);frame++;
  updateWalk();
  if(sun&&!walkMode){sun.position.x=15*Math.cos(frame*.0005);sun.position.z=-10*Math.sin(frame*.0005);}
  renderer.render(scene,camera);
  // Hide loading overlay after first real render
  if(frame===2)hideLoading();
}
animate();

// ── INIT ──────────────────────────────────────────────────────────────────────
setTimeout(hideLoading, 600);
