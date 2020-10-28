import sys
import re
from socket import *

from ftpparser import FTPParser

from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from files_model import *

BUFFER_SIZE = 4096


def print_error(e):
    sys.stdout.write(type(e).__name__)
    if str(e):
        sys.stdout.write(f': {str(e)}')
    sys.stdout.write('\n')


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sess = None
        uic.loadUi('window.ui', self)

        self.index.setFocus()
        self.index.setModel(FilesModel())
        header = self.index.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.index.setColumnWidth(1, 100)
        self.index.setColumnWidth(2, 180)

        self.buttonLogin.clicked.connect(self.loginClicked)

        self.host.setText('199.255.99.141')
        self.username.setText('cat')
        self.password.setText('cat')

    def send(self, msg):
        msg += '\r\n'
        sys.stdout.write(msg)
        self.sess.sendall(msg.encode())

    def recv(self):
        msg = b''
        while True:
            msg += self.sess.recv(BUFFER_SIZE)
            if msg[-1] == 10:
                break
        msg = msg.decode()
        sys.stdout.write(msg)
        code = int(msg.splitlines()[-1].split()[0])
        assert code in range(100, 400)
        return msg

    def login(self):
        host = self.host.text()
        port = int(self.port.text())
        self.sess = socket(AF_INET, SOCK_STREAM)
        self.sess.connect((host, port))
        try:
            self.recv()
            self.send(f'USER {self.username.text()}')
            self.recv()
            self.send(f'PASS {self.password.text()}')
            self.recv()
            self.send('TYPE I')
            self.recv()
        except Exception as e:
            self.sess.close()
            self.sess = None
            raise

    def transfer(self, req, callback):
        if not self.actionPassive.isChecked():
            server = socket(AF_INET, SOCK_STREAM)
            server.bind(('', 0))
            server.listen(5)
            try:
                host = self.sess.getsockname()[0]
                port = server.getsockname()[1]
                self.send('PORT {},{},{}'.format(host.replace('.', ','), port >> 8, port & 255))
                self.recv()
                self.send(req)
                self.recv()
                data = server.accept()[0]
                try:
                    callback(data)
                finally:
                    data.close()
            finally:
                server.close()
        else:
            self.send('PASV')
            addr = re.findall(r'\b\d+(?:,\d+){5}\b', self.recv())[0]
            addr = tuple(map(int, addr.split(',')))
            host = '.'.join(map(str, addr[:4]))
            port = addr[4] << 8 | addr[5]
            data = socket(AF_INET, SOCK_STREAM)
            data.connect((host, port))
            try:
                self.send(req)
                self.recv()
                callback(data)
            finally:
                data.close()
        self.recv()

    def recvList(self, data):
        msg = b''
        while True:
            res = data.recv(BUFFER_SIZE)
            msg += res
            if len(res) < BUFFER_SIZE:
                break
        try:
            msg = msg.decode()
        except ValueError:
            msg = msg.decode(encoding='latin1')
        self.index.setModel(FilesModel(FTPParser().parse(msg.splitlines())))

    def loginClicked(self):
        try:
            self.index.setModel(FilesModel())
            self.login()
            self.transfer('LIST', self.recvList)
        except Exception as e:
            print_error(e)
            QMessageBox.critical(self, 'Error', 'Login failed.')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
