import json
import os
import shutil
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
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .graphics_view import GraphicsView
from .segmentation import SegmentationModel


class MainWindow(QMainWindow):
    brush_feedback = pyqtSignal(int)  # allows QSlider react on mouse wheel
    sam_signal = pyqtSignal(bool)  # used to propagate sam mode to all widgets

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Image segmentation annotation tool")
        self.resize(1000, 1400)

        top_work_dir = Path("work")
        workdir = os.environ["WORKSET"]
        segmentation_model_path = os.environ["SEGMENTATION_MODEL"]

        self._workdir = top_work_dir / workdir
        self._class_dir = top_work_dir / "classes.json"
        self._image_dir = self._workdir / "images"
        self._label_dir = self._workdir / "labels"
        self._sam_dir = self._workdir / "sam"
        self._label_dir.mkdir(exist_ok=True)

        with open(self._class_dir, "r") as f:
            self._classes = json.loads("".join(f.readlines()))["classes"]
        ids = [c["id"] for c in self._classes]
        colors = [c["color"] for c in self._classes]
        self._id2color = {k: v for k, v in zip(ids, colors)}

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

        self.ls_label_value = QLabel()
        self.ls_label_value.setText("Label opacity: 50%")

        self.ls_label_slider = QSlider()
        self.ls_label_slider.setOrientation(Qt.Orientation.Horizontal)
        self.ls_label_slider.setMinimum(0)
        self.ls_label_slider.setMaximum(100)
        self.ls_label_slider.setSliderPosition(50)
        self.ls_label_slider.valueChanged.connect(self.on_ls_label_slider_change)

        self.ls_sam_value = QLabel()
        self.ls_sam_value.setText("SAM opacity: 0%")

        self.ls_sam_slider = QSlider()
        self.ls_sam_slider.setOrientation(Qt.Orientation.Horizontal)
        self.ls_sam_slider.setMinimum(0)
        self.ls_sam_slider.setMaximum(100)
        self.ls_sam_slider.setSliderPosition(0)
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

        self.bs_value = QLabel()
        self.bs_value.setText("Size: 50 px")

        self.bs_slider = QSlider()
        self.bs_slider.setOrientation(Qt.Orientation.Horizontal)
        self.bs_slider.setMinimum(1)
        self.bs_slider.setMaximum(150)
        self.bs_slider.setSliderPosition(50)
        self.bs_slider.valueChanged.connect(self.on_bs_slider_change)

        bs_vlay = QVBoxLayout(bs_group)
        bs_vlay.addWidget(self.bs_value)
        bs_vlay.addWidget(self.bs_slider)

        # Classs selection group
        cs_group = QGroupBox(self.tr("Classes"))

        self.cs_list = QListWidget()
        for i, c in enumerate(self._classes):
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

        nav_hlay = QHBoxLayout(nav_group)
        nav_hlay.addWidget(self.prev_button)
        nav_hlay.addWidget(self.next_button)

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

        # self._curr_id = 0
        self._graphics_view.set_brush_color(QColor(colors[0]))
        self.cs_list.setCurrentRow(0)

        self._undo_history_dir = top_work_dir / "undo_history"
        self._undo_history_dir.mkdir(exist_ok=True)
        self._curr_undo_index = 0

        self._reset_undo_history()  # 初回起動時に履歴をリセット

        self.segmentation_model = (
            SegmentationModel(segmentation_model_path)
            if segmentation_model_path
            else None
        )

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
        curr_label_path = self._label_dir / (self._current_image_path.stem + ".png")
        self._graphics_view.save_label_to(curr_label_path)

    def save_undo_state(self):
        """現在のラベル状態を番号付きファイル名で保存"""
        self._curr_undo_index += 1
        undo_file = self._undo_history_dir / f"undo_{self._curr_undo_index}.png"
        self._graphics_view.save_label_to(undo_file)

    def undo(self):
        """Undo操作を実行"""
        print("Undo operation triggered", self._curr_undo_index)
        if self._curr_undo_index > 0:
            self._curr_undo_index -= 1
            undo_file = self._undo_history_dir / f"undo_{self._curr_undo_index}.png"
            if undo_file.exists():
                self._update_label(undo_file)

    def redo(self):
        """Redo操作を実行"""
        redo_file = self._undo_history_dir / f"undo_{self._curr_undo_index + 1}.png"
        if redo_file.exists():
            self._curr_undo_index += 1
            self._update_label(redo_file)

    def _reset_undo_history(self):
        """履歴をリセット"""
        if self._undo_history_dir.exists():
            shutil.rmtree(self._undo_history_dir)
        self._undo_history_dir.mkdir(exist_ok=True)
        self._curr_undo_index = -1

        # 初期状態のラベルを保存
        self.save_undo_state()

    def _load_sample(
        self,
        image_path: Path,
        label_path: Path | None = None,
        fit: bool = True,
    ):
        self._current_image_path = image_path
        name = self._current_image_path.stem + ".png"

        if label_path is None:
            label_path = self._label_dir / name

        sam_path = self._sam_dir / name
        self._graphics_view.load_sample(
            self._current_image_path, label_path, sam_path, fit=fit
        )
        self.ds_label.setText(f"{name[:30]}")

    def _update_label(self, label_path: Path):
        self._graphics_view.update_label(label_path)

    def _get_sorted_images(self):
        """画像ディレクトリ内の画像を更新日時順にソートして取得"""
        return sorted(self._image_dir.iterdir(), key=lambda p: p.stat().st_mtime)

    def load_latest_sample(self):
        images = self._get_sorted_images()
        self._load_sample(images[-1])  # 最新の画像を読み込む

    def _switch_sample_by(self, step: int):
        """画像を切り替える処理"""
        if step == 0:
            return

        images = self._get_sorted_images()
        try:
            current_index = images.index(self._current_image_path)
        except ValueError:
            current_index = 0

        new_index = (current_index + step) % len(images)
        new_image_path = images[new_index]

        self.save_current_label()
        self._load_sample(new_image_path)
        self._reset_undo_history()

    def keyPressEvent(self, a0: QKeyEvent) -> None:
        if a0.key() == Qt.Key.Key_Space:
            self._graphics_view.reset_zoom()
        elif a0.key() == Qt.Key.Key_S:
            self.sam_checkbox.toggle()
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
        elif a0.key() == Qt.Key.Key_E:
            self.cs_list.clearSelection()
            self._graphics_view.set_eraser(True)
            self.sam_checkbox.setChecked(False)  # SAM自動オフ
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

    def on_sam_run_clicked(self):
        if self.segmentation_model is None:
            QMessageBox.warning(
                self,
                "No Segmentation Model",
                "Segmentation model is not set. Please provide a valid model path.",
            )
            return
        print("SAM run button clicked")

        sam_path = self._sam_dir / (self._current_image_path.stem + ".png")
        self.segmentation_model.segment_image(self._current_image_path, sam_path)
        self._graphics_view.update_sam(sam_path)
