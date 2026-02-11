import vtk

from pathlib import Path

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class ActionsPyQt5:
    def __init__(self, win):
        self.host = win
        self._connect()
    
    def on_open(self, path):
        ext = Path(path).suffix
        #print(f"Selected file: {path}")
        data = self._loaders[ext]().load(self, path)
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
        reader = vtk.vtkImageReader2Factory().CreateImageReader2(path)
        reader.SetFileName(path)
        reader.Update()

        layout = host.host.layout()
        print(f"{layout}")

        self.vtk_widget = QVTKRenderWindowInteractor(host.host)
        layout.addWidget(self.vtk_widget)

        self.rw = self.vtk_widget.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.rw.AddRenderer(self.ren)

        self.actor = vtk.vtkImageActor()
        self.ren.AddActor(self.actor)

        self.vtk_widget.Initialize()

        self.actor.GetMapper().SetInputConnection(reader.GetOutputPort())
        
        self.ren.ResetCamera()
        self.rw.Render()


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

