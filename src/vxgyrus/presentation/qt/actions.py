import vtk

from pathlib import Path

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5 import QtCore, QtWidgets

class ActionsPyQt5:
    def __init__(self, host):
        self.host = host
        self._connect()
    
    def on_open(self, path):
        ext = Path(path).suffix
        #print(f"Selected file: {path}")
        data = self._loaders[ext]().load(self.host, path)
        self.on_main_window_resize()
        QtCore.QTimer.singleShot(0, self.on_main_window_resize)
        #print(f"Data loaded: {data}")
        return data

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
            ".png": ActionsVTK,
            ".jpg": ActionsVTK,
            ".jpeg": ActionsVTK
        }


class ActionsVTK:
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
        return render.GetOutput()
