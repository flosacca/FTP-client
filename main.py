import sys
import re
from socket import *
from PyQt5 import uic
from PyQt5.QtWidgets import *


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        uic.loadUi('window.ui', self)
        self.host = self.findChild(QLineEdit, 'host')
        self.port = self.findChild(QLineEdit, 'port')
        self.username = self.findChild(QLineEdit, 'username')
        self.password = self.findChild(QLineEdit, 'password')
        self.login = self.findChild(QPushButton, 'login')

        self.host.setText('59.66.136.21')
        self.username.setText('ssast')
        self.password.setText('ssast')

        self.login.clicked.connect(self.loginClicked)

    def loginClicked(self):
        host = self.host.text()
        port = int(self.port.text())
        client = socket(AF_INET, SOCK_STREAM)
        client.connect((host, port))
        message = client.recv(4096).decode()
        sys.stdout.write(message)
        assert re.match(r'220\b', message)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
