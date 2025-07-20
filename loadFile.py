from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication
import sys, os, time

from datetime import datetime

def decrypt_time(time):
    time_list = time.split("-")
    new_val = []
    for each in time_list:
        each = each.replace("0", "a").replace("1", "b").replace("2", "c").replace("3", "d").replace("4", "e").replace("5", "f").replace("6", "g").replace("7", "h").replace("8", "i").replace("9", "j")
        new_val.append(each)

    return '-'.join(new_val)


def encrypt_time(time):
    time_list = time.split("-")
    new_val = []
    for each in time_list:
        each = each.replace("a", "0").replace("b", "1").replace("c", "2").replace("d", "3").replace("e", "4").replace("f", "5").replace("g", "6").replace("h", "7").replace("i", "8").replace("j", "9")
        new_val.append(each)

    return '-'.join(new_val)

getCwd = os.getcwd()
dateFile = getCwd+"/crypto.txt"

if os.path.isfile(dateFile):
    #print("File is present")
    with open(dateFile, "r") as readFile:
        data = readFile.read()
    data = data.strip().replace("\n", "")
    currentTime = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    startTime = encrypt_time(data)
    startDate = startTime.split("-")[2]
    currentDate = currentTime.split("-")[2]
    #print("startDate and currentDate are = {} and {}".format(startDate, currentDate))
    if int(currentDate)-int(startDate) > 6:
        print("Your License has Expired, Please Contact +91-9461651867 (whatsapp too) For License Renewal")
        exit(1)
else:
    #print("File is not present")
    startDate = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    with open(dateFile, "w") as firstFile:
        firstFile.write(decrypt_time(startDate))
        
        
with open(dateFile, "r") as readFile:
    data1 = readFile.read()
data1 = data1.strip().replace("\n", "")
currentTime = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
startTime = encrypt_time(data1)
startDate = startTime.split("-")[2]
currentDate = currentTime.split("-")[2]

day_remains = 6 - (int(currentDate) - int(startDate))

print("***********************************************************************\n\t\tDay Remains License To Expire = {}\n***********************************************************************".format(day_remains))
time.sleep(7)

import GUI

class ExampleApp(QtWidgets.QMainWindow, GUI.Ui_Frame):
    def __init__(self, parent=None):
        super(ExampleApp, self).__init__(parent)
        self.setupUi(self)

def main():
    app = QApplication(sys.argv)
    form = ExampleApp()
    form.show()
    app.exec_()

if __name__ == '__main__':
    main()