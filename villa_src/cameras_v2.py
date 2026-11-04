"""Camera set for the v2 exterior + interior stills.

Same idea as `cameras.py`, but composed for the rebuild: the garden view is the hero,
and the interior shots sit lower with longer lenses, which is how architectural
photography is actually shot (a 1.2 m eye height and a 24-35 mm lens, not a 1.5 m
standing height with a wide angle).
"""
SHOTS = {
    # ---- exterior (hero)
    "hero_garden":   ((7.00, -16.20, 1.85), (9.60, 3.0, 1.70), 35.0),
    "hero_pool":     ((22.80, -7.40, 1.95), (12.40, 2.6, 1.75), 30.0),
    "hero_entry":    ((22.90, 10.20, 2.15), (18.90, 5.30, 1.55), 30.0),
    "hero_dusk":     ((4.20, -19.0, 2.10), (9.0, 3.0, 1.90), 26.0),
    "hero_aerial":   ((9.50, -24.0, 16.0), (9.5, 3.0, 0.0), 30.0),
    "detail_terrace": ((3.10, -7.40, 1.35), (9.4, -2.6, 1.25), 45.0),
    # ---- interior
    "living":        ((9.05, 0.95, 1.22), (2.30, 4.70, 1.05), 28.0),
    "living_wide":   ((11.90, 1.55, 1.30), (1.60, 5.60, 1.00), 21.0),
    "kitchen":       ((11.20, 1.25, 1.28), (14.90, 4.60, 1.05), 22.0),
    "dining":        ((6.95, 1.10, 1.25), (10.30, 5.10, 1.02), 28.0),
    "master":        ((4.90, 11.90, 1.24), (1.00, 9.40, 0.95), 24.0),
    "corridor":      ((17.30, 7.18, 1.42), (2.20, 7.10, 1.25), 30.0),
}
