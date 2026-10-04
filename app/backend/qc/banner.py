"""Banner applicability is separate from geometry evidence and may evolve independently."""


def banner_region(rules, position, shot_type):
    mode = rules.get("banner_application", "all")  # Legacy positive-height banners applied everywhere.
    height = rules.get("banner_top_pct", 0) / 100
    allowed = rules.get("banner_shot_types", [])
    applicable = mode != "none" and height > 0 and (mode != "first" or position == 1)
    if applicable and allowed:
        applicable = None if shot_type == "unknown" else shot_type in allowed
    return {
        "mode": mode,
        "applicable": applicable,
        "top_fraction": height,
        "clearance_fraction": rules.get("banner_clearance_pct", 0) / 100,
        "region_version": 1,
    }


def banner_overlap(region, vehicle_top=None):
    if region["applicable"] is False:
        return "not_applicable"
    if region["applicable"] is None:
        return "needs_shot_label"
    if vehicle_top is None:
        return "unavailable"
    if not 0 <= vehicle_top <= 1:
        raise ValueError("Vehicle top must be normalized to image height.")
    return "overlap" if vehicle_top < region["top_fraction"] + region["clearance_fraction"] else "clear"
