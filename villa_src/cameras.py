"""Named camera presets for the hero stills and the walkthrough."""

# name -> (location, target, focal length mm, vertical fov helper)
SHOTS = {
    "hero_living": ((9.15, 1.05, 1.48), (2.40, 4.80, 1.12), 25.0),
    "living_from_kitchen": ((9.60, 1.70, 1.60), (2.40, 4.60, 1.25), 24.0),
    "kitchen_wide": ((11.60, 1.35, 1.62), (14.70, 4.30, 1.10), 19.0),
    "kitchen_island": ((13.90, 1.35, 1.35), (11.30, 4.40, 1.15), 24.0),
    "dining": ((7.55, 1.05, 1.50), (10.20, 5.00, 1.15), 24.0),
    "master": ((4.95, 12.00, 1.50), (1.10, 9.60, 1.05), 22.0),
    "bed2": ((10.90, 8.35, 1.55), (8.20, 11.40, 1.10), 22.0),
    "bath": ((5.78, 10.62, 1.40), (7.30, 11.60, 1.05), 15.0),
    "corridor": ((16.95, 7.16, 1.46), (2.00, 7.10, 1.30), 26.0),
    "foyer": ((15.45, 6.10, 1.52), (18.35, 4.05, 1.10), 18.0),
    "exterior": ((8.50, -13.00, 2.20), (9.50, 6.00, 1.40), 26.0),
    "study": ((17.52, 8.06, 1.52), (18.02, 11.55, 1.08), 17.0),
}

# walkthrough path: (position, look-at, hold seconds) -- routed along real doorways
# and clear floor lanes so the camera never enters a wall or a piece of furniture.
WALK = [
    ((18.55, 5.15, 1.55), (15.40, 5.02, 1.35), 2.6),   # front door
    ((17.10, 5.10, 1.55), (14.60, 4.85, 1.32), 2.4),   # foyer
    ((15.60, 4.90, 1.55), (13.20, 4.75, 1.28), 2.4),   # through the kitchen door
    ((14.10, 5.05, 1.55), (11.60, 4.85, 1.26), 2.4),   # past the fridge
    ((12.60, 5.35, 1.55), (10.20, 4.70, 1.24), 2.6),   # past the island
    ((10.60, 5.35, 1.55), (8.40, 4.60, 1.22), 2.6),    # dining
    ((8.60, 5.45, 1.55), (6.20, 4.60, 1.20), 2.6),     # toward the living room
    ((6.60, 5.50, 1.55), (4.00, 4.80, 1.18), 2.6),     # living, past the TV wall
    ((4.60, 5.35, 1.52), (1.20, 2.60, 1.10), 3.0),     # turn to the glazing
    ((2.90, 4.90, 1.50), (1.10, 1.30, 1.05), 3.0),     # settle on the garden view
]
