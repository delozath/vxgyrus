"""Domain model: Mask (label map aligned to a Volume).

Put here:
- Mask dataclass:
  - data: numpy ndarray uint8/uint16 (same shape as volume)
  - label definitions (id->name/color)
  - dirty_slices tracking (optional)
- operations:
  - paint/erase on slice region
  - merge, clear, relabel
"""
