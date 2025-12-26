import sys
import vtk
from PyQt5 import QtWidgets, uic
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


class App(QtWidgets.QMainWindow):
    def __init__(self, ui_path: str):
        super().__init__()
        uic.loadUi(ui_path, self)  # carga testing.ui dentro de ESTE QMainWindow

        #self.host = self.findChild(QtWidgets.QWidget, "widgetMain2DViewer")
        self.host = self.findChild(QtWidgets.QWidget, "widget")

        layout = self.host.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.host)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

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


def main():
    app = QtWidgets.QApplication(sys.argv)

    win = App("./vxgyrus/application/testing.ui")

    img, _ = QtWidgets.QFileDialog.getOpenFileName(
        win, "Open image", "",
        "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp);;All (*.*)"
    )
    if img:
        win.show()
        win.load_image(img)
    else:
        win.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
