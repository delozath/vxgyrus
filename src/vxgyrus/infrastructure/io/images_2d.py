import vtk
from PyQt5 import QtWidgets
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class VTKImages2DLoader:
    def load(self, path: str):
        reader = vtk.vtkImageReader2Factory().CreateImageReader2(path)
        if reader is None:
            raise RuntimeError(f"VTK no pudo crear reader para: {path}")
        reader.SetFileName(path)
        reader.Update()

        vtk_img = reader.GetOutput()

        return vtk_img
