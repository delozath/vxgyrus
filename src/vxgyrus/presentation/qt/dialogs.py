from PyQt5 import QtWidgets

from vxgyrus.presentation.qt.actions import ActionsPyQt5

class DialogsPyQt5:
    def __init__(self, win):
        self.win = win
        self.win.actionOpen.triggered.connect(self.on_open)
        print(self.win.__dict__)
        if hasattr(self.win, "tools_window") and hasattr(self.win.tools_window, "enable_segmentation"):
            self.win.tools_window.enable_segmentation.clicked.connect(
                self.on_enable_manual_segmentation
            )
        
        self.actions = ActionsPyQt5(win)
    
    def on_open(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.win,
            "Open file",
            "",
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All (*.*)"
        )

        self.actions.on_open(path)
        return path

    def on_enable_manual_segmentation(self):
        self.actions.manual_segmentation()