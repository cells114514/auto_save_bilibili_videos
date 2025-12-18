from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget, QLineEdit, QLabel, QPlainTextEdit, QHBoxLayout, QVBoxLayout, QStackedLayout
import sys
import io
import time
import os
import PyQt5
from threading import Thread

from make_list import get_media_id, load_media_id, load_lst_from_csv
from watch_fav import watch_fav, init_program
from download import down_single_video

# from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
# print(f"Qt {QT_VERSION_STR}, PyQt {PYQT_VERSION_STR}")
# # 查看PyQt5版本

pyqt5_path = os.path.dirname(PyQt5.__file__)
QT_PLUGIN_PATH = os.path.join(pyqt5_path, 'Qt5', 'plugins')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(QT_PLUGIN_PATH, 'platforms')       # 这里是针对Ubuntu下找不到平台插件的问题，请根据实际情况调整

from PyQt5.QtCore import QThread, pyqtSignal

class MonitorThread(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()
    update_titles = pyqtSignal()
    def __init__(self, media_ids):
        super().__init__()
        self.media_ids = media_ids
        self._running = True
    def stop(self):
        self._running = False
    def new_watch_fav(self, media_id):
        watch_fav(media_id=media_id, download_new=True, interval=3)
        self.update_titles.emit()
    def run(self):
        try:
            self.log.emit("监视已启动。")
            curr_media_ids = load_media_id()
            while self._running:
                workers = []
                for media_id in curr_media_ids:
                    worker = Thread(
                        target=self.new_watch_fav,
                        args=(media_id,),
                        daemon=True,
                    )
                    worker.start()
                    workers.append(worker)
                for worker in workers:
                    worker.join()
                # self.update_titles.emit()
                time.sleep(60)
        except Exception as e:
            self.log.emit(f"错误: {e}")
        finally:
            self.log.emit("监视已停止。")
            self.finished.emit()

class DownloadThread(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, setTitle, bvid):
        super().__init__()
        self.setTitle = setTitle
        self.bvid = bvid
    def run(self):
        try:
            # 假设有一个函数 download_video_by_bvid 用于下载视频
            down_single_video(self.setTitle, self.bvid)
            self.log.emit(f"下载完成: {self.bvid}")
        except Exception as e:
            self.log.emit(f"下载错误 ({self.bvid}): {e}")
        finally:
            self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bilibili 收藏夹监视器")
        self.setGeometry(400, 200, 1000, 600)
        self.monitoring = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        menu = self.menuBar().addMenu("File")
        menu.addAction("fav monitor", lambda: self.pageBlock.setCurrentIndex(0))
        menu.addAction("down a video(low quality)", lambda: self.pageBlock.setCurrentIndex(1))
        menu.addAction("退出", self.close)

        self.titleBox = QVBoxLayout()
        self.monitorBlock = QVBoxLayout()
        self.mainBlock = QHBoxLayout()
        self.pageBlock = QStackedLayout()
        self.central_widget.setLayout(self.pageBlock)

        page1 = QWidget()
        page1.setLayout(self.mainBlock)
        self.pageBlock.addWidget(page1)

        self.logBox = QPlainTextEdit("", self)
        self.logBox.setReadOnly(True)

        self.videoTitle = QPlainTextEdit("", self)
        self.videoTitle.setReadOnly(True)
        # self.QplainTextEdit.setGeometry(100, 100, 400, 100)
        self.titleLabel = QLabel("已下载视频列表:", self)

        self.media_id_label = QLabel("Media IDs (每行一个):", self)
        self.media_id_input = QPlainTextEdit("", self)
        self.media_id_input.appendPlainText("\n".join(str(media_id) for media_id in load_media_id()))
        self.saveBotton = QPushButton("保存", self)
        self.saveBotton.clicked.connect(self.save_media_ids)

        self.monitorThread = MonitorThread(load_media_id())

        self.startBotton = QPushButton("开始监视", self)
        self.startBotton.clicked.connect(self.monitorThread.start)
        self.monitorThread.log.connect(lambda msg: self.logBox.appendPlainText(msg))
        self.monitorThread.finished.connect(lambda: self.startBotton.setEnabled(True))
        self.monitorThread.update_titles.connect(self.load_titles)
        self.stopBotton = QPushButton("停止监视", self)
        self.stopBotton.clicked.connect(self.monitorThread.stop)

        # self.mainBlock.addWidget(self.QLineEdit)
        self.titleBox.addWidget(self.titleLabel)
        self.titleBox.addWidget(self.videoTitle)
        self.titleBox.addWidget(self.logBox)       # 图省事放在这里了
        self.monitorBlock.addWidget(self.media_id_label)
        self.monitorBlock.addWidget(self.media_id_input)
        self.monitorBlock.addWidget(self.saveBotton)
        self.monitorBlock.addWidget(self.startBotton)
        self.monitorBlock.addWidget(self.stopBotton)
        self.mainBlock.addLayout(self.titleBox)
        self.mainBlock.addLayout(self.monitorBlock)

        self.SingledownBlock = QVBoxLayout()
        page2 = QWidget()
        page2.setLayout(self.SingledownBlock)
        self.pageBlock.addWidget(page2)

        self.SinLabel = QLabel("单独下载视频", self)
        self.setTitle = QLineEdit(self)
        self.setTitle.setPlaceholderText("自定义标题（默认为bvid）")
        self.bvid_input = QLineEdit(self)
        self.bvid_input.setPlaceholderText("输入BVID")
        self.singleDownBotton = QPushButton("下载", self)
        self.singleDownBotton.clicked.connect(self.start_single_download)
        self.tinyTerminal = QPlainTextEdit("", self)
        self.tinyTerminal.setReadOnly(True)

        self.SingledownBlock.addWidget(self.SinLabel)
        self.SingledownBlock.addWidget(self.setTitle)
        self.SingledownBlock.addWidget(self.bvid_input)
        self.SingledownBlock.addWidget(self.singleDownBotton)
        self.SingledownBlock.addWidget(self.tinyTerminal)
        self.pageBlock.setCurrentIndex(0)

    def load_titles(self):
        self.videoTitle.clear()
        lst = load_lst_from_csv()
        for title, bvid, cid in lst:
            self.videoTitle.appendPlainText(f"{title} | {bvid} | {cid}")

    def save_media_ids(self):
        text = self.media_id_input.toPlainText()
        media_id_list = []
        for line in text.splitlines():
            line = line.strip()
            if line.isdigit():
                media_id_list.append(int(line))
        get_media_id(media_id_list)
        print(f"Saved media IDs: {media_id_list}")

    def start_single_download(self):
        bvid = self.bvid_input.text().strip()
        setTitle = self.setTitle.text().strip() if self.setTitle.text().strip() else str(bvid)
        if bvid:
            self.singleDownBotton.setEnabled(False)
            self.downloadThread = DownloadThread(setTitle, bvid)
            self.downloadThread.log.connect(lambda msg: self.tinyTerminal.appendPlainText(msg))
            self.downloadThread.finished.connect(lambda: self.singleDownBotton.setEnabled(True))
            self.downloadThread.start()

    # def stopMoitor(self):
    #     self.monitoring = False     # 不直接抛出异常，让循环自然结束，防止文件损坏导致无法再次使用

    # def monitor(self):
    #     media_id_list = load_media_id()
    #     print(f"Loaded media IDs: {media_id_list}")
    #     self.monitoring = True
    #     try:
    #         while self.monitoring:
    #             for media_id in media_id_list:
    #                 watch_fav(media_id=media_id, download_new=True, interval=3)
    #             self.load_titles()
    #             time.sleep(60)  # 每60秒检查一次
    #     except Exception as e:
    #         print(f"Monitoring error: {e}")
    #     print("Monitoring stopped.")
        



if __name__ == "__main__":
    init_program()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.load_titles()
    window.show()
    sys.exit(app.exec_())
