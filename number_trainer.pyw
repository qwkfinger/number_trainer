# -*- coding: utf-8 -*-
"""A tool to assist learning a language."""

import sys
import os
import random
import subprocess
import shutil
import decimal
import time

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtMultimedia import QSound
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer, QMediaPlaylist
from PyQt5.QtCore import QDir, Qt, QUrl

from googletrans import Translator
from gtts import gTTS
#import playsound

class Signals(QObject):
    """Create signals."""

    new_number = pyqtSignal()
    repeat = pyqtSignal()
    answer = pyqtSignal("QString")
    solve = pyqtSignal()
    change_from = pyqtSignal(float)
    change_to = pyqtSignal(float)
    change_fraction = pyqtSignal(int)
    change_preset = pyqtSignal("QString")
    change_speed = pyqtSignal(int)
    app_quit = pyqtSignal()

    show_solution = pyqtSignal("QString")
    show_result = pyqtSignal("QString")
    update_statusbar = pyqtSignal("QString")
    update_text = pyqtSignal("QString")
    update_ui = pyqtSignal("QVariant")


class MainWindow(QtWidgets.QMainWindow):
    """Create the UI window based on ui file."""

    def __init__(self, signals):
        super(MainWindow, self).__init__() # Call the inherited classes __init__ method
        uic.loadUi('number_trainer.ui', self) # Load the .ui file
        self.signals = signals
        #self.signals.update_myresult.connect(self.update_myresult)
        #self.signals.update_help.connect(self.update_help)
        #self.signals.update_statusbar.connect(self.update_statusbar)

        self.pushButton_new.clicked.connect(self.on_new)
        self.pushButton_repeat.clicked.connect(self.on_repeat)
        self.pushButton_solve.clicked.connect(self.on_solve)
        self.lineEdit_answer.returnPressed.connect(self.on_answer)
        self.spinBox_from.valueChanged.connect(self.on_change_from)
        self.spinBox_to.valueChanged.connect(self.on_change_to)
        self.spinBox_fraction.valueChanged.connect(self.on_change_fraction)
        self.comboBox_presets.currentIndexChanged.connect(self.on_change_preset)
        self.dial_speed.valueChanged.connect(self.on_change_speed)

        self.signals.show_solution.connect(self.show_solution)
        self.signals.show_result.connect(self.show_result)
        self.signals.update_statusbar.connect(self.update_statusbar)
        self.signals.update_text.connect(self.update_text)
        self.signals.update_ui.connect(self.update_ui)
        #self.textEdit_mytext.setTabChangesFocus(True)
        self.lineEdit_answer.setFocus()
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.media_player.mediaStatusChanged[QMediaPlayer.MediaStatus].connect(self.on_media_status_changed)

    def on_new(self, event=None):
        """React on button press."""
        del event
        self.statusBar().showMessage("Speaking number ...")
        self.signals.new_number.emit()
        self.lineEdit_answer.setFocus()

    def on_repeat(self, event=None):
        """React on button press."""
        del event
        self.statusBar().showMessage("Repeating number ...")
        self.signals.repeat.emit()
        self.lineEdit_answer.setFocus()

    def on_answer(self, event=None):
        """React on button press."""
        del event
        text = self.lineEdit_answer.text()
        self.signals.answer.emit(text)

    def on_solve(self, event=None):
        """React on button press."""
        del event
        self.signals.solve.emit()
        self.lineEdit_answer.setFocus()

    def on_change_from(self, event=None):
        del event
        self.signals.change_from.emit(self.spinBox_from.value())
        self.lineEdit_answer.setFocus()

    def on_change_to(self, event=None):
        del event
        self.signals.change_to.emit(self.spinBox_to.value())
        self.lineEdit_answer.setFocus()

    def on_change_fraction(self, event=None):
        del event
        self.signals.change_fraction.emit(self.spinBox_fraction.value())
        self.lineEdit_answer.setFocus()

    def on_change_preset(self, event=None):
        del event
        self.signals.change_preset.emit(self.comboBox_presets.currentText())
        self.lineEdit_answer.setFocus()

    def on_change_speed(self, event=None):
        del event
        value = self.dial_speed.value()
        self.label_speed.setText(str(int(value*10.0)) + "%")
        self.signals.change_speed.emit(int(value*10.0))
        
    def on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            empty_playlist = QMediaPlaylist()
            self.media_player.setPlaylist(empty_playlist )
            
    def playsound(self, path):
        if os.path.exists(path):
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            self.media_player.play()

    def update_text(self, text):
        """Update window."""
        self.lineEdit_answer.setText(text)

    def show_result(self, text):
        """Update window."""
        self.label_result.setText(text)

    def show_solution(self, text):
        """Update window."""
        self.label_solution.setText(text)

    def update_statusbar(self, text):
        self.statusBar().showMessage(text)

    def update_ui(self, model):
        self.comboBox_presets.blockSignals(True)
        self.spinBox_from.blockSignals(True)
        self.spinBox_to.blockSignals(True)
        self.spinBox_fraction.blockSignals(True)

        self.spinBox_from.setValue(model.number_from)
        self.spinBox_to.setValue(model.number_to)
        self.spinBox_fraction.setValue(model.fraction)
        self.dial_speed.setValue(int(model.playback_speed/10.0))
        self.label_speed.setText(str(model.playback_speed) + "%")
        self.comboBox_presets.clear()
        self.comboBox_presets.addItems(model.presets.keys())
        index = self.comboBox_presets.findText(model.selected_preset, Qt.MatchFixedString)
        if index >= 0:
            self.comboBox_presets.setCurrentIndex(index)

        self.comboBox_presets.blockSignals(False)
        self.spinBox_from.blockSignals(False)
        self.spinBox_to.blockSignals(False)
        self.spinBox_fraction.blockSignals(False)

    def closeEvent(self, event=None):
        del event
        self.signals.app_quit.emit()

class Model:
    """Create model class that does the translation work."""

    def __init__(self, args):
        self.args = args

        self.translator = Translator()

        self.signals = Signals()
        self.connect_signals()

        self.number = "0"
        self.number_from = 0
        self.number_to = 0
        self.fraction = 0
        self.playback_speed = 100
        self.errors = 0
        self.max_errors = 2

        self.presets = {
            "0 à 10" : {
                "from" : 0,
                "to" : 10,
                "fraction" : 0,
                "speed" : 100,
                },
            "0 à 60" : {
                "from" : 0,
                "to" : 60,
                "fraction" : 0,
                "speed" : 100,
                },
            "0 à 100" : {
                "from" : 0,
                "to" : 100,
                "fraction" : 0,
                "speed" : 100,
                },
            "60 à 79" : {
                "from" : 60,
                "to" : 79,
                "fraction" : 0,
                "speed" : 100,
                },
            "80 à 99" : {
                "from" : 80,
                "to" : 99,
                "fraction" : 0,
                "speed" : 100,
                },
            "60 à 99" : {
                "from" : 60,
                "to" : 99,
                "fraction" : 0,
                "speed" : 100,
                },
            "0 à 10 avec 1 décimal" : {
                "from" : 0,
                "to" : 10,
                "fraction" : 1,
                "speed" : 100,
                },
            "0 à 10 avec 2 décimals" : {
                "from" : 0,
                "to" : 10,
                "fraction" : 2,
                "speed" : 100,
                },
            "années de naissance" : {
                "from" : 1970,
                "to" : 2020,
                "fraction" : 0,
                "speed" : 100,
                },
            "20ème siècle" : {
                "from" : 1900,
                "to" : 2000,
                "fraction" : 0,
                "speed" : 100,
                },
            "19ème siècle" : {
                "from" : 1800,
                "to" : 1900,
                "fraction" : 0,
                "speed" : 100,
                },
            "des siècles" : {
                "from" : 1000,
                "to" : 2000,
                "fraction" : -2,
                "speed" : 100,
                },
            "grands nombres" : {
                "from" : 10000,
                "to" : 9999999,
                "fraction" : -2,
                "speed" : 70,
                },
            }
        self.selected_preset = "0 à 10"
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r", encoding="utf-8") as filehandler:
                self.selected_preset = filehandler.read()
        if self.selected_preset not in self.presets:
            self.selected_preset = "0 à 10"

        self.learning_language = "fr"
        self.native_language = "de"

        self.number_stack = []

        self.app = QtWidgets.QApplication(sys.argv) # Create an instance of QtWidgets.QApplication
        self.gui = MainWindow(self.signals) # Create an instance of our class
        self.change_preset(self.selected_preset)
        self.gui.show() # Show the GUI
        self.app.exec_() # Start the application

    @staticmethod
    def float_range(start, stop, step):
        while start < stop:
            yield float(start)
            start += decimal.Decimal(step)

    def new_number(self):
        if self.number_stack:
            pass
        else:
            if self.fraction == 0:
                self.number_stack = list(range(int(self.number_from), int(self.number_to)))
                random.shuffle(self.number_stack)
            else:
                stack = list(
                    self.float_range(
                        self.number_from, self.number_to, 1/(10**(self.fraction))))
                for number in stack:
                    self.number_stack.append(round(number, self.fraction))
                random.shuffle(self.number_stack)
            if self.number_from == self.number_to:
                self.number_stack = [self.number_from]
        self.number = self.number_stack.pop(0)
        self.number = str(self.number).replace(".", ",")
        self.say_number()
        self.signals.update_text.emit("")
        self.signals.show_result.emit("")
        self.signals.show_solution.emit("")

    def repeat(self):
        self.app.setOverrideCursor(Qt.WaitCursor)
        self.errors += 1
        if self.errors > self.max_errors:
            self.say_number(slow=True)
        else:
            self.say_number(slow=False)
        #self.signals.update_text.emit("")
        self.app.restoreOverrideCursor()

    def answer(self, answer):
        if self.number == answer:
            self.errors = 0
            self.gui.playsound(r"C:\Windows\Media\ding.wav")
            self.signals.show_result.emit("Correct!")
            self.signals.update_statusbar.emit("The answer was correct. Speaking next number ...")
            self.new_number()
        else:
            self.gui.playsound(r"C:\Windows\Media\chord.wav")
            self.signals.update_statusbar.emit("The answer was wrong, please try again ...")
            self.signals.show_result.emit("Wrong!")
            self.repeat()
        self.signals.update_text.emit("")
        
    def solve(self):
        self.signals.update_statusbar.emit("OK, showing solution ...")
        self.signals.show_solution.emit(self.number)
        self.signals.update_text.emit("")

    def say_number(self, slow=False):
        self.app.setOverrideCursor(Qt.WaitCursor)
        self.app.processEvents()
        self.synthesize(self.number, slow)
        self.app.restoreOverrideCursor()

    def connect_signals(self):
        """Connect signals."""
        self.signals.new_number.connect(self.new_number)
        self.signals.repeat.connect(self.repeat)
        self.signals.answer.connect(self.answer)
        self.signals.solve.connect(self.solve)
        self.signals.change_from.connect(self.change_from)
        self.signals.change_to.connect(self.change_to)
        self.signals.change_fraction.connect(self.change_fraction)
        self.signals.change_preset.connect(self.change_preset)
        self.signals.change_speed.connect(self.change_speed)

        self.signals.app_quit.connect(self.app_quit)

    def change_from(self, value):
        self.number_from = value
        self.number_stack = []
        self.new_number()

    def change_to(self, value):
        self.number_to = value
        self.number_stack = []
        self.new_number()

    def change_fraction(self, value):
        self.fraction = value
        self.number_stack = []
        self.new_number()

    def change_preset(self, value):
        self.number_from = self.presets[value]["from"]
        self.number_to = self.presets[value]["to"]
        self.fraction = self.presets[value]["fraction"]
        self.playback_speed = self.presets[value]["speed"]
        self.selected_preset = value
        self.signals.update_ui.emit(self)
        self.number_stack = []
        self.new_number()

    def change_speed(self, value):
        self.playback_speed = value

    def synthesize(self, text, slow):
        self.signals.update_statusbar.emit("Synthesizing ...")
        language = self.learning_language
        #mp3_fp = BytesIO()
        filename = "{}_{}_{}.mp3".format(language, text, slow)
        sound_file = os.path.join(
            os.getcwd(),
            "cache",
            filename,
            )
        os.makedirs(os.path.dirname(sound_file), exist_ok=True)
        if os.path.exists(sound_file):
            pass
        else:
            tts = gTTS(text=text, lang=language, slow=slow)
            counter = 0
            while counter < 3:
                try:
                    tts.save(sound_file)
                    counter = 0
                    break
                except Exception as exception:
                    print(exception)
                    self.signals.update_statusbar.emit(
                        "Waiting for Google TTS, try {}/{} ...".format(counter+1, 3))
                    time.sleep(1)
                    counter += 1
            if counter != 0:
                self.signals.update_statusbar.emit("Timout on Google TTS, try the repeat button.")
        self.signals.update_statusbar.emit("Setting speed ...")
        self.apply_speed_change(sound_file, speed=self.playback_speed/100.0)
        self.signals.update_statusbar.emit("Speaking ...")
        self.gui.playsound(sound_file)
        self.signals.update_statusbar.emit("Waiting for answer ...")

    def apply_speed_change(self, file, speed=1.0):
        if speed == 1.0:
            return
        self.signals.update_statusbar.emit("Applying speed change ...")
        root, ext = os.path.splitext(file)
        outfile = "{}_mod{}".format(root, ext)
        cmd = [
            "ffmpeg.exe",
            "-i",
            file,
            '-filter:a "atempo={}"'.format(speed),
            outfile,
            ]
        cmd = " ".join(cmd)
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.Popen(cmd, startupinfo=startupinfo, shell=False).wait()
        try:
            shutil.move(outfile, file)
        except:
            print("Could not move file.")

    def app_quit(self):
        with open("settings.txt", "w", encoding="utf-8") as filehandler:
            filehandler.write(self.selected_preset)
        self.app.quit()

def main(args):
    """Create instance of class and run its main method."""
    Model(args)

if __name__ == "__main__":
    main(sys.argv)

#* added caching of sound files
#* added timeout on gTTS
#* added wait cursor during synthesis
#* changed slowing down on repeat: only after 3 errors
