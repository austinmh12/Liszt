import io
import csv

from PySide2.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QDockWidget,
    QWidget,
    QTableView,
    QHBoxLayout,
    QTreeView,
    QListView,
    QLineEdit,
    QAbstractItemView,
    QDialog,
    QTextEdit,
    QPushButton,
)
from PySide2.QtGui import (
    Qt,
    QStandardItemModel,
    QStandardItem,
)
from PySide2.QtCore import (
    QFile,
    QMimeData,
    QByteArray,
    QModelIndex,
    Signal,
    Slot,
)


def getCards(db, listId):
    if listId == -1:
        return []
    result = db.runCommand(f'show-cards {listId}')
    cards = []
    with io.StringIO(result) as f:
        reader = csv.DictReader(f, delimiter='\t')
        for idx, row in enumerate(reader):
            card = Card(
                row['title'],
                row['id'],
                idx,
                row['content'],
                row['due'])
            cards.append(card)
    return cards

# TODO: Create a json serialization of Card, List, and Board

class Card(QStandardItem):
    def __init__(self, name, rowid, idx, content, dueDate):
        QStandardItem.__init__(self)
        self.itemType = 'CARD'
        self.name = name
        self.content = content.replace('<|NEWLINE|>', '\n')
        self.dueDate = int(dueDate)
        self.rowid = int(rowid)
        self.setText(name)
        self.idx = int(idx)


    def __str__(self):
        return f'{self.itemType}::{self.rowid}::{self.idx}::{self.name}'


class CardView(QListView):
    def __init__(self, db, parent=None):
        QListView.__init__(self)
        self.db = db
        self.setStyleSheet('''
                QListView {
                    font-size: 16pt;
                    background-color: #2e2e2e;
                    color: #cccccc;
                };
                ''')
        self.setWordWrap(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setSpacing(7)
        self.editDialog = CardEditWidget()
        self.doubleClicked.connect(self.onDoubleClick)
        return

    @Slot(QModelIndex)
    def onDoubleClick(self, index):
        card = self.model().itemFromIndex(index)
        self.editDialog.showCard(card)
        return

    @Slot(list)
    def selectedCards(self, cardList):
        indexes = self.selectedIndexes()
        for idx in indexes:
            cardModel = self.model().itemFromIndex(idx)
            cardId = cardModel.rowid
            cardList.append(cardId)
        return


class CardModel(QStandardItemModel):
    def __init__(self, db):
        QStandardItemModel.__init__(self, parent=None)
        self.db = db
        self.listId = -1
        return

    @Slot()
    def refresh(self):
        self.clear()
        try:
            for card in reversed(getCards(self.db, self.listId)):
                self.appendRow(card)
        except TypeError:
            pass
        return
    
    @Slot(int)
    def showListCards(self, listId):
        self.listId = listId
        self.refresh()
        return

    @Slot(list)
    def currentList(self, listidContainer):
        listidContainer.append(self.listId)
        return

    def dropMimeData(self, data, action, row, column, parent):
        result = False
        if 'CARD' in data.text():
            # A card being dropped in between cards
            _, cardId, cardIdx, _ = data.text().split('::')
            cardId, cardIdx = int(cardId), int(cardIdx)
            row = self.rowCount() - row

            if row == cardIdx or (row - 1) == cardIdx:
                return True

            if cardIdx > row:
                newIdx = row
            else:
                newIdx = row - 1

            cmd = f'shift-card {cardId} to {newIdx}'
            self.db.runCommand(cmd)
            self.refresh()
            result = True
        return result

    def mimeData(self, indexes):
        result = QMimeData()
        item = self.itemFromIndex(indexes[0])
        result.setText(str(item))
        return result

    def mimeTypes(self):
        return ['text/plain']


class CardEditWidget(QDialog):
    cardEdited = Signal(str, str, int, int)  # (name, content, dueDate, id)

    def __init__(self):
        QDialog.__init__(self)
        self.setStyleSheet('''
            QDialog {
                background-color: #2e2e2e;
                color: #cccccc;
                min-width: 500px;
            };
        ''')

        self.cardTitle = ''
        self.dueDate = -1
        self.content = ''
        self.cardId = -1

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        nameLayout = self.makeNameLayout()
        self.layout.addLayout(nameLayout)

        dueDateLayout = self.makeDueDateLayout()
        self.layout.addLayout(dueDateLayout)

        contentLayout = self.makeContentLayout()
        self.layout.addLayout(contentLayout)

        buttonLayout = self.makeButtonLayout()
        self.layout.addLayout(buttonLayout)
        return

    def makeNameLayout(self):
        nameLayout = QHBoxLayout()

        nameLabel = QLabel('Title:')
        nameLabel.setStyleSheet('QLabel { color: #cccccc; };')
        nameLayout.addWidget(nameLabel)

        self.nameTextEdit = QLineEdit()
        self.nameTextEdit.setStyleSheet('''
            QLineEdit {
                background-color: #2a2a2a;
                color: #cccccc;
            }; ''')
        nameLayout.addWidget(self.nameTextEdit)
        return nameLayout

    def makeDueDateLayout(self):
        dueDateLayout = QHBoxLayout()
        dateLabel = QLabel('Due Date:')
        dateLabel.setStyleSheet('QLabel { color: #cccccc; };')
        dueDateLayout.addWidget(dateLabel)
        dateLineEdit = QLineEdit()
        dateLineEdit.setStyleSheet('''
            QLineEdit {
                background-color: #2a2a2a;
                color: #cccccc;
            }; ''')

        dueDateLayout.addWidget(dateLineEdit)
        return dueDateLayout

    def makeContentLayout(self):
        contentLayout = QVBoxLayout()
        contentLabel = QLabel('Content:')
        contentLabel.setStyleSheet('QLabel { color: #cccccc; };')
        contentLayout.addWidget(contentLabel)

        contentEdit = QTextEdit()
        contentEdit.setStyleSheet('''
            QTextEdit {
                background-color: #2a2a2a;
                color: #cccccc;
            }; ''')
        contentLayout.addWidget(contentEdit)
        return contentLayout

    def makeButtonLayout(self):
        buttonLayout = QHBoxLayout()
        cancelButton = QPushButton('Cancel')
        cancelButton.setStyleSheet('''
            QPushButton {
                background-color: #2e2e2e;
                color: #cccccc;
            };
        ''')
        cancelButton.clicked.connect(self.close)

        saveButton = QPushButton('Save')
        saveButton.setStyleSheet('''
            QPushButton {
                background-color: #2e2e2e;
                color: #cccccc;
            };
        ''')
        saveButton.clicked.connect(self.handleSave)

        buttonLayout.addWidget(saveButton)
        buttonLayout.addWidget(cancelButton)
        return buttonLayout

    def showCard(self, card):
        self.cardTitle = card.name
        self.nameTextEdit.setText(card.name)
        self.dueDate = card.dueDate
        self.content = card.content
        self.cardId = card.rowid
        self.show()
        return

    @Slot()
    def handleSave(self):
        print('handle save')
        self.close()
        return
