import vtk

from pathlib import Path

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5 import QtCore, QtWidgets


from vtkmodules.vtkInteractionWidgets import (
    vtkContourWidget,
    vtkOrientedGlyphContourRepresentation,
    vtkDijkstraImageContourLineInterpolator,
)

from dataclasses import dataclass
from typing import Optional
from vtkmodules.vtkImagingStencil import vtkImageStencil, vtkPolyDataToImageStencil
from vtkmodules.vtkImagingCore import vtkImageCast
@dataclass
class ViewerHandles:
    vtk_widget: QVTKRenderWindowInteractor
    render_window: vtk.vtkRenderWindow
    renderer: vtk.vtkRenderer
    image_reader: vtk.vtkImageReader2
    image_actor: vtk.vtkImageActor
    contour_widget: Optional[vtkContourWidget] = None


class ActionsPyQt5:
    def __init__(self, host):
        self.host = host
        self._viewer_actions = ActionsVTK()
        self._connect()
    
    def on_open(self, path):
        if not path:
            return None

        ext = Path(path).suffix
        #print(f"Selected file: {path}")
        data = self._loaders[ext].load(self.host, path)
        self.on_main_window_resize()
        QtCore.QTimer.singleShot(0, self.on_main_window_resize)
        #print(f"Data loaded: {data}")
        return data

    def enable_magnetic_segmentation(self):
        try:
            self._viewer_actions.enable_magnetic_segmentation()
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


class ActionsVTK:
    def __init__(self):
        self._h = None

    def load(self, host, path: str):
        render = vtk.vtkImageReader2Factory().CreateImageReader2(path)
        render.SetFileName(path)
        render.Update()
    
        container = host.findChild(QtWidgets.QWidget, "widgetMain2DViewer")
        layout = container.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        
        vtk_widget = QVTKRenderWindowInteractor(container)
        vtk_widget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(vtk_widget)

        rw = vtk_widget.GetRenderWindow()
        ren = vtk.vtkRenderer()
        rw.AddRenderer(ren)

        actor = vtk.vtkImageActor()
        ren.AddActor(actor)
        vtk_widget.Initialize()
        
        actor.GetMapper().SetInputData(render.GetOutput())
        ren.ResetCamera()
        vtk_widget.GetRenderWindow().Render()

        self._h = ViewerHandles(
            vtk_widget=vtk_widget,
            render_window=rw,
            renderer=ren,
            image_reader=render,
            image_actor=actor,
        )
        return render.GetOutput()

    def _require_handles(self) -> ViewerHandles:
        if self._h is None:
            raise RuntimeError("Viewer not loaded. Call load(host, path) first.")
        return self._h

    def enable_magnetic_segmentation(self) -> None:
            h = self._require_handles()

            if h.contour_widget is not None:
                return

            iren = h.vtk_widget.GetRenderWindow().GetInteractor()
            iren.SetInteractorStyle(vtk.vtkInteractorStyleImage())

            img = h.image_reader.GetOutput()

            # 1) Suavizar (reduce ruido)
            gauss = vtk.vtkImageGaussianSmooth()
            gauss.SetInputData(img)
            gauss.SetStandardDeviations(1.0, 1.0, 0.0)
            gauss.Update()

            # 2) Gradiente (magnitud)
            grad = vtk.vtkImageGradientMagnitude()
            grad.SetInputConnection(gauss.GetOutputPort())
            grad.SetDimensionality(2)
            grad.Update()

            # 3) Convertir gradiente a costo: cost = 1 / (1 + grad)
            # VTK no tiene "reciprocal(1+X)" directo limpio; usa vtkImageMathematics:
            # 3) denom = 1 + grad
            denom = vtk.vtkImageMathematics()
            denom.SetInputConnection(0, grad.GetOutputPort())
            denom.SetOperationToAddConstant()
            denom.SetConstantK(1.0)
            denom.Update()

            # 4) ones image con la MISMA geometría que img (extent/origin/spacing)
            ones = vtk.vtkImageData()
            ones.DeepCopy(img)  # copia geometría y también escalares; luego los sobreescribimos
            ones.AllocateScalars(vtk.VTK_FLOAT, 1)
            ones.GetPointData().GetScalars().FillComponent(0, 1.0)

            # 5) cost = ones / denom
            div = vtk.vtkImageMathematics()
            div.SetInputData(0, ones)
            div.SetInputConnection(1, denom.GetOutputPort())
            div.SetOperationToDivide()
            div.Update()

            cost_img = div.GetOutput()

            dijkstra = vtk.vtkDijkstraImageContourLineInterpolator()
            dijkstra.SetCostImage(cost_img)

            contour = vtkContourWidget()
            contour.SetInteractor(iren)

            #rep = vtkOrientedGlyphContourRepresentation()
            rep = vtk.vtkOrientedGlyphContourRepresentation.SafeDownCast(
                contour.GetRepresentation()
            )
            rep.SetLineInterpolator(dijkstra)
            rep.GetLinesProperty().SetLineWidth(2.5)
            contour.SetRepresentation(rep)

            contour.On()

            h.contour_widget = contour
            h.render_window.Render()

            # Tip: If you want to guide the user, you can show tooltips or status-bar hints here.
            # E.g. "Click to add points; drag points; close loop; press OK to rasterize."
