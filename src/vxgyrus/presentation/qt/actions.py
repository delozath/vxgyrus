import vtk

from pathlib import Path

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PyQt5 import QtWidgets

class ActionsPyQt5:
    def __init__(self, host):
        self.host = host
        self._connect()
    
    def on_open(self, path):
        ext = Path(path).suffix
        #print(f"Selected file: {path}")
        data = self._loaders[ext]().load(self.host, path)
        #print(f"Data loaded: {data}")
        return data
    
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

        # limpiar el contenedor (para no apilar widgets)
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        
        vtk_widget = QVTKRenderWindowInteractor(host)
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


class Temp():
    def tmp(self, layout):
        self.vtk_widget = QVTKRenderWindowInteractor(self.host)
        layout.addWidget(self.vtk_widget)

        self.rw = self.vtk_widget.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.rw.AddRenderer(self.ren)

        self.actor = vtk.vtkImageActor()
        self.ren.AddActor(self.actor)

        self.vtk_widget.Initialize()

