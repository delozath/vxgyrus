from PyQt5 import QtWidgets, uic

from vxgyrus.presentation.qt.dialogs import DialogsPyQt5
from vxgyrus.presentation.qt.tools_window import SegmentationToolsWindow

class App(QtWidgets.QMainWindow):
    def __init__(self, ui_path: str):
        super().__init__()
        uic.loadUi(ui_path, self) 

        #main window
        self._setup_main_viewer_layout()

        #tools window: segmentation
        self.tools_window = SegmentationToolsWindow(self)
        self.tools_window.show()
        
        self.dialogs = DialogsPyQt5(self)

    def _setup_main_viewer_layout(self):
        central = self.findChild(QtWidgets.QWidget, "centralwidget")
        viewer = self.findChild(QtWidgets.QWidget, "widgetMain2DViewer")
        if central is None or viewer is None:
            return

        layout = central.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(central)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        if viewer.parent() is not central:
            viewer.setParent(central)

        if layout.indexOf(viewer) == -1:
            layout.addWidget(viewer)

    