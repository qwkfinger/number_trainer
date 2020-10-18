# -*- coding: utf-8 -*-
"""
A tool to assist learning a language.
"""

import sys
import os
import datetime
import random
import subprocess
import shutil

import winsound
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QObject, pyqtSignal, Qt

from googletrans import Translator
import difflib
import speech_recognition as sr
from gtts import gTTS
import playsound
import tempfile

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
        self.signals.change_from.emit(self.spinBox_from.value())
        self.lineEdit_answer.setFocus()

    def on_change_to(self, event=None):
        self.signals.change_to.emit(self.spinBox_to.value())
        self.lineEdit_answer.setFocus()

    def on_change_fraction(self, event=None):
        self.signals.change_fraction.emit(self.spinBox_fraction.value())
        self.lineEdit_answer.setFocus()

    def on_change_preset(self, event=None):
        self.signals.change_preset.emit(self.comboBox_presets.currentText())
        self.lineEdit_answer.setFocus()

    def on_change_speed(self, event=None):
        value = self.dial_speed.value()
        self.label_speed.setText(str(int(value*10.0)) + "%")
        self.signals.change_speed.emit(int(value*10.0))

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
        self.spinBox_from.setValue(model.number_from)
        self.spinBox_to.setValue(model.number_to)
        self.spinBox_fraction.setValue(model.fraction)
        self.dial_speed.setValue(int(model.playback_speed/10.0))
        self.label_speed.setText(str(model.playback_speed) + "%")
        self.comboBox_presets.blockSignals(True)
        self.comboBox_presets.clear()
        self.comboBox_presets.addItems(model.presets.keys())
        index = self.comboBox_presets.findText(model.selected_preset, Qt.MatchFixedString)
        if index >= 0:
            self.comboBox_presets.setCurrentIndex(index)
        self.comboBox_presets.blockSignals(False)

    def closeEvent(self, event=None):
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

        self.presets = {
            "0 à 10" : {
                "from" : 0,
                "to" : 10,
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
        self.selected_preset ="0 à 10"
        if os.path.exists("settings.txt"):
            with open("settings.txt", "r", encoding="utf-8") as filehandler:
                self.selected_preset = filehandler.read()
        if self.selected_preset not in self.presets:
            self.selected_preset ="0 à 10"

        self.learning_language = "fr"
        self.native_language = "de"

        self.app = QtWidgets.QApplication(sys.argv) # Create an instance of QtWidgets.QApplication
        self.gui = MainWindow(self.signals) # Create an instance of our class
        self.change_preset(self.selected_preset)
        self.gui.show() # Show the GUI
        self.app.exec_() # Start the application

    def new_number(self):
        old_number = self.number
        while old_number == str(self.number).replace(".", ","):
            if self.fraction == 0:
                self.number = random.randint(self.number_from, self.number_to)
            elif self.fraction <=0:
                self.number = int(round(random.uniform(self.number_from, self.number_to), self.fraction))
            else:
                self.number = round(random.uniform(self.number_from, self.number_to), self.fraction)
            if self.number_from == self.number_to:
                break
        self.number = str(self.number).replace(".", ",")
        self.say_number()
        self.signals.update_text.emit("")
        self.signals.show_result.emit("")
        self.signals.show_solution.emit("")

    def repeat(self):
        self.say_number(slow=True)
        #self.signals.update_text.emit("")

    def answer(self, answer):
        if self.number == answer:
            playsound.playsound(r"C:\Windows\Media\ding.wav", False)
            self.signals.show_result.emit("Correct!")
            self.signals.update_statusbar.emit("The answer was correct. Speaking next number ...")
            self.new_number()
        else:
            playsound.playsound(r"C:\Windows\Media\chord.wav", False)
            self.signals.update_statusbar.emit("The answer was wrong, please try again ...")
            self.signals.show_result.emit("Wrong!")
            self.repeat()
        self.signals.update_text.emit("")

    def solve(self):
        self.signals.update_statusbar.emit("OK, showing solution ...")
        self.signals.show_solution.emit(self.number)
        self.signals.update_text.emit("")

    def say_number(self, slow=False):
        self.app.processEvents()
        self.synthesize(self.number, slow)

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

    def change_to(self, value):
        self.number_to = value

    def change_fraction(self, value):
        self.fraction = value

    def change_preset(self, value):
        self.number_from = self.presets[value]["from"]
        self.number_to = self.presets[value]["to"]
        self.fraction = self.presets[value]["fraction"]
        self.playback_speed = self.presets[value]["speed"]
        self.selected_preset = value
        self.signals.update_ui.emit(self)
        self.new_number()

    def change_speed(self, value):
        self.playback_speed = value

    def synthesize(self, text, slow):
        self.signals.update_statusbar.emit("Speaking ...")
        language = self.learning_language
        #mp3_fp = BytesIO()
        tmpfile = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmpfile.close()
        tts = gTTS(text=text, lang=language, slow=slow)
        tts.save(tmpfile.name)
        self.apply_speed_change(tmpfile.name, speed=self.playback_speed/100.0)
        playsound.playsound(tmpfile.name, False)
        tmpfile.close()
        os.remove(tmpfile.name)
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
        shutil.move(outfile, file)

    def app_quit(self):
        with open("settings.txt", "w", encoding="utf-8") as filehandler:
            filehandler.write(self.selected_preset)
        self.app.quit()

def main(args):
    """Create instance of class and run its main method."""
    app = Model(args)

if __name__ == "__main__":
    main(sys.argv)

