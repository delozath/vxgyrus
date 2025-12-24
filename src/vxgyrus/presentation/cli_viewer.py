    
import vtk

class SceneViewer:
    def __init__(self, actor: vtk.vtkActor):
        self.actor = actor

    def start(self):
        ren = vtk.vtkRenderer()
        ren.AddActor(self.actor)
        ren.ResetCamera()

        rw = vtk.vtkRenderWindow()
        rw.AddRenderer(ren)
        rw.SetSize(1000, 800)

        iren = vtk.vtkRenderWindowInteractor()
        iren.SetRenderWindow(rw)

        rw.Render()
        iren.Start()