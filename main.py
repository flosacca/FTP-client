import sys
import re
from socket import *

from ftpparser import FTPParser

from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from files_model import *


def print_error(e):
    print(f'{type(e).__name__}: {str(e)}')


def ftpsend(client, msg):
    msg += '\r\n'
    sys.stdout.write(msg)
    client.sendall(msg.encode())


def ftprecv(client):
    msg = b''
    n = 4096
    while True:
        res = client.recv(n)
        msg += res
        if len(res) < n:
            break
    try:
        msg = msg.decode()
    except ValueError:
        msg = msg.decode(encoding='latin1')
    sys.stdout.write(msg)
    return msg


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
        ftpsend(self.sess, msg)

    def recv(self):
        msg = ftprecv(self.sess)
        code = msg.splitlines()[-1].split()[0]
        assert int(code[0]) in range(1, 4)
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
            print_error(e)
            print('login failed')
            self.sess.close()
            self.sess = None

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
        self.index.setModel(FilesModel(FTPParser().parse(ftprecv(data).splitlines())))

    def loginClicked(self):
        try:
            self.login()
            self.transfer('LIST', self.recvList)
        except Exception as e:
            print_error(e)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
