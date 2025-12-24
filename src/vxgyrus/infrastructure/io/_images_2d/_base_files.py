import vtk

#from typing import override

from .base import BaseVTK2DFileHandler

class PNGFileHandler(BaseVTK2DFileHandler):
    def __init__(self, pfname):
        self.pfname = pfname

    #@override
    def load(self):
        reader = vtk.vtkPNGReader()
        reader.SetFileName(self.pfname)
        reader.Update()
        return reader.GetOutput()


class JPEGFileHandler(BaseVTK2DFileHandler):
    def __init__(self, pfname):
        self.pfname = pfname

    #@override
    def load(self):
        reader = vtk.vtkJPEGReader()
        reader.SetFileName(self.pfname)
        reader.Update()
        return reader.GetOutput()

