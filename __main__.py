import sys

from dotenv import load_dotenv
from PyQt5.QtWidgets import QApplication

from src.data_store import DataStore
from src.main_window import MainWindow

if __name__ == "__main__":
    load_dotenv()

    app = QApplication(sys.argv)
    mw = MainWindow(DataStore())
    mw.show()
    mw.load_latest_sample()
    sys.exit(app.exec_())
