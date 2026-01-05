from PyQt5 import QtWidgets, uic
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from vxgyrus.presentation.qt.dialogs import DialogsPyQt5

class App(QtWidgets.QMainWindow):
    def __init__(self, ui_path: str):
        super().__init__()
        uic.loadUi(ui_path, self) 

        #self.host = self.findChild(QtWidgets.QWidget, "widgetMain2DViewer")
        self.host = self.findChild(QtWidgets.QWidget, "widget")

        layout = self.host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        
        self.dialogs = DialogsPyQt5(self)