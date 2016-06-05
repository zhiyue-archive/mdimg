import sys
import os
import time
import subprocess
import urllib.request
import pickle
from functools import partial
from PyQt4 import QtGui
import qiniu
import pyperclip
import configparser


class MDImg(QtGui.QWidget):
    __HISTORY_FILENAME__ = '.paste_history'

    def __init__(self, parent):
        super(MDImg, self).__init__(parent)

        self.tray = QtGui.QSystemTrayIcon(QtGui.QIcon('icon.ico'), self)
        self.menu = QtGui.QMenu(self)

        exitAction = QtGui.QAction(
            "E&xit", self, shortcut="Ctrl+Q",
            statusTip="Exit the application", triggered=self.close)

        self.enableAction = QtGui.QAction(
            "&Enable", self, shortcut='Ctrl+E',
            statusTip='Enable monitor the clipboard', checkable=True)

        self.historyMenu = QtGui.QMenu("&History")

        self.enableAction.setChecked(True)

        self.menu.addMenu(self.historyMenu)
        self.menu.addAction(self.enableAction)
        self.menu.addAction(exitAction)

        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip('upload qiniu')
        self.history = {'urls':[], 'titles':{}}

        self.load_history()
        self.load_config()
        self.img_dir = './imgs'
        if not os.path.exists('./imgs'):
             os.mkdir('./imgs')


    def close(self):
        self.save_history()
        super().close()

    def load_history(self):
        try:
            with open(self.__HISTORY_FILENAME__, 'rb') as f:
                self.history = pickle.load(f)
        except:
            pass
        self.update_history_menu()

    def load_config(self):
        try:
            cf = configparser.ConfigParser()
            cf.read(u"config.ini")
            self.access_key = cf.get("main", "access_key")
            self.secret_key = cf.get("main", "secret_key")
            self.bucket = cf.get("main", "bucket")
            self.domain = cf.get("main", "domain")

        except Exception as e:
            raise

    def save_history(self):
        with open(self.__HISTORY_FILENAME__, 'wb') as f:
            pickle.dump(self.history, f, -1)

    def append_history(self, title, url):
        if url in self.history['urls']:
            self.history['urls'].remove(url)
            del self.history['titles'][url]
        if len(self.history['urls']) > 10:
            del self.history['titles'][self.history['urls'][0]]
            self.history['urls'] = self.history['urls'][1:]
        self.history['urls'].append(url)
        self.history['titles'][url] = title
        self.update_history_menu()

    def update_history_menu(self):
        self.historyMenu.clear()
        last = None
        for url in self.history['urls']:
            title = self.history['titles'][url]
            action = QtGui.QAction(title, self, triggered=partial(pyperclip.copy, url))
            self.historyMenu.insertAction(last, action)
            last = action

    def upload(self, name):
        key = os.path.basename(name)
        q = qiniu.Auth(self.access_key, self.secret_key)
        with open(name, 'rb') as img:
            data = img
            token = q.upload_token(self.bucket)
            ret, info = qiniu.put_data(token, key, data)
            if self.parseRet(ret, info):
                md_url = "![]({}/{})".format(self.domain, key)
                print(md_url)
                title = name
                pyperclip.copy(md_url)
                self.append_history(title, md_url)

    # 处理七牛返回结果
    def parseRet(self,retData, respInfo):
        if retData != None:
            print("success")
            for k, v in retData.items():
                if k[:2] == "x:":
                    print(k + ":" + v)
            for k, v in retData.items():
                if k[:2] == "x:" or k == "hash" or k == "key":
                    continue
                else:
                    print(k + ":" + str(v))
            return True
        else:
            print("Upload file failed!")
            return False

    def get_url(self, name):
        site, title = (None, None)
        site = "![]({}/{})".format(self.domain, name)
        title = name
        return '@'.join([title,site])

    def onClipChanged(self):
        if(QtGui.QApplication.clipboard().mimeData().hasImage()):
            image = QtGui.QApplication.clipboard().mimeData().imageData()
            if self.enableAction.isChecked():
                try:
                    img_name = time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime(time.time())) + ".png"
                    img_path = os.path.join(self.img_dir,img_name)
                    image.save(img_path)
                    url = self.get_url(img_name)
                    if QtGui.QSystemTrayIcon.supportsMessages():
                        self.tray.showMessage('Now Upload ...', img_name)
                    self.upload(img_path)
                except Exception as e:
                    print(e)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    frame = MDImg(None)
    frame.tray.show()
    app.clipboard().dataChanged.connect(frame.onClipChanged)
    sys.exit(app.exec_())
