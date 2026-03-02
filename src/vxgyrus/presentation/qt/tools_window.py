from PyQt5 import QtCore, QtWidgets


class SegmentationToolsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Segmentation Tools")
        self.setWindowFlag(QtCore.Qt.WindowType.Tool, True)
        self.setMinimumWidth(260)
        self._build_ui()

    def _build_ui(self):
        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        group = QtWidgets.QGroupBox("Image Segmentation")
        form = QtWidgets.QFormLayout(group)

        self.combo_tool = QtWidgets.QComboBox()
        self.combo_tool.addItems(["Brush", "Eraser"])

        self.slider_brush_size = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_brush_size.setRange(1, 100)
        self.slider_brush_size.setValue(20)

        self.label_brush_size = QtWidgets.QLabel("20 px")
        self.slider_brush_size.valueChanged.connect(
            lambda v: self.label_brush_size.setText(f"{v} px")
        )

        brush_size_layout = QtWidgets.QHBoxLayout()
        brush_size_layout.addWidget(self.slider_brush_size)
        brush_size_layout.addWidget(self.label_brush_size)

        self.button_apply = QtWidgets.QPushButton("Apply Stroke")
        self.enable_magnetic_segmentation = QtWidgets.QPushButton("Enable Segmentation")

        form.addRow("Tool", self.combo_tool)
        form.addRow("Brush size", brush_size_layout)
        form.addRow(self.button_apply)
        form.addRow(self.enable_magnetic_segmentation)

        root_layout.addWidget(group)
        root_layout.addStretch(1)
