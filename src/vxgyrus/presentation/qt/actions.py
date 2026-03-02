import vtk
from pathlib import Path

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5 import QtCore, QtWidgets

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Callable

import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk


# =============================================================================
# CORE: pincel + pintado + mask->vtk
# =============================================================================

def brush_offsets_ellipse(rx_vox: float, ry_vox: float) -> np.ndarray:
    """
    Offsets enteros (dy,dx) dentro de una elipse:
        (dx/rx)^2 + (dy/ry)^2 <= 1

    rx_vox, ry_vox: radios en "voxeles/píxeles".
    """
    rx = max(float(rx_vox), 0.5)
    ry = max(float(ry_vox), 0.5)
    x_max = int(np.ceil(rx))
    y_max = int(np.ceil(ry))

    pts: List[Tuple[int, int]] = []
    for dy in range(-y_max, y_max + 1):
        for dx in range(-x_max, x_max + 1):
            if (dx * dx) / (rx * rx) + (dy * dy) / (ry * ry) <= 1.0:
                pts.append((dy, dx))
    return np.asarray(pts, dtype=np.int32)


def draw_line_with_brush(mask2d: np.ndarray,
                         p0: Tuple[int, int],
                         p1: Tuple[int, int],
                         offsets: np.ndarray,
                         value: int) -> None:
    """
    Dibuja una línea p0->p1 sobre mask2d aplicando offsets dy/dx del pincel.
    p0,p1: (y,x) en índices.
    """
    h, w = mask2d.shape
    y0, x0 = p0
    y1, x1 = p1
    dy = y1 - y0
    dx = x1 - x0
    n = int(max(abs(dx), abs(dy)))

    if n == 0:
        yy, xx = y0, x0
        for oy, ox in offsets:
            y = yy + int(oy)
            x = xx + int(ox)
            if 0 <= y < h and 0 <= x < w:
                mask2d[y, x] = value
        return

    for t in np.linspace(0.0, 1.0, n + 1):
        yy = int(round(y0 + t * dy))
        xx = int(round(x0 + t * dx))
        for oy, ox in offsets:
            y = yy + int(oy)
            x = xx + int(ox)
            if 0 <= y < h and 0 <= x < w:
                mask2d[y, x] = value


def numpy_mask2d_to_vtk(mask_yx_u8: np.ndarray,
                        spacing_xy: Tuple[float, float],
                        origin_xy: Tuple[float, float]) -> vtk.vtkImageData:
    """
    mask (H,W) -> vtkImageData (W,H,1), con spacing/origin coherentes.
    """
    h, w = mask_yx_u8.shape
    img = vtk.vtkImageData()
    img.SetDimensions(w, h, 1)
    img.SetSpacing(float(spacing_xy[0]), float(spacing_xy[1]), 1.0)
    img.SetOrigin(float(origin_xy[0]), float(origin_xy[1]), 0.0)

    flat = mask_yx_u8.astype(np.uint8, copy=False).ravel(order="C")
    vtk_arr = numpy_to_vtk(flat, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    img.GetPointData().SetScalars(vtk_arr)
    return img


# =============================================================================
# UI actions wrapper (PyQt5)
# =============================================================================

class ActionsPyQt5:
    def __init__(self, host):
        self.host = host
        self._viewer_actions = ActionsVTK()
        self._connect()

    def on_open(self, path):
        if not path:
            return None

        ext = Path(path).suffix.lower()
        data = self._loaders[ext].load(self.host, path)

        # Reajuste tamaño
        self.on_main_window_resize()
        QtCore.QTimer.singleShot(0, self.on_main_window_resize)

        return data

    def enable_manual_segmentation(self):
        try:
            self._viewer_actions.enable_manual_segmentation()
        except RuntimeError as error:
            QtWidgets.QMessageBox.information(
                self.host,
                "Enable Segmentation",
                str(error),
            )

    def on_main_window_resize(self):
        container = self.host.findChild(QtWidgets.QWidget, "widgetMain2DViewer")
        if container is None:
            return

        vtk_widget = container.findChild(QVTKRenderWindowInteractor)
        if vtk_widget is None:
            return

        size = container.size()
        vtk_widget.resize(size)
        rw = vtk_widget.GetRenderWindow()
        rw.SetSize(size.width(), size.height())
        rw.Render()

    def _connect(self):
        self._loaders = {
            ".png": self._viewer_actions,
            ".jpg": self._viewer_actions,
            ".jpeg": self._viewer_actions,
        }


# =============================================================================
# VTK handles (viewer ya creado)
# =============================================================================

@dataclass
class VTK2DHandles:
    vtk_widget: QVTKRenderWindowInteractor
    render_window: vtk.vtkRenderWindow
    renderer: vtk.vtkRenderer
    interactor: vtk.vtkRenderWindowInteractor
    base_actor: vtk.vtkImageActor


# =============================================================================
# Overlay + tracer (lazy init)
# =============================================================================

class VTK2DOverlayBase:
    """
    - No crea la vista base (eso ya lo hace ActionsVTK.load()).
    - Añade:
        * overlay de máscara (vtkImageActor + LUT alpha)
        * tracer (vtkImageTracerWidget) ligado al actor base
    - Lazy init: ensure_segmenter() crea todo solo una vez.
    """

    def __init__(self, container: VTK2DHandles):
        self.container = container

        # Estos se crean lazily
        self.tracer: Optional[vtk.vtkImageTracerWidget] = None
        self.mask_actor: Optional[vtk.vtkImageActor] = None
        self.mask_map: Optional[vtk.vtkImageMapToColors] = None

    def ensure_segmenter(self, on_tracer_end: Callable[[], None]) -> None:
        """
        Crea tracer + overlay + observer SOLO si no existen.
        """
        if self.tracer is not None and self.mask_actor is not None and self.mask_map is not None:
            return

        # ---- Overlay LUT (0 transparente, 1 rojo alpha) ----
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

        # ---- Tracer ----
        tracer = vtk.vtkImageTracerWidget()
        tracer.SetInteractor(self.container.interactor)

        # Crucial: ligar al actor base (coherencia de coordenadas con la imagen)
        tracer.SetViewProp(self.container.base_actor)

        # Plano 2D y snap al grid
        tracer.ProjectToPlaneOn()
        tracer.SnapToImageOn()
        tracer.AutoCloseOff()

        # Callback al terminar el trazo
        tracer.AddObserver("EndInteractionEvent", lambda obj, evt: on_tracer_end())

        # Arranca apagado; el controlador decide On/Off
        tracer.Off()

        self.tracer = tracer
        self.mask_actor = mask_actor
        self.mask_map = mask_map

        self.container.render_window.Render()

    def set_segmentation_enabled(self, enabled: bool) -> None:
        if self.tracer is None:
            return
        self.tracer.On() if enabled else self.tracer.Off()
        self.container.render_window.Render()

    def set_tracer_line_width(self, lw: float) -> None:
        if self.tracer is None:
            return
        self.tracer.GetLineProperty().SetLineWidth(max(1.0, float(lw)))
        self.container.render_window.Render()

    def update_mask_overlay(self, vtk_mask2d: vtk.vtkImageData) -> None:
        if self.mask_map is None:
            return
        self.mask_map.SetInputData(vtk_mask2d)
        self.mask_map.Update()
        self.container.render_window.Render()

    def get_tracer_path_world(self) -> List[Tuple[float, float, float]]:
        """
        Puntos world (xw,yw,zw) del trazo actual.
        """
        if self.tracer is None:
            return []
        poly = vtk.vtkPolyData()
        self.tracer.GetPath(poly)
        npts = poly.GetNumberOfPoints()
        if npts < 1:
            return []
        pts = poly.GetPoints()
        return [pts.GetPoint(i) for i in range(npts)]


# =============================================================================
# Segmentación manual 2D controller
# =============================================================================

@dataclass
class Seg2DState:
    mask2d: np.ndarray
from .GUI_Model.win_segmentation import Ui_Dialog, QtWidgets
from .win_guardar import win_sav
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkImageActor,
    vtkPolyDataMapper,
    vtkRenderer
)
from vtk.numpy_interface import dataset_adapter as dsa
from itk import GetImageFromArray, vtk_image_from_image
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtk import (vtkMatrix4x4, vtkImageReslice, vtkLookupTable, vtkImageMapToColors,
                 vtkInteractorStyleImage,vtkImageTracerWidget,vtkPolyData, vtkFlyingEdges2D)
from numpy import ascontiguousarray, array, zeros, save, round, cos, sin,pi, linspace
from numpy import __name__ as np_name

def circular_plane(radio):
    if radio !=1:
        a = 0 if radio%2 == 0 else .5
        radio = int(radio/2)
    else:
        return array([array([0,0])])
    #
    phi = [[0,0]]
    for r in range(1,radio+1):
        theta = linspace(0,2*pi,(r)*9)
        phi += [[(r+a)*cos(angle),(r+a)*sin(angle)] for angle in theta]
    return array(phi).astype(int)

def recta(init,final,width,k,vol,borrar = False):
    valor = 0 if borrar else 1
    v = final-init
    nx = int(abs(round(final[0])-init[0]))
    ny = int(abs(round(final[1]-init[1])))
    if nx == 0 and ny > 0:
        n = ny
    elif nx == 0 and ny == 0:
        cir_plane = circular_plane(width)
        for c in cir_plane:
            try:
                vol[k][int(c[1]+init[1])][int(c[0]+init[0])] = valor
            except (ValueError,IndexError):
                pass
        return
    else:
        n = nx
    v = v/n
    recta = [init[:2] + phi*v[:2] for phi in range(n+1)]
    cir_plane = circular_plane(width-2)
    for point in recta:
        for c in cir_plane:
            try:
                vol[k][int(c[1]+init[1])][int(c[0]+init[0])] = valor
            except (ValueError,IndexError):
                pass

class win_seg(QtWidgets.QDialog):
    def __init__(self,rotNcut,spacing,manual_segment = None, targets = None):
        super().__init__()
        self.win = Ui_Dialog()
        self.win.setupUi(self)
        #-----------Manejo de eventos GUI------------
        self.ans_slice = 0
        self.borrar = False
        self.win.slice_numberBox.setMaximum(rotNcut.shape[0]-1)
        #----------------atributos vtk---------------
        self.colors = vtkNamedColors()
        self.colors.SetColor("BkgColor", [0,0,0,255])
        self.colors.SetColor('traza', [0,0,255,255])
        self.rNc = rotNcut
        if type(manual_segment).__module__ == np_name:
            self.manual_segment = manual_segment
            self.targets = [int(i) for i in targets]
        else:
            self.manual_segment = zeros(self.rNc.shape)
            self.targets = list()
        self.vol = GetImageFromArray(ascontiguousarray(self.rNc))
        self.spacing = spacing
        self.vol = vtk_image_from_image(self.vol)
        self.vol.SetSpacing(*self.spacing)
        self.axial = array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
            ])
        #---------configuración de ventana vtk-------
        self.vtkWidget = QVTKRenderWindowInteractor()
        self.win.verticalLcut.addWidget(self.vtkWidget)
        self.ren = vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        self.show_im()
        if len(self.targets) > 0:
            self.win.slice_numberBox.setValue(targets[0])
            self.slicing()
            #
    def show_im(self):
        axial = vtkMatrix4x4()
        axial.DeepCopy(tuple(i for i in self.axial.reshape(16)))
        # Extract a slice in the desired orientation
        self.reslice = vtkImageReslice()
        self.reslice.SetInputData(self.vol)
        self.reslice.SetOutputDimensionality(2)
        self.reslice.SetResliceAxes(axial)
        self.reslice.SetInterpolationModeToCubic()
        # Create a greyscale lookup table
        table = vtkLookupTable()
        table.SetRange(0, 255) # image intensity range
        table.SetValueRange(255, 0) # from black to white 255 0
        table.SetSaturationRange(0, 0) # no color saturation
        table.SetRampToLinear()
        table.Build()
        # Map the image through the lookup table
        color = vtkImageMapToColors()
        color.SetLookupTable(table)
        color.SetInputConnection(self.reslice.GetOutputPort())
        # Display the image
        self.actor = vtkImageActor()
        self.actor.GetMapper().SetInputConnection(color.GetOutputPort())
        self.ren.AddActor(self.actor)
        self.interactorStyle = vtkInteractorStyleImage()
        self.iren.SetInteractorStyle(self.interactorStyle)
        #------------------Tracer widget---------------------
        self.actort = vtkImageActor()
        self.actort.GetMapper().SetInputData(self.vol)
        self.ren.AddActor(self.actort)
        self.tracer = vtkImageTracerWidget()
        self.tracer.GetLineProperty().SetLineWidth(1)
        self.tracer.GetLineProperty().SetLineWidth(2/self.spacing[1])
        self.tracer.SetViewProp(self.actort)
        self.tracer.SetInteractor(self.iren)
        self.tracer.AutoCloseOff()
        #----------------Segmentación manual----------------------
        slice = self.manual_segment[0,::]
        slice = GetImageFromArray(ascontiguousarray(slice))
        slice = vtk_image_from_image(slice)
        slice.SetSpacing(*self.vol.GetSpacing())
        FlyingEd =vtkFlyingEdges2D()
        FlyingEd.SetInputData(slice)
        FlyingEd.GenerateValues(10,[0,1])
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(FlyingEd.GetOutputPort())
        self.actori = vtkActor()
        self.actori.SetMapper(mapper)
        self.ren.AddActor(self.actori)
        #
        self.vtkWidget.Render()
        self.tracer.AddObserver("EndInteractionEvent",self.callback_tracer)
        self.iren.Initialize()
        self.iren.Start()
        self.win.activate_draw.stateChanged.connect(self.actdeactTracer)
        self.win.slice_numberBox.valueChanged.connect(self.slicing)
        self.win.radio_numberBox.valueChanged.connect(self.modify_rad)
        self.win.dibujar_btn.clicked.connect(self.setDibujar)
        self.win.borrar_btn.clicked.connect(self.setBorrar)
        self.win.guardar_btn.clicked.connect(self.guardar)
    #
    def slicing(self):
        self.reslice.Update()
        sliceSpacing = self.reslice.GetOutput().GetSpacing()[2]
        matrix = self.reslice.GetResliceAxes()
        k = self.win.slice_numberBox.value()
        if k < self.manual_segment.shape[0]:
            n = k - self.ans_slice
            center = matrix.MultiplyPoint((0,0,sliceSpacing*n,1))
            matrix.SetElement(0,3,center[0])
            matrix.SetElement(1,3,center[1])
            matrix.SetElement(2,3,center[2])
            self.ans_slice = self.win.slice_numberBox.value()
            slice = self.manual_segment[k,::]
            slice = GetImageFromArray(ascontiguousarray(slice))
            slice = vtk_image_from_image(slice)
            slice.SetSpacing(*self.vol.GetSpacing())
            FlyingEd =vtkFlyingEdges2D()
            FlyingEd.SetInputData(slice)
            FlyingEd.GenerateValues(10,[0,1])
            mapper = vtkPolyDataMapper()
            mapper.SetInputConnection(FlyingEd.GetOutputPort())
            self.actori.SetMapper(mapper)
            self.vtkWidget.Render()
    #
    def actdeactTracer(self):
        if self.win.activate_draw.isChecked():
            self.tracer.On()
        else:
            self.tracer.Off()
    #
    def callback_tracer(self,obj,event):
        path = vtkPolyData()
        self.tracer.GetPath(path)
        points = dsa.WrapDataObject(path).Points
        points = points/self.spacing
        k = self.win.slice_numberBox.value()
        radio = int(self.win.radio_numberBox.value())
        for i in range(len(points)-1):
            recta(points[i],points[i+1],radio,k,self.manual_segment,self.borrar)
        slice = self.manual_segment[k,::]
        slice = GetImageFromArray(ascontiguousarray(slice))
        slice = vtk_image_from_image(slice)
        slice.SetSpacing(*self.vol.GetSpacing())
        FlyingEd =vtkFlyingEdges2D()
        FlyingEd.SetInputData(slice)
        FlyingEd.GenerateValues(10,[0,1])
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(FlyingEd.GetOutputPort())
        self.actori.SetMapper(mapper)
        self.ren.Render()
        if k not in self.targets:
            self.targets.append(k)
    #
    def modify_rad(self):
        self.tracer.GetLineProperty().SetLineWidth(self.win.radio_numberBox.value()*2/self.spacing[1])
    #
    def setDibujar(self):
        self.borrar = False
        self.win.dibujar_btn.setStyleSheet("background-color: rgb(255, 85, 0);")
        self.win.borrar_btn.setStyleSheet("background-color: rgb(32, 177, 124);")
    #
    def setBorrar(self):
        self.borrar = True
        self.win.dibujar_btn.setStyleSheet("background-color: rgb(32, 177, 124);")
        self.win.borrar_btn.setStyleSheet("background-color: rgb(255, 85, 0);")
    #
    def guardar(self):
        self.targets.sort()
        #sav = win_sav(self.manual_segment,self.rNc,self.spacing,self.targets)
        win_sav(self.manual_segment,self.rNc,self.spacing,self.targets)
        #sav.exec_()
        self.close()
    #
    def closeEvent(self,QCloseEvent):
        super().closeEvent(QCloseEvent)
        self.vtkWidget.Finalize()
        self.vtkWidget.close()    origin_xy: Tuple[float, float]
    brush_radius_mm: float = 600.0
    erase: bool = False


class ManualVoxelSeg2DController:
    """
    Controlador de segmentación 2D:
    - Usa VTK2DOverlayBase para tracer+overlay.
    - Mantiene mask2d (numpy) y pinta voxeles al finalizar un trazo.
    - Lazy init: solo cuando se habilita por primera vez.
    """

    def __init__(self):
        self.viewer: Optional[VTK2DOverlayBase] = None
        self.state: Optional[Seg2DState] = None
        self._seg_enabled = False
        self._brush_cache: Dict[Tuple[int, int], np.ndarray] = {}

    def bind(self,
             viewer: VTK2DOverlayBase,
             vtk_img2d: vtk.vtkImageData,
             spacing_xy: Tuple[float, float] = (1.0, 1.0),
             origin_xy: Tuple[float, float] = (0.0, 0.0),
             existing_mask2d: Optional[np.ndarray] = None,
             initial_radius_mm: float = 3.0) -> None:
        """
        Une el controlador con el overlay (que conoce el interactor/actor base),
        y crea/valida la máscara 2D.
        """
        self.viewer = viewer

        w, h, z = vtk_img2d.GetDimensions()
        if z != 1:
            raise RuntimeError(f"Se esperaba imagen 2D (Z=1). dims={vtk_img2d.GetDimensions()}")

        if existing_mask2d is None:
            mask2d = np.zeros((h, w), dtype=np.uint8)
        else:
            mask2d = existing_mask2d.astype(np.uint8, copy=False)
            if mask2d.shape != (h, w):
                raise ValueError(f"Mask shape {mask2d.shape} != {(h, w)}")

        self.state = Seg2DState(
            mask2d=mask2d,
            spacing_xy=(float(spacing_xy[0]), float(spacing_xy[1])),
            origin_xy=(float(origin_xy[0]), float(origin_xy[1])),
            brush_radius_mm=float(initial_radius_mm),
            erase=False
        )

        self._seg_enabled = False

    def enable_segmentation(self, enabled: bool) -> None:
        """
        Activación desde tu botón.
        """
        if self.viewer is None or self.state is None:
            raise RuntimeError("Primero llama bind(...) con un viewer válido.")

        enabled = bool(enabled)

        # Lazy init SOLO si se va a activar
        if enabled:
            self.viewer.ensure_segmenter(on_tracer_end=self._on_tracer_end)
            self._sync_linewidth()
            self._refresh_overlay()

        self._seg_enabled = enabled
        self.viewer.set_segmentation_enabled(enabled)

    def set_mode(self, erase: bool) -> None:
        if self.state is None:
            raise RuntimeError("No inicializado.")
        self.state.erase = bool(erase)

    def set_brush_radius_mm(self, r_mm: float) -> None:
        if self.state is None:
            raise RuntimeError("No inicializado.")
        self.state.brush_radius_mm = float(r_mm)
        if self.viewer is not None and self.viewer.tracer is not None:
            self._sync_linewidth()

    def get_mask2d(self) -> np.ndarray:
        if self.state is None:
            raise RuntimeError("No inicializado.")
        return self.state.mask2d

    # ---- internals ----

    def _sync_linewidth(self) -> None:
        assert self.viewer is not None and self.state is not None
        _, sy = self.state.spacing_xy
        diam_vox = (2.0 * self.state.brush_radius_mm) / sy
        self.viewer.set_tracer_line_width(max(1.0, float(diam_vox)))

    def _get_brush_offsets(self) -> np.ndarray:
        assert self.state is not None
        sx, sy = self.state.spacing_xy
        r = self.state.brush_radius_mm
        rx = r / sx
        ry = r / sy
        key = (int(np.ceil(rx)), int(np.ceil(ry)))
        if key not in self._brush_cache:
            self._brush_cache[key] = brush_offsets_ellipse(rx, ry)
        return self._brush_cache[key]

    def _world_to_pixel_yx(self, xw: float, yw: float) -> Tuple[int, int]:
        """
        World -> pixel (y,x) usando origin+spacing.
        """
        assert self.state is not None
        ox, oy = self.state.origin_xy
        sx, sy = self.state.spacing_xy
        ix = int(round((xw - ox) / sx))
        iy = int(round((yw - oy) / sy))
        return iy, ix

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

        pix = [self._world_to_pixel_yx(xw, yw) for (xw, yw, zw) in world]
        offsets = self._get_brush_offsets()
        value = 0 if self.state.erase else 1

        for p0, p1 in zip(pix[:-1], pix[1:]):
            draw_line_with_brush(self.state.mask2d, p0, p1, offsets, value)

        self._refresh_overlay()

    def _refresh_overlay(self) -> None:
        assert self.viewer is not None and self.state is not None
        if self.viewer.mask_map is None:
            return
        vtk_mask = numpy_mask2d_to_vtk(self.state.mask2d, self.state.spacing_xy, self.state.origin_xy)
        self.viewer.update_mask_overlay(vtk_mask)


# =============================================================================
# ActionsVTK: loader + activación
# =============================================================================

class ActionsVTK:
    def __init__(self):
        self.container: Optional[VTK2DHandles] = None
        self._vtk_img2d: Optional[vtk.vtkImageData] = None

        # Segmentación (se crean al habilitar)
        self._overlay: Optional[VTK2DOverlayBase] = None
        self._driver: Optional[ManualVoxelSeg2DController] = None

        # Parámetros (ajústalos si quieres)
        self.spacing_xy = (1.0, 1.0)
        self.origin_xy = (0.0, 0.0)

    def load(self, host, path: str):
        reader = vtk.vtkImageReader2Factory().CreateImageReader2(path)
        if reader is None:
            raise RuntimeError(f"VTK no pudo crear reader para: {path}")
        reader.SetFileName(path)
        reader.Update()

        vtk_img = reader.GetOutput()
        self._vtk_img2d = vtk_img

        win_container = host.findChild(QtWidgets.QWidget, "widgetMain2DViewer")
        if win_container is None:
            raise RuntimeError('No existe widgetMain2DViewer en el host.')

        layout = win_container.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(win_container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        # Limpiar viejo VTK widget
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()

        vtk_widget = QVTKRenderWindowInteractor(win_container)
        vtk_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(vtk_widget)

        rw = vtk_widget.GetRenderWindow()
        ren = vtk.vtkRenderer()
        rw.AddRenderer(ren)

        actor = vtk.vtkImageActor()
        ren.AddActor(actor)

        vtk_widget.Initialize()

        actor.GetMapper().SetInputData(vtk_img)
        ren.ResetCamera()
        rw.Render()

        iren = rw.GetInteractor()
        iren.SetInteractorStyle(vtk.vtkInteractorStyleImage())

        self.container = VTK2DHandles(
            vtk_widget=vtk_widget,
            render_window=rw,
            renderer=ren,
            interactor=iren,
            base_actor=actor,
        )

        # Reset segmentación (si cambiaste de imagen)
        self._overlay = None
        self._driver = None

        return vtk_img

    def enable_manual_segmentation(self):
        """
        Llamado por tu botón:
        - crea overlay+driver si no existen
        - habilita tracer ON
        """
        if self.container is None or self._vtk_img2d is None:
            raise RuntimeError("Primero carga una imagen antes de habilitar segmentación.")

        # Lazy init overlay/driver (una sola vez por imagen cargada)
        if self._overlay is None:
            self._overlay = VTK2DOverlayBase(self.container)

        if self._driver is None:
            self._driver = ManualVoxelSeg2DController()
            self._driver.bind(
                viewer=self._overlay,
                vtk_img2d=self._vtk_img2d,
                spacing_xy=self.spacing_xy,
                origin_xy=self.origin_xy,
                existing_mask2d=None,
                initial_radius_mm=3.0,
            )

        print("Enabling manual segmentation...")
        self._driver.enable_segmentation(True)

    # Opcional: métodos para que conectes otros botones/spinboxes
    def disable_manual_segmentation(self):
        if self._driver is None:
            return
        self._driver.enable_segmentation(False)

    def set_draw_mode(self):
        if self._driver is None:
            return
        self._driver.set_mode(erase=False)

    def set_erase_mode(self):
        if self._driver is None:
            return
        self._driver.set_mode(erase=True)

    def set_radius_mm(self, r_mm: float):
        if self._driver is None:
            return
        self._driver.set_brush_radius_mm(r_mm)

    def get_mask2d(self) -> Optional[np.ndarray]:
        if self._driver is None:
            return None
        return self._driver.get_mask2d()