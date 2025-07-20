import os, time, json, sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRunnable, Qt, QThreadPool
from PyQt5.QtWidgets import QApplication

from common import getExpiry
from BOT import main_call, squareOffAll

import sys, os, time
import codecs

import threading
from datetime import datetime

from pathlib import Path
import base64

getCwd = os.getcwd()
time.sleep(1)


default_expiry = ["current", "next"]
order_expiry_timer = ["ON", "OFF"]
order_transmit = ["True", "False"]
candle_time_set = ["5 mins", "3 mins", "1 min", "15 mins", "30 mins", "1 hour", "2 hours", "3 hours", "4 hours", "1 day"]


#----------------------#
# -- LICENSE SYSTEM --
#----------------------#
LICENSE_FILE = "license.json"
LICENSE_KEY = "TraderNova_987_90_1"

def encrypt_string(plain_text):
    return base64.b64encode(plain_text.encode()).decode()
    
def decrypt_string(encoded_text):
    return base64.b64decode(encoded_text.encode()).decode()

def is_license_valid(file_path: str = LICENSE_FILE) -> bool:
    try:
        if not Path(file_path).exists():
            print("License file not found/Deleted.\nPlease Contact Support Team at 'treetechconsultancy@gmail.com'")
            time.sleep(10)
            sys.exit()
            sys.exit(0)
            sys.exit(1)
        elif Path(file_path).exists():
            print("License file present, validating it")

        with open(file_path, "r") as f:
            license_data = json.load(f)

        issued_str = base64.b64decode(license_data["issued"]).decode()
        issued_date = datetime.fromisoformat(issued_str)

        now = datetime.now()
        delta = now - issued_date
        days_remain = 90 - delta.days
        if delta.days <= 90:
            print(f"License is valid.")
            print(f"Days remains : {days_remain}")
            time.sleep(5)
            return True
        else:
            print("Your License has expired.\nPlease Contact Support Team at 'treetechconsultancy@gmail.com'")
            time.sleep(20)
            sys.exit()
            sys.exit(0)
            sys.exit(1)
            return False

    except Exception as e:
        print("License validation error:", e)
        return False

#----------------------#
# -- LICENSE SYSTEM --
#----------------------#

class Ui_Frame(object):
    def setupUi(self, Frame):
        Frame.setObjectName("Frame")
        Frame.resize(1365, 880)
        font = QtGui.QFont()
        font.setPointSize(11)
        Frame.setFont(font)
        #icon = QtGui.QIcon()
        #icon.addPixmap(QtGui.QPixmap("C:/Users/Administrator/Desktop/BOT_Cris/test-img/Level Up (Black _ Gold Transparent).png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        pixmap = QtGui.QPixmap("C:/Users/Administrator/Desktop/BOT_Cris/test-img/Level Up (White _ Gold Transparent).png")
        #Frame.setWindowIcon(icon)
        Frame.setStyleSheet("background-color: rgb(0, 0, 0);")
        Frame.setWindowTitle("Uprety Capital Securities, LP")

        self.groupBox = QtWidgets.QGroupBox(Frame)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 871, 91))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        self.groupBox.setFont(font)
        self.groupBox.setStyleSheet("color: rgb(255, 255, 255);")
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setTitle("TWS Configuratoin")

        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(10, 50, 71, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label.setFont(font)
        self.label.setStyleSheet("color: rgb(255, 255, 255);")
        self.label.setObjectName("label")
        self.label.setText("TWS IP :")

        self.textEdit = QtWidgets.QTextEdit(self.groupBox)
        self.textEdit.setGeometry(QtCore.QRect(90, 40, 161, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.textEdit.setFont(font)
        self.textEdit.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit.setObjectName("textEdit")
        self.textEdit.setText("127.0.0.1")

        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(270, 50, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label_2.setFont(font)
        self.label_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_2.setObjectName("label_2")
        self.label_2.setText("TWS PORT :")

        self.textEdit_2 = QtWidgets.QTextEdit(self.groupBox)
        self.textEdit_2.setGeometry(QtCore.QRect(380, 40, 161, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.textEdit_2.setFont(font)
        self.textEdit_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_2.setObjectName("textEdit_2")
        self.textEdit_2.setText("7497")

        self.label_3 = QtWidgets.QLabel(self.groupBox)
        self.label_3.setGeometry(QtCore.QRect(560, 50, 81, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label_3.setFont(font)
        self.label_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_3.setObjectName("label_3")
        self.label_3.setText("TWS ID :")

        self.textEdit_3 = QtWidgets.QTextEdit(self.groupBox)
        self.textEdit_3.setGeometry(QtCore.QRect(640, 40, 161, 41))
        self.textEdit_3.setFont(font)
        self.textEdit_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_3.setObjectName("textEdit_3")
        self.textEdit_3.setText("0")

        self.groupBox_2 = QtWidgets.QGroupBox(Frame)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 110, 871, 751))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        self.groupBox_2.setFont(font)
        self.groupBox_2.setStyleSheet("color: rgb(255, 255, 255);")
        self.groupBox_2.setObjectName("groupBox_2")
        self.groupBox_2.setTitle("Trade System Configuration")

        self.label_4 = QtWidgets.QLabel(self.groupBox_2)
        self.label_4.setGeometry(QtCore.QRect(20, 40, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_4.setFont(font)
        self.label_4.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.label_4.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_4.setAlignment(QtCore.Qt.AlignCenter)
        self.label_4.setObjectName("label_4")
        self.label_4.setText("Expiry :")

        """self.textEdit_4 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_4.setGeometry(QtCore.QRect(210, 40, 161, 41))
        self.textEdit_4.setTabChangesFocus(True)
        self.textEdit_4.setObjectName("textEdit_4")
        self.textEdit_4.setStyleSheet("color: rgb(255, 255, 255);\n"
"background-color: rgb(255, 255, 255);")
        self.textEdit_4.setPlaceholderText("Expiry To Trade")"""
        
        self.comboBox_6 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_6.setGeometry(QtCore.QRect(210, 40, 161, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.comboBox_6.setFont(font)
        self.comboBox_6.setStyleSheet("color: rgb(255, 255, 255);"
"font: 11pt 'MS Shell Dlg 2';")
        self.comboBox_6.setEditable(True)
        self.comboBox_6.setObjectName("comboBox")
        self.comboBox_6.addItems(default_expiry)

        self.label_5 = QtWidgets.QLabel(self.groupBox_2)
        self.label_5.setGeometry(QtCore.QRect(20, 100, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_5.setFont(font)
        self.label_5.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName("label_5")
        self.label_5.setText("SPY/QQQ Expiry :")

        self.label_6 = QtWidgets.QLabel(self.groupBox_2)
        self.label_6.setGeometry(QtCore.QRect(20, 160, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_6.setFont(font)
        self.label_6.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_6.setAlignment(QtCore.Qt.AlignCenter)
        self.label_6.setObjectName("label_6")
        self.label_6.setText("Start Time :")

        self.label_7 = QtWidgets.QLabel(self.groupBox_2)
        self.label_7.setGeometry(QtCore.QRect(10, 220, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_7.setFont(font)
        self.label_7.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_7.setScaledContents(False)
        self.label_7.setAlignment(QtCore.Qt.AlignCenter)
        self.label_7.setObjectName("label_7")
        self.label_7.setText("Close Time :")

        self.label_8 = QtWidgets.QLabel(self.groupBox_2)
        self.label_8.setGeometry(QtCore.QRect(410, 570, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_8.setFont(font)
        self.label_8.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_8.setAlignment(QtCore.Qt.AlignCenter)
        self.label_8.setObjectName("label_8")
        self.label_8.setText("Loss $ For Day:")
        
        self.textEdit_61 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_61.setGeometry(QtCore.QRect(590, 570, 161, 41))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.textEdit_61.setFont(font)
        self.textEdit_61.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_61.setTabChangesFocus(True)
        self.textEdit_61.setObjectName("textEdit_61")
        self.textEdit_61.setPlaceholderText("Loss amount to stop the system")
        self.textEdit_61.setText("250")

        self.label_9 = QtWidgets.QLabel(self.groupBox_2)
        self.label_9.setGeometry(QtCore.QRect(20, 360, 152, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_9.setFont(font)
        self.label_9.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_9.setAlignment(QtCore.Qt.AlignCenter)
        self.label_9.setObjectName("label_9")
        self.label_9.setText("Timer In Order(S)")

        self.label_10 = QtWidgets.QLabel(self.groupBox_2)
        self.label_10.setGeometry(QtCore.QRect(10, 420, 171, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_10.setFont(font)
        self.label_10.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_10.setAlignment(QtCore.Qt.AlignCenter)
        self.label_10.setObjectName("label_10")
        self.label_10.setText("Order Expiry Timer :")

        self.label_11 = QtWidgets.QLabel(self.groupBox_2)
        self.label_11.setGeometry(QtCore.QRect(420, 80, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_11.setFont(font)
        self.label_11.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_11.setAlignment(QtCore.Qt.AlignCenter)
        self.label_11.setObjectName("label_11")
        self.label_11.setText("Order Transmit :")

        self.label_12 = QtWidgets.QLabel(self.groupBox_2)
        self.label_12.setGeometry(QtCore.QRect(440, 140, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_12.setFont(font)
        self.label_12.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_12.setAlignment(QtCore.Qt.AlignCenter)
        self.label_12.setObjectName("label_12")
        self.label_12.setText("CALL Delta :")

        self.textEdit_6 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_6.setGeometry(QtCore.QRect(210, 160, 161, 41))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.textEdit_6.setFont(font)
        self.textEdit_6.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_6.setTabChangesFocus(True)
        self.textEdit_6.setObjectName("textEdit_6")
        self.textEdit_6.setPlaceholderText("System Start Time")
        self.textEdit_6.setText("09:35")

        self.textEdit_7 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_7.setGeometry(QtCore.QRect(210, 220, 161, 41))
        self.textEdit_7.setFont(font)
        self.textEdit_7.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_7.setTabChangesFocus(True)
        self.textEdit_7.setObjectName("textEdit_7")
        self.textEdit_7.setPlaceholderText("System End Time")
        self.textEdit_7.setText("15:45")

        self.textEdit_9 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_9.setGeometry(QtCore.QRect(210, 350, 161, 41))
        self.textEdit_9.setFont(font)
        self.textEdit_9.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_9.setTabChangesFocus(True)
        self.textEdit_9.setObjectName("textEdit_9")
        self.textEdit_9.setPlaceholderText("Timer In Order")
        self.textEdit_9.setText("15")

        self.textEdit_11 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_11.setGeometry(QtCore.QRect(590, 140, 161, 41))
        self.textEdit_11.setFont(font)
        self.textEdit_11.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_11.setTabChangesFocus(True)
        self.textEdit_11.setObjectName("textEdit_11")
        self.textEdit_11.setPlaceholderText("CALL Delta Strike")
        self.textEdit_11.setText("0.35")

        self.textEdit_12 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_12.setGeometry(QtCore.QRect(590, 200, 161, 41))
        self.textEdit_12.setFont(font)
        self.textEdit_12.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_12.setTabChangesFocus(True)
        self.textEdit_12.setObjectName("textEdit_12")
        self.textEdit_12.setPlaceholderText("PUT Delta Strike")
        self.textEdit_12.setText("-0.35")

        self.textEdit_13 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_13.setGeometry(QtCore.QRect(590, 260, 161, 41))
        self.textEdit_13.setFont(font)
        self.textEdit_13.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_13.setTabChangesFocus(True)
        self.textEdit_13.setObjectName("textEdit_13")
        self.textEdit_13.setPlaceholderText("Trade Volumn Check")
        self.textEdit_13.setText("100")

        self.textEdit_14 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_14.setGeometry(QtCore.QRect(590, 320, 161, 41))
        self.textEdit_14.setFont(font)
        self.textEdit_14.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_14.setTabChangesFocus(True)
        self.textEdit_14.setObjectName("textEdit_14")
        self.textEdit_14.setPlaceholderText("ATR Checks")
        self.textEdit_14.setText("0.047")
        
        self.textEdit_15 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_15.setGeometry(QtCore.QRect(590, 380, 161, 41))
        self.textEdit_15.setFont(font)
        self.textEdit_15.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_15.setTabChangesFocus(True)
        self.textEdit_15.setObjectName("textEdit_15")
        self.textEdit_15.setPlaceholderText("Active Volumn Check")
        self.textEdit_15.setText("5")

        self.label_13 = QtWidgets.QLabel(self.groupBox_2)
        self.label_13.setGeometry(QtCore.QRect(440, 210, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_13.setFont(font)
        self.label_13.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_13.setAlignment(QtCore.Qt.AlignCenter)
        self.label_13.setObjectName("label_13")
        self.label_13.setText("PUT Delta :")

        self.label_14 = QtWidgets.QLabel(self.groupBox_2)
        self.label_14.setGeometry(QtCore.QRect(420, 260, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_14.setFont(font)
        self.label_14.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_14.setAlignment(QtCore.Qt.AlignCenter)
        self.label_14.setObjectName("label_14")
        self.label_14.setText("Volumn Check :")

        self.label_15 = QtWidgets.QLabel(self.groupBox_2)
        self.label_15.setGeometry(QtCore.QRect(430, 320, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_15.setFont(font)
        self.label_15.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_15.setAlignment(QtCore.Qt.AlignCenter)
        self.label_15.setObjectName("label_15")
        self.label_15.setText("ATR Check :")

        self.label_16 = QtWidgets.QLabel(self.groupBox_2)
        self.label_16.setGeometry(QtCore.QRect(420, 380, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_16.setFont(font)
        self.label_16.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_16.setAlignment(QtCore.Qt.AlignCenter)
        self.label_16.setObjectName("label_16")
        self.label_16.setText("Active Volumn :")

        self.label_18 = QtWidgets.QLabel(self.groupBox_2)
        self.label_18.setGeometry(QtCore.QRect(10, 500, 171, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_18.setFont(font)
        self.label_18.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_18.setAlignment(QtCore.Qt.AlignCenter)
        self.label_18.setObjectName("label_18")
        self.label_18.setText("Candle Time :")
        
        self.label_17 = QtWidgets.QLabel(self.groupBox_2)
        self.label_17.setGeometry(QtCore.QRect(400, 500, 171, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_17.setFont(font)
        self.label_17.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_17.setAlignment(QtCore.Qt.AlignCenter)
        self.label_17.setObjectName("label_17")
        self.label_17.setText("Profit $ For Day :")

        self.label_19 = QtWidgets.QLabel(self.groupBox_2)
        self.label_19.setGeometry(QtCore.QRect(410, 440, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_19.setFont(font)
        self.label_19.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_19.setAlignment(QtCore.Qt.AlignCenter)
        self.label_19.setObjectName("label_19")
        self.label_19.setText("Gap B/W Trades :")

        self.label_20 = QtWidgets.QLabel(self.groupBox_2)
        self.label_20.setGeometry(QtCore.QRect(20, 280, 161, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_20.setFont(font)
        self.label_20.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_20.setAlignment(QtCore.Qt.AlignCenter)
        self.label_20.setObjectName("label_20")
        self.label_20.setText("Max Contract\n"
"Amount :")

        self.label_21 = QtWidgets.QLabel(self.groupBox_2)
        self.label_21.setGeometry(QtCore.QRect(10, 560, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.label_21.setFont(font)
        self.label_21.setStyleSheet("color: rgb(255, 255, 255);")
        self.label_21.setAlignment(QtCore.Qt.AlignCenter)
        self.label_21.setObjectName("label_21")
        self.label_21.setText("Stock List :")
        
        self.textEdit_17 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_17.setGeometry(QtCore.QRect(590, 510, 161, 41))
        self.textEdit_17.setFont(font)
        self.textEdit_17.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_17.setTabChangesFocus(True)
        self.textEdit_17.setObjectName("textEdit_17")
        self.textEdit_17.setPlaceholderText("Profit amount to stop the system")
        self.textEdit_17.setText("300")

        self.textEdit_19 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_19.setGeometry(QtCore.QRect(590, 440, 161, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setWeight(75)
        self.textEdit_19.setFont(font)
        self.textEdit_19.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_19.setTabChangesFocus(True)
        self.textEdit_19.setObjectName("textEdit_19")
        self.textEdit_19.setPlaceholderText("Seconds Gap B/W Trades")
        self.textEdit_19.setText("300")

        self.comboBox = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox.setGeometry(QtCore.QRect(210, 100, 161, 41))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(75)
        self.comboBox.setFont(font)
        self.comboBox.setStyleSheet("color: rgb(255, 255, 255);"
"font: 11pt 'MS Shell Dlg 2';")
        self.comboBox.setEditable(True)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.setCurrentText("same as expiry")

        self.textEdit_20 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_20.setGeometry(QtCore.QRect(210, 290, 161, 41))
        self.textEdit_20.setFont(font)
        self.textEdit_20.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_20.setTabChangesFocus(True)
        self.textEdit_20.setObjectName("textEdit_20")
        self.textEdit_20.setPlaceholderText("Max Amt Contract")
        self.textEdit_20.setText("350")

        self.comboBox_3 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_3.setGeometry(QtCore.QRect(210, 420, 161, 41))
        self.comboBox_3.setFont(font)
        self.comboBox_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.comboBox_3.setEditable(False)
        self.comboBox_3.setCurrentText("")
        self.comboBox_3.setObjectName("comboBox_3")
        self.comboBox_3.addItems(order_expiry_timer)

        self.comboBox_4 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_4.setGeometry(QtCore.QRect(210, 490, 161, 41))
        self.comboBox_4.setFont(font)
        self.comboBox_4.setStyleSheet("color: rgb(255, 255, 255);")
        self.comboBox_4.setEditable(False)
        self.comboBox_4.setCurrentText("")
        self.comboBox_4.setObjectName("comboBox_4")
        self.comboBox_4.addItems(candle_time_set)

        self.comboBox_5 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_5.setGeometry(QtCore.QRect(590, 80, 161, 41))
        self.comboBox_5.setFont(font)
        self.comboBox_5.setStyleSheet("color: rgb(255, 255, 255);")
        self.comboBox_5.setEditable(False)
        self.comboBox_5.setCurrentText("")
        self.comboBox_5.setObjectName("comboBox_5")
        self.comboBox_5.addItems(order_transmit)

        self.textEdit_21 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_21.setGeometry(QtCore.QRect(200, 560, 210, 75))
        self.textEdit_21.setFont(font)
        self.textEdit_21.setStyleSheet("color: rgb(255, 255, 255);")
        self.textEdit_21.setTabChangesFocus(True)
        self.textEdit_21.setObjectName("textEdit_21")
        self.textEdit_21.setPlaceholderText("comma seperate stocks")
        self.textEdit_21.setText('"SPY":"NASDAQ"')
        
        self.checkBox = QtWidgets.QCheckBox(self.groupBox_2)
        self.checkBox.setGeometry(QtCore.QRect(590, 20, 171, 41))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.checkBox.setFont(font)
        self.checkBox.setStyleSheet("color: rgb(255, 255, 255);")
        self.checkBox.setText("Advance Options")
        self.checkBox.setTristate(False)
        self.checkBox.setObjectName("checkBox")
        self.checkBox.stateChanged.connect(self.enable_advance)
        #self.checkBox.stateChanged.disconnect(self.hideBeforeLoad)
        
        self.groupBox_3 = QtWidgets.QGroupBox(Frame)
        self.groupBox_3.setGeometry(QtCore.QRect(900, 122, 431, 741))
        font = QtGui.QFont()
        font.setPointSize(11)

        self.groupBox_3.setFont(font)
        self.groupBox_3.setAutoFillBackground(False)
        self.groupBox_3.setStyleSheet("color: rgb(255, 255, 255);")
        self.groupBox_3.setObjectName("groupBox_3")
        self.groupBox_3.setTitle("LOGS")
        
        self.label_22 = QtWidgets.QLabel(self.groupBox_3)
        self.label_22.setGeometry(QtCore.QRect(10, 20, 411, 701))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label_22.setFont(font)
        self.label_22.setStyleSheet("background-color: rgb(255, 255, 255);\n"
"color: rgb(0, 0, 0);")
        self.label_22.setObjectName("label_22")
        self.label_22.setText("")

        self.groupBox_4 = QtWidgets.QGroupBox(Frame)
        self.groupBox_4.setGeometry(QtCore.QRect(900, 20, 431, 101))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.groupBox_4.setFont(font)
        self.groupBox_4.setStyleSheet("image: url(:/test-img/Level Up (Black _ Gold Transparent).png);")
        self.groupBox_4.setTitle("")
        self.groupBox_4.setObjectName("groupBox_4")
        
        #############################################################################
        #############################################################################
        ############################################################################
        self.label_image = QtWidgets.QLabel(self.groupBox_4)
        self.label_image.setGeometry(QtCore.QRect(0, 0, 431, 101))
        self.label_image.setStyleSheet("color: rgb(255, 255, 255);")
        pixmap = QtGui.QPixmap("C:/Users/Administrator/Desktop/BOT_Cris/test-img/Level Up (White _ Gold Transparent).png")
        self.label_image.setPixmap(pixmap)
        self.label_image.setScaledContents(True)
        ############################################################################
        ###########################################################################
        ##########################################################################

        self.label_img = QtWidgets.QLabel(self.groupBox_4)
        self.label_img.setObjectName("label_img")
        self.label_img.setPixmap(pixmap)
        self.label_img.setGeometry(QtCore.QRect(900, 20, 431, 101))
        self.label_img.setStyleSheet("color: rgb(255, 255, 255);")

        self.pushButton = QtWidgets.QPushButton(self.groupBox_2)
        self.pushButton.setGeometry(QtCore.QRect(200, 650, 161, 61))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.pushButton.setFont(font)
        self.pushButton.setStyleSheet("background-color: rgb(255, 255, 127);\n"
"color: rgb(0, 0, 0);")
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setText("Save")
        self.pushButton.clicked.connect(self.save_data)

        self.pushButton_2 = QtWidgets.QPushButton(self.groupBox_2)
        self.pushButton_2.setGeometry(QtCore.QRect(400, 650, 161, 61))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setStyleSheet("background-color: rgb(255, 255, 127);\n"
"color: rgb(0, 0, 0);")
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.setText("Start")
        self.pushButton_2.clicked.connect(self.startExecution)
        
        self.pushButton_3 = QtWidgets.QPushButton(self.groupBox_2)
        self.pushButton_3.setGeometry(QtCore.QRect(600, 650, 161, 61))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.pushButton_3.setFont(font)
        self.pushButton_3.setStyleSheet("background-color: rgb(255, 255, 127);\n"
"color: rgb(0, 0, 0);")
        self.pushButton_3.setObjectName("pushButton_3")
        self.pushButton_3.setText("SquareOff")
        self.pushButton_3.clicked.connect(self.squareOffExecution)
        
        self.hideBeforeLoad()


    def returnLoadValues(self):
        self.returnValues = {}

        ip = self.textEdit.toPlainText()
        self.returnValues.update({"ip":ip})
        
        port = self.textEdit_2.toPlainText()
        self.returnValues.update({"port":port})
        
        clientId = self.textEdit_3.toPlainText()
        self.returnValues.update({"clientId":clientId})
        
        expiry = self.comboBox_6.currentText()
        self.returnValues.update({"expiry":expiry})
		
        spy_qqq_expiry = self.comboBox.currentText()
        self.returnValues.update({"spy_qqq_expiry":spy_qqq_expiry})
        
        bot_startTime = self.textEdit_6.toPlainText()
        self.returnValues.update({"bot_startTime":bot_startTime})
        
        bot_endTime = self.textEdit_7.toPlainText()
        self.returnValues.update({"bot_endTime":bot_endTime})
        
        loss_amount_day = self.textEdit_61.toPlainText()
        self.returnValues.update({"loss_amount_day":loss_amount_day})
        
        timer_in_order = self.textEdit_9.toPlainText()
        self.returnValues.update({"timer_in_order":timer_in_order})
        
        order_timer = self.comboBox_3.currentText()
        self.returnValues.update({"order_timer":order_timer})
        
        candle_time = self.comboBox_4.currentText()
        self.returnValues.update({"candle_time":candle_time})
        
        contract_amount = self.textEdit_20.toPlainText()
        self.returnValues.update({"contract_amount":contract_amount})
        
        order_transmit = self.comboBox_5.currentText()
        self.returnValues.update({"order_transmit":order_transmit})
        
        call_delta = self.textEdit_11.toPlainText()
        self.returnValues.update({"call_delta":call_delta})
        
        put_delta = self.textEdit_12.toPlainText()
        self.returnValues.update({"put_delta":put_delta})
        
        vol_check = self.textEdit_13.toPlainText()
        self.returnValues.update({"vol_check":vol_check})
        
        atr_check = self.textEdit_14.toPlainText()
        self.returnValues.update({"atr_check":atr_check})
        
        active_vol = self.textEdit_15.toPlainText()
        self.returnValues.update({"active_vol":active_vol})
        
        profit_amount_day = self.textEdit_17.toPlainText()
        self.returnValues.update({"profit_amount_day":profit_amount_day})
        
        gap_in_trades = self.textEdit_19.toPlainText()
        self.returnValues.update({"gap_in_trades":gap_in_trades})
        
        stocks_list = self.textEdit_21.toPlainText()
        self.returnValues.update({"stocks_list":stocks_list})

        self.returnValues.update({"log_level":self.label_22})
        print(self.returnValues,'f'*10)
        return self.returnValues
        
        
    def hideBeforeLoad(self):
        self.label_11.hide()
        self.label_12.hide()
        self.label_13.hide()
        self.label_14.hide()
        self.label_15.hide()
        self.label_16.hide()
        self.label_17.hide()
        self.label_19.hide()
        self.label_8.hide()

        self.textEdit_61.hide()
        self.comboBox_5.hide()
        self.textEdit_11.hide()
        self.textEdit_12.hide()
        self.textEdit_13.hide()
        self.textEdit_14.hide()
        self.textEdit_15.hide()
        self.textEdit_17.hide()
        self.textEdit_19.hide()
        

    def enable_advance(self):
        if self.checkBox.isChecked():
            self.label_11.show()
            self.label_12.show()
            self.label_13.show()
            self.label_14.show()
            self.label_15.show()
            self.label_16.show()
            self.label_17.show()
            self.label_19.show()
            self.label_8.show()
            
            self.textEdit_61.show()
            self.comboBox_5.show()
            self.textEdit_11.show()
            self.textEdit_12.show()
            self.textEdit_13.show()
            self.textEdit_14.show()
            self.textEdit_15.show()
            self.textEdit_17.show()
            self.textEdit_19.show()
        else:
            self.hideBeforeLoad()


    def save_data(self):
        self.returnLoadValues()
        import pprint
        pprint.pprint(self.returnValues)
        print();
        ip = self.returnValues["ip"]
        port = self.returnValues["port"]
        clientId = self.returnValues["clientId"]
        expiry = self.returnValues["expiry"]
        spy_qqq_expiry = self.returnValues["spy_qqq_expiry"]
        bot_startTime = self.returnValues["bot_startTime"]
        bot_endTime = self.returnValues["bot_endTime"]
        loss_amount_day = self.returnValues["loss_amount_day"]
        timer_in_order = self.returnValues["timer_in_order"]
        order_timer = self.returnValues["order_timer"]
        candle_time = self.returnValues["candle_time"]
        contract_amount = self.returnValues["contract_amount"]
        order_transmit = self.returnValues["order_transmit"]
        call_delta = self.returnValues["call_delta"]
        put_delta = self.returnValues["put_delta"]
        vol_check = self.returnValues["vol_check"]
        atr_check = self.returnValues["atr_check"]
        active_vol = self.returnValues["active_vol"]
        profit_amount_day = self.returnValues["profit_amount_day"]
        gap_in_trades = self.returnValues["gap_in_trades"]
        stocks_list = self.returnValues["stocks_list"]
        log_level = self.returnValues["log_level"]
        PnL = 0
        tradesTaken = 0
        openTrades = 0
        
        dataToDisplay = "**Trade Config Details **\n\n**Summary**\nStock Lists = {}\nExpiry = {}\nExpiry Timer = {}\nSPY_QQQ Expiry = {}\nMax Amount Per Contract = {}\n\n**Current Trades:**\nPnL = {}\nTrades Taken = {}\nOpen Trades = {}\n\n**Advance Configuration Details:**\nBOT Start Time = {}\nBOT End Time = {}\nLoss Amount Day = {}\nProfit Amount Day = {}\nTimer On/Off = {}\nCandle Time = {}\nOrder Transmit = {}\nCall Delta = {}\nPut Delta = {}\nVolumn Check = {}\nATR Check = {}\nActive Volumn = {}\nGap Time In Same Stocks = {}"
        dataDisplay = dataToDisplay.format(stocks_list, expiry, timer_in_order, spy_qqq_expiry, contract_amount, PnL, tradesTaken, openTrades, bot_startTime, bot_endTime, loss_amount_day, profit_amount_day, order_timer, candle_time, order_transmit, call_delta, put_delta, vol_check, atr_check, active_vol, gap_in_trades)
        log_level.setText(dataDisplay)
        
        
    def startExecution(self):
        returnValues = self.returnLoadValues()
        threadCount = QThreadPool.globalInstance().maxThreadCount()
        pool = QThreadPool.globalInstance()
        runnable = Runnable(returnValues)
        pool.start(runnable.startFunction)
        
    def squareOffExecution(self):
        returnValues = self.returnLoadValues()
        threadCount = QThreadPool.globalInstance().maxThreadCount()
        pool = QThreadPool.globalInstance()
        runnable = Runnable(returnValues)
        pool.start(runnable.squareOffEvent)
        time.sleep(2)
        sys.exit(1)
        
        
     
# Runnable class for system execution
class Runnable(QRunnable):
    def __init__(self, returnValues):
        super().__init__()
        #print("YESSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSSS\n"*10);
        self.returnValues = returnValues
        ip = self.returnValues["ip"]
        port = self.returnValues["port"]
        clientId = self.returnValues["clientId"]
        expiry = self.returnValues["expiry"]
        spy_qqq_expiry = self.returnValues["spy_qqq_expiry"]
        bot_startTime = self.returnValues["bot_startTime"]
        bot_endTime = self.returnValues["bot_endTime"]
        loss_amount_day = self.returnValues["loss_amount_day"]
        timer_in_order = self.returnValues["timer_in_order"]
        order_timer = self.returnValues["order_timer"]
        candle_time = self.returnValues["candle_time"]
        contract_amount = self.returnValues["contract_amount"]
        order_transmit = self.returnValues["order_transmit"]
        call_delta = self.returnValues["call_delta"]
        put_delta = self.returnValues["put_delta"]
        vol_check = self.returnValues["vol_check"]
        atr_check = self.returnValues["atr_check"]
        active_vol = self.returnValues["active_vol"]
        profit_amount_day = self.returnValues["profit_amount_day"]
        gap_in_trades = self.returnValues["gap_in_trades"]
        stocks_list = self.returnValues["stocks_list"]
        log_level = self.returnValues["log_level"]

        # Update Config.Json File.
        with open("config.json", "r") as config_file:
            self.data = json.loads(config_file.read())
            
        #print("Assign data = {}\n\n".format(self.data))
        
        self.data["expiryToTrade"] = expiry
        if "same" in spy_qqq_expiry:
            self.data["SPY_QQQ_EXPIRY"] = getExpiry(expiry)
        else:
            self.data["SPY_QQQ_EXPIRY"] = "20230623"
        self.data["USE_DIFF_EXPIRY_INDEX"] = "yes"
        self.data["IP"] = ip
        self.data["PORT"] = int(port)
        self.data["CLIENTID"] = int(clientId)
        self.data["marketStartTime"] = "19:00:00"
        self.data["scriptStartTime"] = bot_startTime.replace(":","")
        self.data["scriptEndTime"] = bot_endTime.replace(":","")
        self.data["loss_amount_day"] = int(loss_amount_day)
        if order_transmit.lower() == "true":
            self.data["ORDER_TRANSMIT"] = True
        else:
            self.data["ORDER_TRANSMIT"] = False
        self.data["USE_TIMER_IN_ORDER"] = order_timer.upper()
        self.data["ORDER_EXPIRY_TIMER"] = int(timer_in_order)
        self.data["CALL_DELTA_CHECK"] = float(call_delta)
        self.data["PUT_DELTA_CHECK"] = float(put_delta)
        self.data["VOLUME_CHECK"] = int(vol_check)
        self.data["ATR_CHECK"] = float(atr_check)
        self.data["ACTIVE_VOLUME"] = int(active_vol)
        self.data["MAX_CONTRACT_AMOUNT"] = int(contract_amount)
        self.data["profit_amount_day"] = int(profit_amount_day)
        self.data["fetchValue"] = "1 D"
        self.data["candleTime"] = candle_time
        self.data["distance_between_trade"] = int(gap_in_trades)
        stock_amount_dict = {}
        stockListToTrade = {}
        stockList = stocks_list.split(",")
        for each in stockList:
            eachSplit= each.split(":")
            stock = eachSplit[0].replace('"','').strip()
            stock_amount_dict.update({stock:{"amount":int(contract_amount)}})
        self.data["stockData"] = stock_amount_dict
        
        for each in stockList:
            eachSplit= each.split(":")
            stock = eachSplit[0].replace('"', '').strip()
            exchange = eachSplit[1].replace('"', '').strip()
            stockListToTrade.update({stock:exchange})
            
        self.data["stockListToTrade"] = stockListToTrade
        
        with open("config.json", "w") as config_file_wrt:
            config_file_wrt.write(json.dumps(self.data).__str__())

        with open("config.json", "r") as config_file_read:
            new_read = json.loads(config_file_read.read())
            
        
    def startFunction(self):
        #returnValues = self.returnLoadValues()
        thread = threading.Thread(target=main_call, args=(self.data,), daemon=True)
        thread.start()
         
        # Calling Main Function to trigger the System
        print("NOW I GET CALL")
        
    def squareOffEvent(self):
        #returnValues = self.returnLoadValues()
        thread2 = threading.Thread(target=squareOffAll, args=(), daemon=True)
        thread2.start()
         
        # Calling Main Function to trigger the System
        print("NOW I SQUAREOFF ALL")


class ExampleApp(QtWidgets.QMainWindow, Ui_Frame):
    def __init__(self, parent=None):
        super(ExampleApp, self).__init__(parent)
        licensed = is_license_valid()
        if not licensed:
            sys.exit()
            sys.exit(0)
            sys.exit(1)
        self.setupUi(self)

def main():
    app = QApplication(sys.argv)
    form = ExampleApp()
    form.show()
    app.exec_()
    


if __name__ == '__main__':
    main()