import sys
import vtk

from PyQt5 import QtWidgets
from vxgyrus.presentation.qt.main_window import App



def main():
    app = QtWidgets.QApplication(sys.argv)

    win = App("./vxgyrus/application/testing.ui")
    win.show()
    """
    img, _ = QtWidgets.QFileDialog.getOpenFileName(
        win, "Open image", "",
        "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All (*.*)"
    )
    if img:
        win.show()
        win.load_image(img)
    else:
        win.show()
    """
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
