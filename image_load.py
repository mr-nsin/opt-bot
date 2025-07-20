import sys
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QFrame


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Image in Frame')
        self.setGeometry(100, 100, 400, 400)

        # Create a frame
        frame = QFrame(self)
        frame.setGeometry(50, 50, 300, 300)
        frame.setStyleSheet("QFrame { background-color: #CCCCCC }")

        # Load the image
        image_path = "C:/Users/Administrator/Desktop/BOT_Cris/test-img/Level Up (White _ Gold Transparent).png"  # Replace with the actual image path
        pixmap = QPixmap(image_path)

        # Create a label and set the image pixmap
        label = QLabel(frame)
        label.setPixmap(pixmap)
        label.setGeometry(50, 50, 200, 200)

        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
