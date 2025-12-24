from abc import ABC, abstractmethod


import vtk


class BaseVTK2DFileHandler(ABC):
    pfname: str

    @abstractmethod
    def load(self):
        ...

    def build(self):
        img = self.load()
        actor = vtk.vtkImageActor()
        actor.SetInputData(img)
        return actor