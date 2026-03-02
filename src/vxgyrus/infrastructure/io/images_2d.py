import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from typing import Callable
from dataclasses import dataclass

import numpy as np

@dataclass
class VTK2DHandles:
    image: vtk.vtkImageData
    widget: QVTKRenderWindowInteractor
    renwin: vtk.vtkRenderWindow
    renderer: vtk.vtkRenderer
    interactor: vtk.vtkRenderWindowInteractor
    actor: vtk.vtkImageActor


@dataclass
class Segmentation2DState:
    mask2d: np.ndarray
    spacing_xy: tuple[float, float]
    origin_xy: tuple[float, float]
    brush_radius_mm: float = 600.0
    erase: bool = False


class VTKImages2DLoader:
    def load(self, path: str):
        reader = vtk.vtkImageReader2Factory().CreateImageReader2(path)
        if reader is None:
            raise RuntimeError(f"VTK no pudo crear reader para: {path}")
        reader.SetFileName(path)
        reader.Update()

        vtk_img = reader.GetOutput()

        return vtk_img



class VTKImage2DTracerBackend:
    def __init__(self, container: VTK2DHandles):
        self.container = container

        # Lacy tracer + overlays
        self.tracer: vtk.vtkImageTracerWidget | None = None
        self.mask_actor: vtk.vtkImageActor | None = None
        self.mask_map: vtk.vtkImageMapToColors | None = None

    def event_end_tracing(self, on_tracer_end: Callable[[], None]) -> None:
        if self.tracer is not None and self.mask_actor is not None and self.mask_map is not None:
            return

        mask_lut = vtk.vtkLookupTable()
        mask_lut.SetNumberOfTableValues(2)
        mask_lut.Build()
        mask_lut.SetTableValue(0, 0.0, 0.0, 0.0, 0.0)
        mask_lut.SetTableValue(1, 1.0, 0.0, 0.0, 0.35)

        mask_map = vtk.vtkImageMapToColors()
        mask_map.SetLookupTable(mask_lut)

        mask_actor = vtk.vtkImageActor()
        mask_actor.GetMapper().SetInputConnection(mask_map.GetOutputPort())
        self.container.renderer.AddActor(mask_actor)

        tracer = vtk.vtkImageTracerWidget()
        tracer.SetInteractor(self.container.interactor)

        tracer.SetViewProp(self.container.actor)

        tracer.ProjectToPlaneOn()
        tracer.SnapToImageOn()
        tracer.AutoCloseOff()

        tracer.AddObserver("EndInteractionEvent", lambda obj, evt: on_tracer_end())

        tracer.Off()

        self.tracer = tracer
        self.mask_actor = mask_actor
        self.mask_map = mask_map

        self.container.renwin.Render()

    def set_segmentation_enabled(self, enabled: bool) -> None:
        if self.tracer is None:
            return
        self.tracer.On() if enabled else self.tracer.Off()
        self.container.renwin.Render()

    def set_tracer_line_width(self, lw: float) -> None:
        if self.tracer is None:
            return
        self.tracer.GetLineProperty().SetLineWidth(max(1.0, float(lw)))
        self.container.renwin.Render()

    def update_mask_overlay(self, vtk_mask2d: vtk.vtkImageData) -> None:
        if self.mask_map is None:
            return
        self.mask_map.SetInputData(vtk_mask2d)
        self.mask_map.Update()
        self.container.renwin.Render()

    def get_tracer_path_world(self) -> list[tuple[float, float, float]]:
        if self.tracer is None:
            return []
        poly = vtk.vtkPolyData()
        self.tracer.GetPath(poly)
        npts = poly.GetNumberOfPoints()
        if npts < 1:
            return []
        pts = poly.GetPoints()
        return [pts.GetPoint(i) for i in range(npts)]



class VTKImage2DTracerFrontend():
    def __init__(self):
            self.tracer: VTKImage2DTracerBackend | None = None
            self.state: Segmentation2DState | None = None
            self._seg_enabled = False
            self._brush_cache: dict[tuple[int, int], np.ndarray] = {}

    def bind(self,
             viewer: VTK2DHandles,
             spacing_xy: tuple[float, float] = (1.0, 1.0),
             origin_xy: tuple[float, float] = (0.0, 0.0),
             existing_mask2d: np.ndarray | None = None,
             initial_radius_mm: float = 3.0
        ) -> None:
        self.viewer = viewer
        """
        self.state = Segmentation2DState(
            mask2d=existing_mask2d if existing_mask2d is not None else np.zeros(self.viewer.vtk_container.image.GetDimensions()[:2], dtype=np.uint8),
            spacing_xy=spacing_xy,
            origin_xy=origin_xy,
            brush_radius_mm=initial_radius_mm
        )
        """
    
    def _on_tracer_end(self) -> None:
        """
        Al soltar el trazo: pinta en mask2d y actualiza overlay.
        """
        if not self._seg_enabled:
            return
        if self.viewer is None or self.state is None:
            return
        if self.viewer.tracer is None:
            return

        world = self.viewer.get_tracer_path_world()
        if len(world) < 1:
            return

        print("segmentando")
        """pix = [self._world_to_pixel_yx(xw, yw) for (xw, yw, zw) in world]
        offsets = self._get_brush_offsets()
        value = 0 if self.state.erase else 1

        for p0, p1 in zip(pix[:-1], pix[1:]):
            draw_line_with_brush(self.state.mask2d, p0, p1, offsets, value)

        self._refresh_overlay()"""