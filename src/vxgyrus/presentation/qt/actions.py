from PyQt5 import QtWidgets

class ActionsPyQt5:
    def __init__(self, win):
        self.win = win
    
    def on_open(self, path):
        print(f"Selected file: {path}")
        return path

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

    def load_image(self, path: str):
        r = vtk.vtkImageReader2Factory().CreateImageReader2(path)
        r.SetFileName(path)
        r.Update()
        self.actor.SetInputData(r.GetOutput())
        self.ren.ResetCamera()
        self.rw.Render()