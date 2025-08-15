from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QCloseEvent, QColor, QIcon, QKeyEvent, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QShortcut,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .data_store import DataStore
from .ui.graphics_view import GraphicsView


class MainWindow(QMainWindow):
    brush_feedback = pyqtSignal(int)  # allows QSlider react on mouse wheel
    sam_signal = pyqtSignal(bool)  # used to propagate sam mode to all widgets

    def __init__(self, data_store: DataStore):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Image segmentation annotation tool")
        self.resize(1000, 1400)

        self._data_store = data_store
        self._id2color = self._data_store.load_id2color()

        self.brush_feedback.connect(self.on_brush_size_change)
        self._graphics_view = GraphicsView(
            brush_feedback=self.brush_feedback,
            parent=self,
            undo_callback=self.save_undo_state,
        )
        self.sam_signal.connect(self._graphics_view.handle_sam_signal)

        # Dataset group
        ds_group = QGroupBox(self.tr("Dataset"))

        self.ds_label = QLabel()
        self.ds_label.setText("Sample: 000000.png")

        ds_vlay = QVBoxLayout(ds_group)
        ds_vlay.addWidget(self.ds_label)

        # Layers group
        ls_group = QGroupBox(self.tr("Layers"))

        default_label_opacity = 50
        self.ls_label_value = QLabel()
        self.ls_label_value.setText(f"Label opacity: {default_label_opacity}%")
        self.ls_label_slider = QSlider()
        self.ls_label_slider.setOrientation(Qt.Orientation.Horizontal)
        self.ls_label_slider.setMinimum(0)
        self.ls_label_slider.setMaximum(100)
        self.ls_label_slider.setSliderPosition(default_label_opacity)
        self.ls_label_slider.valueChanged.connect(self.on_ls_label_slider_change)

        default_sam_opacity = 0
        self.ls_sam_value = QLabel()
        self.ls_sam_value.setText(f"SAM opacity: {default_sam_opacity}%")
        self.ls_sam_slider = QSlider()
        self.ls_sam_slider.setOrientation(Qt.Orientation.Horizontal)
        self.ls_sam_slider.setMinimum(0)
        self.ls_sam_slider.setMaximum(100)
        self.ls_sam_slider.setSliderPosition(default_label_opacity)
        self.ls_sam_slider.valueChanged.connect(self.on_ls_sam_slider_change)

        ls_vlay = QVBoxLayout(ls_group)
        ls_vlay.addWidget(self.ls_label_value)
        ls_vlay.addWidget(self.ls_label_slider)
        ls_vlay.addWidget(self.ls_sam_value)
        ls_vlay.addWidget(self.ls_sam_slider)

        # SAM group
        sam_group = QGroupBox(self.tr("SAM"))

        self.sam_checkbox = QCheckBox("SAM assistance")
        self.sam_checkbox.stateChanged.connect(self.on_sam_change)
        self.sam_run_button = QPushButton("Run SAM")
        self.sam_run_button.clicked.connect(self.on_sam_run_clicked)

        sam_vlay = QVBoxLayout(sam_group)
        sam_vlay.addWidget(self.sam_checkbox)
        sam_vlay.addWidget(self.sam_run_button)

        # Brush size group
        bs_group = QGroupBox(self.tr("Brush"))

        default_bs_size = 50
        self.bs_value = QLabel()
        self.bs_value.setText(f"Size: {default_bs_size} px")
        self.bs_slider = QSlider()
        self.bs_slider.setOrientation(Qt.Orientation.Horizontal)
        self.bs_slider.setMinimum(1)
        self.bs_slider.setMaximum(150)
        self.bs_slider.setSliderPosition(default_bs_size)
        self.bs_slider.valueChanged.connect(self.on_bs_slider_change)

        bs_vlay = QVBoxLayout(bs_group)
        bs_vlay.addWidget(self.bs_value)
        bs_vlay.addWidget(self.bs_slider)

        # Classs selection group
        cs_group = QGroupBox(self.tr("Classes"))

        self.cs_list = QListWidget()
        for i, c in enumerate(self._data_store.classes):
            color = QColor(c["color"])
            pixmap = QPixmap(20, 20)
            pixmap.fill(color)
            text = f"[{i + 1}] {c['name']}"
            item = QListWidgetItem(QIcon(pixmap), text)
            self.cs_list.addItem(item)
        self.cs_list.itemClicked.connect(self.on_item_clicked)

        cs_vlay = QVBoxLayout(cs_group)
        cs_vlay.addWidget(self.cs_list)

        # Navigation group
        nav_group = QGroupBox(self.tr("Navigation"))

        self.prev_button = QPushButton("prev")
        self.prev_button.clicked.connect(lambda: self._switch_sample_by(-1))

        self.next_button = QPushButton("next")
        self.next_button.clicked.connect(lambda: self._switch_sample_by(1))

        self.accept_button = QPushButton("accept")
        self.accept_button.clicked.connect(lambda: self._accept_annotation())

        nav_hlay = QHBoxLayout(nav_group)
        nav_hlay.addWidget(self.prev_button)
        nav_hlay.addWidget(self.next_button)
        nav_hlay.addWidget(self.accept_button)

        vlay = QVBoxLayout()
        vlay.addWidget(ds_group)
        vlay.addWidget(sam_group)
        vlay.addWidget(ls_group)
        vlay.addWidget(bs_group)
        vlay.addWidget(cs_group)
        vlay.addWidget(nav_group)
        vlay.addStretch()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        lay = QHBoxLayout(central_widget)
        lay.addWidget(self._graphics_view, stretch=1)
        lay.addLayout(vlay, stretch=0)

        # ツールバーの作成
        toolbar = self.addToolBar("Tools")

        # 拡大ボタン
        zoom_in_action = toolbar.addAction("Zoom In")
        zoom_in_action.triggered.connect(lambda: self._graphics_view.scale(1.25, 1.25))

        # 縮小ボタン
        zoom_out_action = toolbar.addAction("Zoom Out")
        zoom_out_action.triggered.connect(lambda: self._graphics_view.scale(0.8, 0.8))

        # S/EキーでSAM・消しゴム切替のグローバルショートカット
        self._sam_shortcut = QShortcut(QKeySequence("S"), self)
        self._sam_shortcut.activated.connect(self.sam_checkbox.toggle)

        self._eraser_shortcut = QShortcut(QKeySequence("E"), self)
        self._eraser_shortcut.activated.connect(self._activate_eraser_mode)

        self._graphics_view.set_brush_color(QColor(self._id2color[1]))
        self.cs_list.setCurrentRow(0)

        self._reset_undo_history()

    @pyqtSlot(int)
    def on_sam_change(self, state: int):
        if state == Qt.CheckState.Checked:
            self.sam_signal.emit(True)
        elif state == Qt.CheckState.Unchecked:
            self.sam_signal.emit(False)
        else:
            print("unsupported check state")

    @pyqtSlot(int)
    def on_ls_label_slider_change(self, value: int):
        self.ls_label_value.setText(f"Label opacity: {value}%")
        self._graphics_view.set_label_opacity(value)

    @pyqtSlot(int)
    def on_ls_sam_slider_change(self, value: int):
        self.ls_sam_value.setText(f"SAM opacity: {value}%")
        self._graphics_view.set_sam_opacity(value)

    @pyqtSlot(int)
    def on_bs_slider_change(self, value: int):
        self.bs_value.setText(f"Size: {value} px")
        self._graphics_view.set_brush_size(value)

    @pyqtSlot(int)
    def on_brush_size_change(self, value: int):
        # updates slider and value label on brush size change via mouse wheel
        self.bs_value.setText(f"Size: {value} px")
        self.bs_slider.setSliderPosition(value)

    def on_item_clicked(self, item: QListWidgetItem):
        idx = self.sender().currentRow()
        color = self._id2color[idx + 1]
        self._graphics_view.set_brush_color(QColor(color))

    def save_current_label(self):
        self._graphics_view.save_label_to(self._data_store.get_current_label_path())

    def accept_current_label(self):
        self._data_store.transfer_image_to_accept(
            label_saver=self._graphics_view.save_label_to
        )

    def save_undo_state(self):
        undo_file = self._data_store.save_undo_state()
        self._graphics_view.save_label_to(undo_file)

    def undo(self):
        undo_file = self._data_store.undo()
        if undo_file:
            self._update_label(undo_file)

    def redo(self):
        redo_file = self._data_store.redo()
        if redo_file:
            self._update_label(redo_file)

    def _reset_undo_history(self):
        self._data_store.reset_undo_history()
        self.save_undo_state()

    def _load_sample(self, image_path: Path, fit: bool = True):
        self._data_store.current_image_path = image_path
        name = image_path.stem + ".png"
        label_path = self._data_store.label_dir / name
        sam_path = self._data_store.sam_dir / name
        self._graphics_view.load_sample(image_path, label_path, sam_path, fit=fit)
        self.ds_label.setText(f"{name[:30]}")

    def _update_label(self, label_path: Path):
        self._graphics_view.update_label(label_path)

    def load_latest_sample(self):
        images = self._data_store.get_sorted_images()
        self._load_sample(images[-1])  # 最新の画像を読み込む

    def _switch_sample_by(self, step: int):
        """画像を切り替える処理"""
        if step == 0:
            return

        images = self._data_store.get_sorted_images()
        try:
            current_index = images.index(self._data_store.current_image_path)
        except ValueError:
            current_index = 0

        new_index = (current_index + step) % len(images)
        new_image_path = images[new_index]

        self.save_current_label()
        self._load_sample(new_image_path)
        self._data_store.reset_undo_history()

    def _accept_annotation(self):
        self.accept_current_label()

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        if a0.key() == Qt.Key.Key_Space:
            self._graphics_view.reset_zoom()
        elif a0.key() == Qt.Key.Key_C:
            reply = QMessageBox.question(
                self,
                "Confirm",
                "Are you sure you want to clear all?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._graphics_view.clear_label()
        elif a0.key() in range(49, 58):
            num_key = int(a0.key()) - 48
            color = self._id2color.get(num_key)
            if color:
                self._graphics_view.set_brush_color(QColor(color))
                self.cs_list.setCurrentRow(num_key - 1)

        elif a0.key() in [Qt.Key.Key_Comma, Qt.Key.Key_Left]:
            self._switch_sample_by(-1)
        elif a0.key() in [Qt.Key.Key_Period, Qt.Key.Key_Right]:
            self._switch_sample_by(1)

        elif a0.matches(QKeySequence.Undo):
            self.undo()
        elif a0.matches(QKeySequence.Redo):
            self.redo()

        return super().keyPressEvent(a0)

    def closeEvent(self, a0: QCloseEvent) -> None:
        self.save_current_label()
        return super().closeEvent(a0)

    def _activate_eraser_mode(self):
        self.cs_list.clearSelection()
        self._graphics_view.set_eraser(True)
        self.sam_checkbox.setChecked(False)  # SAM自動オフ

    def on_sam_run_clicked(self):
        print("SAM run button clicked")
        try:
            sam_path = self._data_store.run_sam()
            self._graphics_view.update_sam(sam_path)
        except Exception:
            QMessageBox.warning(
                self,
                "No Segmentation Model",
                "Segmentation model is not set. Please provide a valid model path.",
            )
