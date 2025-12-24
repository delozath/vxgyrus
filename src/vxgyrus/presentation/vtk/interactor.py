"""VTK interactor style for brush painting (pencil tool).

Put here:
- mouse events: press/move/release
- screen -> world -> voxel (IJK) mapping for current slice
- stroke aggregation (for undo/redo)
- call application.brush.apply_stroke(...)
"""
