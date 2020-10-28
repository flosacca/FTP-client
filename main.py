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

        self.files.setFocus()
        self.files.setModel(FilesModel())
        header = self.files.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.files.setColumnWidth(1, 100)
        self.files.setColumnWidth(2, 180)

        self.buttonLogin.clicked.connect(self.loginClicked)
        self.files.clicked.connect(self.setItemName)
        self.files.doubleClicked.connect(self.access)
        self.buttonChdir.clicked.connect(self.chdir)
        self.buttonMkdir.clicked.connect(self.mkdir)
        self.buttonRmdir.clicked.connect(self.rmdir)
        self.buttonRename.clicked.connect(self.rename)

        self.host.setText('199.255.99.141')
        self.username.setText('cat')
        self.password.setText('cat')

    def setItemName(self, index):
        self.itemName.setText(self.files.model()[index.row(), 0])

    def access(self, index):
        model = self.files.model()
        name = model[index.row(), 0]
        isdir = model[index.row(), 3]
        if isdir:
            self.chdir(name)
        else:
            pass

    def chdir(self, name=None):
        if name is None:
            name = self.itemName.text()
        try:
            if name == '..':
                self.send('CDUP')
            else:
                self.send(f'CWD {name}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to enter folder.')

    def mkdir(self):
        try:
            self.send(f'MKD {self.itemName.text()}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to create folder.')

    def rmdir(self):
        try:
            self.send(f'RMD {self.itemName.text()}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to remove folder.')

    def rename(self):
        try:
            self.send(f'RNFR {self.itemName.text()}')
            self.recv()
            self.send(f'RNTO {self.newName.text()}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to rename item.')

    def loginClicked(self):
        self.files.setModel(FilesModel())
        try:
            self.login()
            self.transfer('LIST', self.recvList)
        except Exception as e:
            print_error(e)
            QMessageBox.critical(self, 'Error', 'Login failed.')

    def send(self, msg):
        msg += '\r\n'
        sys.stdout.write(msg)
        self.sess.sendall(msg.encode())

    def recv(self):
        lines = []
        while True:
            msg = b''
            while True:
                msg += self.sess.recv(BUFFER_SIZE)
                if msg[-1] == 10:
                    break
            msg = msg.decode()
            sys.stdout.write(msg)
            lines.extend(msg.splitlines())
            if re.search(r'^\d{3} ', lines[-1]):
                break
        code = int(lines[-1].split()[0])
        assert code in range(100, 400)
        return lines[-1]

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
        self.files.setModel(FilesModel(FTPParser().parse(msg.splitlines())))
        self.itemName.setText('')
        self.newName.setText('')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
