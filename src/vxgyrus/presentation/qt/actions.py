from vxgyrus.infrastructure.io.images_2d import VTKImage2DTracerFrontend, VTKImages2DLoader, VTK2DHandles
import vtk
from pathlib import Path

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt5 import QtCore, QtWidgets


import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk

class ActionsPyQt5:
    def __init__(self, host):
        self.host = host
        self._actions = ActionsVTK()
        self._connect()

    def on_open(self, path):
        if not path:
            return None

        ext = Path(path).suffix.lower()
        data = self._loaders[ext](self.host, path)

        self.on_main_window_resize()
        QtCore.QTimer.singleShot(0, self.on_main_window_resize)

        return data

    def manual_segmentation(self):
        try:
            self._actions.enable_manual_segmentation()
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
            ".png": self._actions.VTK2DLoaderSetWidget,
            ".jpg": self._actions.VTK2DLoaderSetWidget,
            ".jpeg": self._actions.VTK2DLoaderSetWidget,
        }

class ActionsVTK:
    def __init__(self):
        #self.container: Optional[VTK2DHandles] = None
        #self._vtk_img2d: Optional[vtk.vtkImageData] = None

        # Segmentación (se crean al habilitar)
        #self._overlay: Optional[VTK2DOverlayBase] = None
        #self._driver: Optional[ManualVoxelSeg2DController] = None

        # Parámetros (ajústalos si quieres)
        #self.spacing_xy = (1.0, 1.0)
        #self.origin_xy = (0.0, 0.0)
        pass

    def VTK2DLoaderSetWidget(self, host, path: str):
        vtk_img = VTKImages2DLoader().load(path)

        win_container = host.findChild(QtWidgets.QWidget, "widgetMain2DViewer")
        if win_container is None:
            raise RuntimeError('No existe widgetMain2DViewer en el host.')

        layout = win_container.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(win_container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        # Clean VTK widget
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

        self.vtk_container = VTK2DHandles(
            image = vtk_img,
            widget=vtk_widget,
            renwin=rw,
            renderer=ren,
            interactor=iren,
            actor=actor,
        )
        
        # Reset segmentación (si cambiaste de imagen)
        #self._overlay = None
        #self._driver = None

    def enable_manual_segmentation(self):
        if not hasattr(self, "vtk_container"):
            raise RuntimeError(
                "Before enabling segmentation, an image must be loaded. "
                "Use (File > Open)."
            )
        VTKImage2DTracerFrontend().bind(self.vtk_container)
        
