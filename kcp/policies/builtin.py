BUILTIN_POLICIES = {
    "camera_coverage_12_v1": {
        "policy_id": "camera_coverage_12_v1",
        "label": "Camera Coverage 12-pack",
        "default_count": 12,
        "seed_strategy": {"mode": "offset", "offsets": list(range(12))},
        "injections": [
            {"label": "28mm wide eye level doorway", "text": "28mm lens, wide shot, eye level, doorway perspective"},
            {"label": "35mm medium eye level", "text": "35mm lens, medium shot, eye level"},
            {"label": "50mm medium close-up eye level", "text": "50mm lens, medium close-up, eye level"},
            {"label": "28mm wide slight low", "text": "28mm lens, wide shot, slight low angle"},
            {"label": "35mm medium slight low", "text": "35mm lens, medium shot, slight low angle"},
            {"label": "50mm close-up shallow dof", "text": "50mm lens, close-up emphasis, shallow depth of field"},
            {"label": "OTS POV centered", "text": "over-the-shoulder POV, subject centered"},
            {"label": "Profile 3/4 medium", "text": "profile 3/4 view, medium shot"},
            {"label": "High angle establishing", "text": "high angle mild, establishing"},
            {"label": "Low angle authority", "text": "low angle mild, subject authority"},
            {"label": "Two-shot composition", "text": "two-shot composition framing, keep POV hands visible only if present"},
            {"label": "Detail insert", "text": "detail insert framing, hands or gesture emphasis"},
        ],
    },
    "lens_bracket_3x4_v1": {
        "policy_id": "lens_bracket_3x4_v1",
        "label": "Lens Bracket 3x4",
        "default_count": 12,
        "seed_strategy": {"mode": "offset", "offsets": list(range(12))},
        "injections": [
            {"label": f"{lens}mm {framing}", "text": f"{lens}mm lens, {framing} framing"}
            for lens in (28, 35, 50)
            for framing in ("wide shot", "medium shot", "close shot", "over-shoulder shot")
        ],
    },
    "seed_sweep_12_v1": {
        "policy_id": "seed_sweep_12_v1",
        "label": "Seed Sweep 12",
        "default_count": 12,
        "seed_strategy": {"mode": "offset", "offsets": list(range(12))},
        "injections": [{"label": f"Seed {i}", "text": ""} for i in range(12)],
    },
    "micro_variation_12_v1": {
        "policy_id": "micro_variation_12_v1",
        "label": "Micro Variation 12",
        "default_count": 12,
        "seed_strategy": {"mode": "offset", "offsets": list(range(12))},
        "injections": [
            {"label": "subtle natural expression", "text": "subtle natural expression"},
            {"label": "slight head tilt", "text": "slight head tilt"},
            {"label": "natural weight shift", "text": "natural weight shift"},
            {"label": "hand gesture slightly different", "text": "hand gesture slightly different"},
            {"label": "tiny posture settle", "text": "tiny posture settle"},
            {"label": "small gaze adjustment", "text": "small gaze adjustment"},
            {"label": "soft breathing motion", "text": "soft breathing motion"},
            {"label": "minor shoulder relaxation", "text": "minor shoulder relaxation"},
            {"label": "slight chin raise", "text": "slight chin raise"},
            {"label": "slight chin drop", "text": "slight chin drop"},
            {"label": "micro hand reposition", "text": "micro hand reposition"},
            {"label": "minimal stance shift", "text": "minimal stance shift"},
        ],
    },
}
