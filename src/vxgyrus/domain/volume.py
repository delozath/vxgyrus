"""Domain model: Volume.

Put here:
- Volume dataclass:
  - data: numpy ndarray (suggested canonical shape: Z,Y,X)
  - spacing/origin/direction
  - modality, uid, metadata references
- invariants (geometry consistency)
- helpers like get_slice(k), intensity normalization hooks
"""
