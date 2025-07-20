import os, time, json
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRunnable, Qt, QThreadPool

from common import getExpiry
from BOT import main_call


default_expiry = ["current", "next"]
vwap_values = ["ON", "OFF"]
order_expiry_timer = ["ON", "OFF"]
order_transmit = ["True", "False"]
candle_time_set = ["5 mins", "3 mins", "1 min", "15 mins", "30 mins", "1 hour", "2 hours", "3 hours", "4 hours", "1 day"]

class Ui_Frame(object):
    def setupUi(self, Frame):
        Frame.setObjectName("Frame")
        Frame.resize(1334, 846)
        font = QtGui.QFont()
        font.setPointSize(11)
        Frame.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("../../../../COMPANY_TREETECH/COMPANY_DATA/Level Up (Black _ Gold Transparent).png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        Frame.setWindowIcon(icon)
        Frame.setWindowTitle("LevelUP")

        self.groupBox = QtWidgets.QGroupBox(Frame)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 871, 91))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        self.groupBox.setFont(font)
        self.groupBox.setStyleSheet("")
        self.groupBox.setObjectName("groupBox")
        self.groupBox.setTitle("TWS Configuratoin")

        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(10, 50, 71, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.label.setText("TWS IP :")

        self.textEdit = QtWidgets.QTextEdit(self.groupBox)
        self.textEdit.setGeometry(QtCore.QRect(90, 40, 161, 41))
        self.textEdit.setObjectName("textEdit")
        self.textEdit.setText("127.0.0.1")

        self.label_2 = QtWidgets.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(270, 50, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label_2.setFont(font)
        self.label_2.setObjectName("label_2")
        self.label_2.setText("TWS PORT :")

        self.textEdit_2 = QtWidgets.QTextEdit(self.groupBox)
        self.textEdit_2.setGeometry(QtCore.QRect(380, 40, 161, 41))
        self.textEdit_2.setObjectName("textEdit_2")
        self.textEdit_2.setText("7497")

        self.label_3 = QtWidgets.QLabel(self.groupBox)
        self.label_3.setGeometry(QtCore.QRect(560, 50, 81, 31))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.label_3.setText("TWS ID :")

        self.textEdit_3 = QtWidgets.QTextEdit(self.groupBox)
        self.textEdit_3.setGeometry(QtCore.QRect(640, 40, 161, 41))
        self.textEdit_3.setObjectName("textEdit_3")
        self.textEdit_3.setText("0")

        self.groupBox_2 = QtWidgets.QGroupBox(Frame)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 110, 871, 721))
        font = QtGui.QFont()
        font.setPointSize(11)
        font.setBold(False)
        font.setWeight(50)
        self.groupBox_2.setFont(font)
        self.groupBox_2.setObjectName("groupBox_2")
        self.groupBox_2.setTitle("System Configuration")

        self.label_4 = QtWidgets.QLabel(self.groupBox_2)
        self.label_4.setGeometry(QtCore.QRect(20, 40, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_4.setFont(font)
        self.label_4.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.label_4.setAlignment(QtCore.Qt.AlignCenter)
        self.label_4.setObjectName("label_4")
        self.label_4.setText("Expiry :")

        """self.textEdit_4 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_4.setGeometry(QtCore.QRect(210, 40, 161, 41))
        self.textEdit_4.setTabChangesFocus(True)
        self.textEdit_4.setObjectName("textEdit_4")
        self.textEdit_4.setPlaceholderText("Expiry To Trade")"""
        
        self.comboBox_6 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_6.setGeometry(QtCore.QRect(210, 40, 161, 41))
        self.comboBox_6.setEditable(True)
        self.comboBox_6.setObjectName("comboBox")
        self.comboBox_6.addItems(default_expiry)

        self.label_5 = QtWidgets.QLabel(self.groupBox_2)
        self.label_5.setGeometry(QtCore.QRect(20, 100, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_5.setFont(font)
        self.label_5.setAlignment(QtCore.Qt.AlignCenter)
        self.label_5.setObjectName("label_5")
        self.label_5.setText("SPY/QQQ Expiry :")

        self.label_6 = QtWidgets.QLabel(self.groupBox_2)
        self.label_6.setGeometry(QtCore.QRect(20, 160, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_6.setFont(font)
        self.label_6.setAlignment(QtCore.Qt.AlignCenter)
        self.label_6.setObjectName("label_6")
        self.label_6.setText("BOT Start Time :")

        self.label_7 = QtWidgets.QLabel(self.groupBox_2)
        self.label_7.setGeometry(QtCore.QRect(10, 220, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_7.setFont(font)
        self.label_7.setScaledContents(False)
        self.label_7.setAlignment(QtCore.Qt.AlignCenter)
        self.label_7.setObjectName("label_7")
        self.label_7.setText("Close Time :")

        self.label_8 = QtWidgets.QLabel(self.groupBox_2)
        self.label_8.setGeometry(QtCore.QRect(20, 290, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_8.setFont(font)
        self.label_8.setAlignment(QtCore.Qt.AlignCenter)
        self.label_8.setObjectName("label_8")
        self.label_8.setText("VWAP ON/OFF :")

        self.label_9 = QtWidgets.QLabel(self.groupBox_2)
        self.label_9.setGeometry(QtCore.QRect(20, 360, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_9.setFont(font)
        self.label_9.setAlignment(QtCore.Qt.AlignCenter)
        self.label_9.setObjectName("label_9")
        self.label_9.setText("Timer In Order :")

        self.label_10 = QtWidgets.QLabel(self.groupBox_2)
        self.label_10.setGeometry(QtCore.QRect(10, 420, 171, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_10.setFont(font)
        self.label_10.setAlignment(QtCore.Qt.AlignCenter)
        self.label_10.setObjectName("label_10")
        self.label_10.setText("Order Expiry Timer :")

        self.label_11 = QtWidgets.QLabel(self.groupBox_2)
        self.label_11.setGeometry(QtCore.QRect(400, 40, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_11.setFont(font)
        self.label_11.setAlignment(QtCore.Qt.AlignCenter)
        self.label_11.setObjectName("label_11")
        self.label_11.setText("Order Transmit :")

        self.label_12 = QtWidgets.QLabel(self.groupBox_2)
        self.label_12.setGeometry(QtCore.QRect(420, 100, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_12.setFont(font)
        self.label_12.setAlignment(QtCore.Qt.AlignCenter)
        self.label_12.setObjectName("label_12")
        self.label_12.setText("CALL Delta :")

        self.textEdit_6 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_6.setGeometry(QtCore.QRect(210, 160, 161, 41))
        self.textEdit_6.setTabChangesFocus(True)
        self.textEdit_6.setObjectName("textEdit_6")
        self.textEdit_6.setPlaceholderText("System Start Time")
        self.textEdit_6.setText("09:35")

        self.textEdit_7 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_7.setGeometry(QtCore.QRect(210, 220, 161, 41))
        self.textEdit_7.setTabChangesFocus(True)
        self.textEdit_7.setObjectName("textEdit_7")
        self.textEdit_7.setPlaceholderText("System End Time")
        self.textEdit_7.setText("15:45")

        self.textEdit_9 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_9.setGeometry(QtCore.QRect(210, 350, 161, 41))
        self.textEdit_9.setTabChangesFocus(True)
        self.textEdit_9.setObjectName("textEdit_9")
        self.textEdit_9.setPlaceholderText("Timer In Order")
        self.textEdit_9.setText("15")

        self.textEdit_11 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_11.setGeometry(QtCore.QRect(590, 100, 161, 41))
        self.textEdit_11.setTabChangesFocus(True)
        self.textEdit_11.setObjectName("textEdit_11")
        self.textEdit_11.setPlaceholderText("CALL Delta Strike")
        self.textEdit_11.setText("0.35")

        self.textEdit_12 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_12.setGeometry(QtCore.QRect(590, 160, 161, 41))
        self.textEdit_12.setTabChangesFocus(True)
        self.textEdit_12.setObjectName("textEdit_12")
        self.textEdit_12.setPlaceholderText("PUT Delta Strike")
        self.textEdit_12.setText("-0.35")

        self.textEdit_13 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_13.setGeometry(QtCore.QRect(590, 230, 161, 41))
        self.textEdit_13.setTabChangesFocus(True)
        self.textEdit_13.setObjectName("textEdit_13")
        self.textEdit_13.setPlaceholderText("Trade Volumn Check")
        self.textEdit_13.setText("100")

        self.textEdit_14 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_14.setGeometry(QtCore.QRect(590, 290, 161, 41))
        self.textEdit_14.setTabChangesFocus(True)
        self.textEdit_14.setObjectName("textEdit_14")
        self.textEdit_14.setPlaceholderText("ATR Checks")
        self.textEdit_14.setText("0.047")
        
        self.textEdit_15 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_15.setGeometry(QtCore.QRect(590, 350, 161, 41))
        self.textEdit_15.setTabChangesFocus(True)
        self.textEdit_15.setObjectName("textEdit_15")
        self.textEdit_15.setPlaceholderText("Active Volumn Check")
        self.textEdit_15.setText("5")

        self.label_13 = QtWidgets.QLabel(self.groupBox_2)
        self.label_13.setGeometry(QtCore.QRect(420, 160, 121, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_13.setFont(font)
        self.label_13.setAlignment(QtCore.Qt.AlignCenter)
        self.label_13.setObjectName("label_13")
        self.label_13.setText("PUT Delta :")

        self.label_14 = QtWidgets.QLabel(self.groupBox_2)
        self.label_14.setGeometry(QtCore.QRect(410, 230, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_14.setFont(font)
        self.label_14.setAlignment(QtCore.Qt.AlignCenter)
        self.label_14.setObjectName("label_14")
        self.label_14.setText("Volumn Check :")

        self.label_15 = QtWidgets.QLabel(self.groupBox_2)
        self.label_15.setGeometry(QtCore.QRect(410, 290, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_15.setFont(font)
        self.label_15.setAlignment(QtCore.Qt.AlignCenter)
        self.label_15.setObjectName("label_15")
        self.label_15.setText("ATR Check :")

        self.label_16 = QtWidgets.QLabel(self.groupBox_2)
        self.label_16.setGeometry(QtCore.QRect(410, 350, 141, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_16.setFont(font)
        self.label_16.setAlignment(QtCore.Qt.AlignCenter)
        self.label_16.setObjectName("label_16")
        self.label_16.setText("Active Volumn :")

        self.label_17 = QtWidgets.QLabel(self.groupBox_2)
        self.label_17.setGeometry(QtCore.QRect(410, 410, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_17.setFont(font)
        self.label_17.setAlignment(QtCore.Qt.AlignCenter)
        self.label_17.setObjectName("label_17")
        self.label_17.setText("Mid Point Offset  :")

        self.label_18 = QtWidgets.QLabel(self.groupBox_2)
        self.label_18.setGeometry(QtCore.QRect(0, 480, 171, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_18.setFont(font)
        self.label_18.setAlignment(QtCore.Qt.AlignCenter)
        self.label_18.setObjectName("label_18")
        self.label_18.setText("Candle Time :")

        self.label_19 = QtWidgets.QLabel(self.groupBox_2)
        self.label_19.setGeometry(QtCore.QRect(400, 490, 171, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_19.setFont(font)
        self.label_19.setAlignment(QtCore.Qt.AlignCenter)
        self.label_19.setObjectName("label_19")
        self.label_19.setText("Gap B/W Trades :")

        self.textEdit_17 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_17.setGeometry(QtCore.QRect(590, 410, 161, 41))
        self.textEdit_17.setTabChangesFocus(True)
        self.textEdit_17.setObjectName("textEdit_17")
        self.textEdit_17.setPlaceholderText("Mid Point Offset")
        self.textEdit_17.setText("0.01")

        self.label_20 = QtWidgets.QLabel(self.groupBox_2)
        self.label_20.setGeometry(QtCore.QRect(10, 550, 161, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_20.setFont(font)
        self.label_20.setAlignment(QtCore.Qt.AlignCenter)
        self.label_20.setObjectName("label_20")
        self.label_20.setText("Max Contract\n"
"Amount :")

        self.label_21 = QtWidgets.QLabel(self.groupBox_2)
        self.label_21.setGeometry(QtCore.QRect(410, 560, 171, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_21.setFont(font)
        self.label_21.setAlignment(QtCore.Qt.AlignCenter)
        self.label_21.setObjectName("label_21")
        self.label_21.setText("Stock List :")

        self.textEdit_19 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_19.setGeometry(QtCore.QRect(590, 480, 161, 41))
        self.textEdit_19.setTabChangesFocus(True)
        self.textEdit_19.setObjectName("textEdit_19")
        self.textEdit_19.setPlaceholderText("Seconds Gap B/W Trades")
        self.textEdit_19.setText("300")

        self.comboBox = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox.setGeometry(QtCore.QRect(210, 100, 161, 41))
        self.comboBox.setEditable(True)
        self.comboBox.setObjectName("comboBox")
        self.comboBox.setCurrentText("same as expiry")

        self.comboBox_2 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_2.setGeometry(QtCore.QRect(210, 290, 161, 41))
        self.comboBox_2.setEditable(False)
        self.comboBox_2.setCurrentText("")
        self.comboBox_2.setObjectName("comboBox_2")
        self.comboBox_2.addItems(vwap_values)

        self.textEdit_20 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_20.setGeometry(QtCore.QRect(210, 550, 161, 41))
        self.textEdit_20.setTabChangesFocus(True)
        self.textEdit_20.setObjectName("textEdit_20")
        self.textEdit_20.setPlaceholderText("Max Amt Contract")
        self.textEdit_20.setText("350")

        self.comboBox_3 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_3.setGeometry(QtCore.QRect(210, 420, 161, 41))
        self.comboBox_3.setEditable(False)
        self.comboBox_3.setCurrentText("")
        self.comboBox_3.setObjectName("comboBox_3")
        self.comboBox_3.addItems(order_expiry_timer)

        self.comboBox_4 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_4.setGeometry(QtCore.QRect(210, 480, 161, 41))
        self.comboBox_4.setEditable(False)
        self.comboBox_4.setCurrentText("")
        self.comboBox_4.setObjectName("comboBox_4")
        self.comboBox_4.addItems(candle_time_set)

        self.comboBox_5 = QtWidgets.QComboBox(self.groupBox_2)
        self.comboBox_5.setGeometry(QtCore.QRect(590, 40, 161, 41))
        self.comboBox_5.setEditable(False)
        self.comboBox_5.setCurrentText("")
        self.comboBox_5.setObjectName("comboBox_5")
        self.comboBox_5.addItems(order_transmit)

        self.textEdit_21 = QtWidgets.QTextEdit(self.groupBox_2)
        self.textEdit_21.setGeometry(QtCore.QRect(590, 550, 201, 101))
        self.textEdit_21.setTabChangesFocus(True)
        self.textEdit_21.setObjectName("textEdit_21")
        self.textEdit_21.setPlaceholderText("comma seperate stocks")
        self.textEdit_21.setText('"AAPL":"NASDAQ", "SPY":"NASDAQ", "AMZN":"NASDAQ", "QQQ":"NASDAQ", "NVDA":"NASDAQ", "TSLA":"NASDAQ", "AMD":"NASDAQ", "META":"NASDAQ", "MSFT":"NASDAQ", "NFLX":"NASDAQ"')

        self.groupBox_3 = QtWidgets.QGroupBox(Frame)
        self.groupBox_3.setGeometry(QtCore.QRect(900, 110, 401, 721))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.groupBox_3.setFont(font)
        self.groupBox_3.setAutoFillBackground(False)
        self.groupBox_3.setObjectName("groupBox_3")
        self.groupBox_3.setTitle("LOGS")
        
        self.label_22 = QtWidgets.QLabel(self.groupBox_3)
        self.label_22.setGeometry(QtCore.QRect(10, 30, 381, 681))
        self.label_22.setObjectName("label_22")
        self.label_22.setText("")

        self.groupBox_4 = QtWidgets.QGroupBox(Frame)
        self.groupBox_4.setGeometry(QtCore.QRect(900, 20, 401, 81))
        font = QtGui.QFont()
        font.setPointSize(11)
        self.groupBox_4.setFont(font)
        self.groupBox_4.setStyleSheet("background-image: url(:/test-img/Level Up (Black _ Gold Transparent).png);")
        self.groupBox_4.setTitle("")
        self.groupBox_4.setObjectName("groupBox_4")

        self.pushButton = QtWidgets.QPushButton(self.groupBox_4)
        self.pushButton.setGeometry(QtCore.QRect(30, 10, 161, 61))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pushButton.setFont(font)
        self.pushButton.setStyleSheet("background-color: rgb(255, 255, 127);")
        self.pushButton.setObjectName("pushButton")
        self.pushButton.setText("Save")
        self.pushButton.clicked.connect(self.save_data)

        self.pushButton_2 = QtWidgets.QPushButton(self.groupBox_4)
        self.pushButton_2.setGeometry(QtCore.QRect(220, 10, 161, 61))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.pushButton_2.setFont(font)
        self.pushButton_2.setStyleSheet("background-color: rgb(255, 255, 127);")
        self.pushButton_2.setObjectName("pushButton_2")
        self.pushButton_2.setText("Start")
        self.pushButton_2.clicked.connect(self.startExecution)


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
        
        vwap_value = self.comboBox_2.currentText()
        self.returnValues.update({"vwap_value":vwap_value})
        
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
        
        midpoint_offset = self.textEdit_17.toPlainText()
        self.returnValues.update({"midpoint_offset":midpoint_offset})
        
        gap_in_trades = self.textEdit_19.toPlainText()
        self.returnValues.update({"gap_in_trades":gap_in_trades})
        
        stocks_list = self.textEdit_21.toPlainText()
        self.returnValues.update({"stocks_list":stocks_list})

        self.returnValues.update({"log_level":self.label_22})
        return self.returnValues


    def save_data(self):
        self.returnLoadValues()

        ip = self.returnValues["ip"]
        port = self.returnValues["port"]
        clientId = self.returnValues["clientId"]
        expiry = self.returnValues["expiry"]
        spy_qqq_expiry = self.returnValues["spy_qqq_expiry"]
        bot_startTime = self.returnValues["bot_startTime"]
        bot_endTime = self.returnValues["bot_endTime"]
        vwap_value = self.returnValues["vwap_value"]
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
        midpoint_offset = self.returnValues["midpoint_offset"]
        gap_in_trades = self.returnValues["gap_in_trades"]
        stocks_list = self.returnValues["stocks_list"]
        log_level = self.returnValues["log_level"]
        
        dataToDisplay = "**** Trade Config Details ****\nExpiry= {}\nSPY_QQQ Expiry= {}\nBOT StartTime= {}\nBOT EndTime= {}\nVWAP= {}\nExpiry Timer= {}\nTimer On/Off= {}\nCandle Time= {}\nMax Amount Per Contract= {}\nOrder Transmit= {}\nCall Delta= {}\nPut Delta= {}\nVolumn Check= {}\nATR Check= {}\nActive Volumn= {}\nMidpoint Offset= {}\nGap Time In Same Stock= {}\nStock Lists = {}"
        dataDisplay = dataToDisplay.format(expiry, spy_qqq_expiry, bot_startTime, bot_endTime, vwap_value, timer_in_order, order_timer, candle_time, contract_amount, order_transmit, call_delta, put_delta, vol_check, atr_check, active_vol, midpoint_offset, gap_in_trades, stocks_list)
        log_level.setText(dataDisplay)
        
        
    def startExecution(self):
        returnValues = self.returnLoadValues()
        threadCount = QThreadPool.globalInstance().maxThreadCount()
        pool = QThreadPool.globalInstance()
        runnable = Runnable(returnValues)
        pool.start(runnable)
        
        
        
# Runnable class for system execution 
        
class Runnable(QRunnable):
    def __init__(self, returnValues):
        super().__init__()
        self.returnValues = returnValues
        ip = self.returnValues["ip"]
        port = self.returnValues["port"]
        clientId = self.returnValues["clientId"]
        expiry = self.returnValues["expiry"]
        spy_qqq_expiry = self.returnValues["spy_qqq_expiry"]
        bot_startTime = self.returnValues["bot_startTime"]
        bot_endTime = self.returnValues["bot_endTime"]
        vwap_value = self.returnValues["vwap_value"]
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
        midpoint_offset = self.returnValues["midpoint_offset"]
        gap_in_trades = self.returnValues["gap_in_trades"]
        stocks_list = self.returnValues["stocks_list"]
        log_level = self.returnValues["log_level"]

        # Update Config.Json File.
        with open("config.json", "r") as config_file:
            data = json.loads(config_file.read())
        
        data["expiryToTrade"] = expiry
        if "same" in spy_qqq_expiry:
            data["SPY_QQQ_EXPIRY"] = getExpiry(expiry)
        else:
            data["SPY_QQQ_EXPIRY"] = "20230623"
        data["USE_DIFF_EXPIRY_INDEX"] = "yes"
        data["IP"] = ip
        data["PORT"] = int(port)
        data["CLIENTID"] = int(clientId)
        data["marketStartTime"] = "19:00:00"
        data["scriptStartTime"] = bot_startTime.replace(":","")
        data["scriptEndTime"] = bot_endTime.replace(":","")
        data["VWAP_ON_OFF"] = vwap_value
        if order_transmit.lower() == "true":
            data["ORDER_TRANSMIT"] = True
        else:
            data["ORDER_TRANSMIT"] = False
        data["USE_TIMER_IN_ORDER"] = order_timer.upper()
        data["ORDER_EXPIRY_TIMER"] = int(timer_in_order)
        data["CALL_DELTA_CHECK"] = float(call_delta)
        data["PUT_DELTA_CHECK"] = float(put_delta)
        data["VOLUME_CHECK"] = int(vol_check)
        data["ATR_CHECK"] = float(atr_check)
        data["ACTIVE_VOLUME"] = int(active_vol)
        data["MAX_CONTRACT_AMOUNT"] = int(contract_amount)
        data["MIDPOINT_OFFSET"] = float(midpoint_offset)
        data["fetchValue"] = "1 D"
        data["candleTime"] = candle_time
        data["distance_between_trade"] = int(gap_in_trades)
        stock_amount_dict = {}
        stockListToTrade = {}
        stockList = stocks_list.split(",")
        for each in stockList:
            eachSplit= each.split(":")
            stock = eachSplit[0].replace('"','').strip()
            stock_amount_dict.update({stock:{"amount":int(contract_amount)}})
        data["stockData"] = stock_amount_dict
        
        for each in stockList:
            eachSplit= each.split(":")
            stock = eachSplit[0].replace('"', '').strip()
            exchange = eachSplit[1].replace('"', '').strip()
            stockListToTrade.update({stock:exchange})
            
        data["stockListToTrade"] = stockListToTrade
        
        with open("config.json", "w") as config_file_wrt:
            config_file_wrt.write(json.dumps(data).__str__())

        with open("config.json", "r") as config_file_read:
            new_read = json.loads(config_file_read.read())
            
        # Calling Main Function to trigger the System
        main_call()
        #BOT.main()