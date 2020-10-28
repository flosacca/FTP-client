from datetime import datetime

from humanize import naturalsize

from PyQt5.QtCore import *


class FilesModel(QAbstractTableModel):
    def __init__(self, items=[]):
        super().__init__()
        items.sort(key=lambda row:-row[3])
        self.items = items

    def columnCount(self, parent):
        return 3

    def rowCount(self, parent):
        if self.items:
            return len(self.items) + 1
        return 0

    def rowData(self, row):
        if row == 0:
            return ('..', '', '', 1)
        name, size, ts, isdir = self.items[row - 1][:4]
        if isdir:
            size = ''
        else:
            size = naturalsize(size, gnu=True)
        time = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
        return (name, size, time, isdir)

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
