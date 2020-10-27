import sys
import re
from datetime import datetime
from socket import *

from ftpparser import FTPParser
from humanize import naturalsize

from PyQt5 import uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class FilesModel(QAbstractTableModel):
    def __init__(self, items=[]):
        super().__init__()
        items.sort(key=lambda row:-row[3])
        self.items = items

    def columnCount(self, parent):
        return 3

    def rowCount(self, parent):
        return len(self.items)

    def rowData(self, row):
        name, size, ts, isdir = self.items[row][:4]
        if isdir:
            size = ''
        else:
            size = naturalsize(size, gnu=True)
        time = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        return (name, size, time)

    def data(self, index, role):
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.DisplayRole:
            i = index.row()
            j = index.column()
            return self.rowData(i)[j]

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal:
            if role == Qt.TextAlignmentRole:
                return Qt.AlignLeft | Qt.AlignVCenter

            if role == Qt.DisplayRole:
                if section == 0:
                    return 'Name'
                if section == 1:
                    return 'Size'
                if section == 2:
                    return 'Last modified'


class Window(QMainWindow):
    def __init__(self):
        super().__init__()

        uic.loadUi('window.ui', self)
        self.host = self.findChild(QLineEdit, 'host')
        self.port = self.findChild(QLineEdit, 'port')
        self.username = self.findChild(QLineEdit, 'username')
        self.password = self.findChild(QLineEdit, 'password')
        self.login = self.findChild(QPushButton, 'login')
        self.index = self.findChild(QTableView, 'index')
        self.passive = self.findChild(QAction, 'action_passive')

        self.index.setModel(FilesModel())
        header = self.index.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        self.index.setColumnWidth(1, 100)
        self.index.setColumnWidth(2, 180)

        self.host.setText('199.255.99.141')
        self.username.setText('cat')
        self.password.setText('cat')

        self.login.clicked.connect(self.loginClicked)

    def loginClicked(self):
        try:
            host = self.host.text()
            port = int(self.port.text())
            sess = socket(AF_INET, SOCK_STREAM)
            sess.connect((host, port))
            def recv():
                message = sess.recv(4096).decode()
                sys.stdout.write(message)
                return message
            def send(message):
                message += '\r\n'
                sys.stdout.write(message)
                sess.send(message.encode())
            recv()
            send(f'USER {self.username.text()}')
            recv()
            send(f'PASS {self.password.text()}')
            recv()
            # send('TYPE I')
            # recv()
            conn = None
            if not self.passive.isChecked():
                data = socket(AF_INET, SOCK_STREAM)
                data.bind(('', 0))
                data.listen(5)
                host = sess.getsockname()[0]
                port = data.getsockname()[1]
                print(data.getsockname())
                send('PORT {},{},{}'.format(host.replace('.', ','), port >> 8, port & 255))
                recv()
            else:
                send('PASV')
                addr = re.findall(r'\b\d+(?:,\d+){5}\b', recv())[0]
                print(addr)
                addr = tuple(map(int, addr.split(',')))
                host = '.'.join(map(str, addr[:4]))
                port = addr[4] << 8 | addr[5]
                conn = socket(AF_INET, SOCK_STREAM)
                conn.connect((host, port))
            send('LIST')
            recv()
            if conn is None:
                conn = data.accept()[0]
            res = conn.recv(4096).decode().splitlines()
            recv()
            items = FTPParser().parse(res)
            self.index.setModel(FilesModel(items))

        except Exception as e:
            print(type(e), str(e))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())
