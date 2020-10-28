import sys
import os
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
        self.buttonMkdir.clicked.connect(self.mkdir)
        self.buttonRmdir.clicked.connect(self.rmdir)
        self.buttonRename.clicked.connect(self.rename)
        self.buttonGet.clicked.connect(lambda: self.get())
        self.buttonPut.clicked.connect(self.put)

        self.host.setText('199.255.99.141')
        self.username.setText('cat')
        self.password.setText('cat')

    def setItemName(self, index):
        self.target.setText(self.files.model()[index.row(), 0])

    def access(self, index):
        model = self.files.model()
        name = model[index.row(), 0]
        isdir = model[index.row(), 3]
        if isdir:
            self.chdir(name)
        else:
            self.get(name)

    def chdir(self, dirname=None):
        if dirname is None:
            dirname = self.target.text()
        try:
            if dirname == '..':
                self.send('CDUP')
            else:
                self.send(f'CWD {dirname}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to enter folder.')

    def mkdir(self):
        try:
            self.send(f'MKD {self.target.text()}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to create folder.')

    def rmdir(self):
        try:
            self.send(f'RMD {self.target.text()}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to remove folder.')

    def rename(self):
        try:
            self.send(f'RNFR {self.target.text()}')
            self.recv()
            self.send(f'RNTO {self.newName.text()}')
            self.recv()
            self.transfer('LIST', self.recvList)
        except:
            QMessageBox.critical(self, 'Error', 'Failed to rename item.')

    def get(self, remotePath=None):
        if remotePath is None:
            remotePath = self.target.text()
        dlg = QFileDialog(self, 'Save as')
        # dlg.selectFile(os.path.basename(remotePath))
        if dlg.exec() == QDialog.Accepted:
            localPath = dlg.selectedFiles()[0]
            try:
                self.transfer(f'RETR {remotePath}', self.recvFile, localPath)
                QMessageBox.information(self, 'Info', 'Download completed.')
            except:
                QMessageBox.critical(self, 'Error', 'Download failed.')

    def put(self):
        remotePath = self.target.text()
        dlg = QFileDialog(self, 'Upload')
        dlg.setFileMode(QFileDialog.ExistingFiles)
        if dlg.exec() == QDialog.Accepted:
            localPath = dlg.selectedFiles()[0]
            try:
                self.transfer(f'STOR {remotePath}', self.sendFile, localPath)
                QMessageBox.information(self, 'Info', 'Upload completed.')
            except:
                QMessageBox.critical(self, 'Error', 'Upload failed.')
            try:
                self.transfer('LIST', self.recvList)
            except:
                QMessageBox.critical(self, 'Error', 'Failed to refresh directory.')

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

    def transfer(self, req, callback, *args):
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
                    callback(data, *args)
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
                callback(data, *args)
            finally:
                data.close()
        self.recv()

    def recvList(self, data):
        msg = b''
        while True:
            buf = data.recv(BUFFER_SIZE)
            if not buf:
                break
            msg += buf
        try:
            msg = msg.decode()
        except ValueError:
            msg = msg.decode(encoding='latin1')
        self.files.setModel(FilesModel(FTPParser().parse(msg.splitlines())))
        self.target.setText('')
        self.newName.setText('')

    def recvFile(self, data, filename):
        with open(filename, 'wb') as f:
            while True:
                buf = data.recv(BUFFER_SIZE)
                if not buf:
                    break
                f.write(buf)

    def sendFile(self, data, filename):
        with open(filename, 'rb') as f:
            while True:
                buf = f.read(BUFFER_SIZE)
                if not buf:
                    break
                data.sendall(buf)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
