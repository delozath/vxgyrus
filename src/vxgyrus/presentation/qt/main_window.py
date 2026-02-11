from PyQt5 import QtWidgets, uic
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from vxgyrus.presentation.qt.dialogs import DialogsPyQt5

class App(QtWidgets.QMainWindow):
    def __init__(self, ui_path: str):
        super().__init__()
        uic.loadUi(ui_path, self) 
        
        self.dialogs = DialogsPyQt5(self)