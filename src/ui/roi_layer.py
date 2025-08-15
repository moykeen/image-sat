from PyQt5.QtCore import QPoint, QRectF, Qt
from PyQt5.QtGui import QPen, QPixmap
from PyQt5.QtWidgets import QGraphicsRectItem


class RoiLayer(QGraphicsRectItem):
    def __init__(self, parent):
        super().__init__(parent)
        self.setOpacity(0.2)
        self.setPen(QPen(Qt.PenStyle.NoPen))

        self._pixmap = QPixmap()
        self._img = None  # QImage to fetch color from
        self._np_img = None  # np array for fast pixels fetch

    def set_image(self, path: str):
        r = self.parentItem().pixmap().rect()
        self.setRect(QRectF(r))
        self._pixmap.load(path)
        self._update_img()

    def _update_img(self):
        image = self._pixmap.toImage()
        buffer = image.bits()
        buffer.setsize(image.byteCount())
        # np_img = np.frombuffer(buffer, dtype=np.uint8)
        # np_img = np_img.reshape((image.height(), image.width(), 4))
        self._img = image
        # self._np_img = np_img

    def clear(self):
        r = self.parentItem().pixmap().rect()
        self.setRect(QRectF(r))
        self._pixmap = QPixmap(r.size())
        self._pixmap.fill(Qt.GlobalColor.transparent)
        self.update()  # to make changes be visible instantly

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        painter.save()
        painter.drawPixmap(QPoint(), self._pixmap)
        painter.restore()
