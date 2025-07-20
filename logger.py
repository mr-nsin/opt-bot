import os, sys
import logging
from logging import handlers
from datetime import datetime
from logging.handlers import RotatingFileHandler

		
class Loggers(object):

    def __init__(self, logFileName):
        print('Initializing Logging Object')
        self.logFileName=logFileName
        logPath = os.getcwd()+'\\Logs\\'+self.logFileName
        print("Created log file in - ",  logPath)
        self.logFilePath = logPath
        self.logging=logging.getLogger(self.logFilePath)
        self.logging.setLevel(logging.DEBUG)
        self.consoleHandler=logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.consoleHandler.setFormatter(formatter)		
        self.fileHandler=handlers.RotatingFileHandler(self.logFilePath, maxBytes=(9048576*500), backupCount=10)
        self.fileHandler.setFormatter(formatter)
        self.logging.addHandler(self.fileHandler)
        self.logging.addHandler(self.consoleHandler)

    def info(self, msg):
        self.logging.info(msg)

    def debug(self, msg):
        self.logging.debug(msg)

    def error(self, msg):
        self.logging.error(msg)
		
    def warning(self, msg):
        self.logging.warning(msg)