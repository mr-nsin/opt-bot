import tkinter as tk
import json
from tkinter import ttk
from tkinter import PhotoImage
from PIL import Image, ImageTk
from BOT import main_call
import threading
import psutil
from common import getExpiry
import os
import time
from datetime import datetime
from PyQt5.QtCore import QThreadPool, QRunnable
import concurrent.futures

from collections import ChainMap

def decrypt_time(time):
    time_list = time.split("-")
    new_val = []
    for each in time_list:
        each = each.replace("0", "a").replace("1", "b").replace("2", "c").replace("3", "d").replace(
            "4", "e").replace("5", "f").replace("6", "g").replace("7", "h").replace("8", "i").replace("9", "j")
        new_val.append(each)

    return '-'.join(new_val)


def encrypt_time(time):
    time_list = time.split("-")
    new_val = []
    for each in time_list:
        each = each.replace("a", "0").replace("b", "1").replace("c", "2").replace("d", "3").replace(
            "e", "4").replace("f", "5").replace("g", "6").replace("h", "7").replace("i", "8").replace("j", "9")
        new_val.append(each)

    return '-'.join(new_val)


getCwd = os.getcwd()
dateFile = getCwd+"/crypto.txt"

if os.path.isfile(dateFile):
    # print("File is present")
    with open(dateFile, "r") as readFile:
        data = readFile.read()
    # data = data.decode("utf-8").strip()
    # data = data.strip().replace("\n", "")
    currentTime = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    startTime = encrypt_time(data)
    startDate = startTime.split("-")[2]
    currentDate = currentTime.split("-")[2]
    # print("startDate and currentDate are = {} and {}".format(startDate, currentDate))
    if int(currentDate)-int(startDate) > 6:
        print("Your License has Expired, Please Contact +91-9461651867 (whatsapp too) For License Renewal")
        exit(1)
else:
    # print("File is not present")
    startDate = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
    with open(dateFile, "w") as firstFile:
        firstFile.write(decrypt_time(startDate))


with open(dateFile, "r") as readFile:
    data1 = readFile.read()
# data1 = data1.decode("utf-8").strip()
# data1 = data1.strip().replace("\n", "")
currentTime = datetime.now().strftime("%y-%m-%d-%H-%M-%S")
startTime = encrypt_time(data1)
startDate = startTime.split("-")[2]
currentDate = currentTime.split("-")[2]

day_remains = 6 - (int(currentDate) - int(startDate))

print("***********************************************************************\n\t\tDay Remains License To Expire = {}\n***********************************************************************".format(day_remains))
time.sleep(1)


default_expiry = ["current", "next"]
vwap_values = ["ON", "OFF"]
order_expiry_timer = ["ON", "OFF"]
order_transmit = ["True", "False"]
candle_time_set = ["5 mins", "3 mins", "1 min", "15 mins",
                   "30 mins", "1 hour", "2 hours", "3 hours", "4 hours", "1 day"]


class Runnable(QRunnable):
    def __init__(self,new_read):
        super().__init__()

        main_call(new_read)


class MyApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("Tkinter Example")
        self.root.geometry("1100x650")
        self.root.configure(bg='#000000')
        # self.root.atrributes('-zoomed', False)
        self.root.resizable(0, 0)
        self.root.title('LevelUp')

        self.widgets_to_disable = []

        # self.icon = tk.PhotoImage(file='trading.ico')
        self.icon = Image.open('trading.ico')
        self.icon = ImageTk.PhotoImage(self.icon)
        self.root.iconphoto(True, self.icon)

        self.cache_of_stock_list = []

        self.cache_of_advance_options_labes = []
        self.cache_of_advance_options_inputs = []

        self.cache_valeus = tk.IntVar(value=0)
        self.onse_advance_option_display = False
        self.checkbox = tk.Checkbutton(self.root, variable=self.cache_valeus, font=(
            "Helvetica", 11, 'bold'), text="Advance Option", command=self.check_advance_options)
        self.checkbox.place(x=573, y=115)

        self.short_key = {
            'dropdown_expiry': 'expiry',
            'dropdown_spy_qqq_expiry': 'spy_qqq_expiry',
            'bot_start_time_input': 'bot_startTime',
            'close_time_input': 'bot_endTime',
            'vwap_on_off_input': 'vwap_value',
            'timer_in_order_input': 'timer_in_order',
            'order_expiry_timer_input': 'order_timer',
            'candel_time_input': 'candle_time',
            'max_contract_amount_input': 'contract_amount',
            'Order_Transmit': 'order_transmit',
            'CALL Delta': 'call_delta',
            'PUT Delta': 'put_delta',
            'Volumn Check': 'vol_check',
            'ATR Check': 'atr_check',
            'Active Volumn': 'active_vol',
            "perDayTrades": "perDayTrades",
            'Gap B/W Trades': 'gap_in_trades',
            'Stock List': 'stocks_list',
            'tws_ip': 'ip',
            'tws_port': 'port',
            'tws_id': 'clientId'}

        self.string_vars_local_tws_local_tws = {
            "tws_ip": tk.StringVar(value="127.0.0.1"),
            "tws_port": tk.StringVar(value="7497"),
            "tws_id": tk.StringVar(value="0")
        }

        self.input_values_of_right_side_of_frame_two = {
            "Order_Transmit": tk.StringVar(value="True"),
            "CALL Delta": tk.StringVar(value="0.35"),
            "PUT Delta": tk.StringVar(value="-0.35"),
            "Volumn Check": tk.StringVar(value="100"),
            "ATR Check": tk.StringVar(value="0.047"),
            "Active Volumn": tk.StringVar(value="5"),
            "perDayTrades": tk.StringVar(value="3"),
            "Gap B/W Trades": tk.StringVar(value="300"),
            "Stock List": tk.StringVar(value='"SPY":"NASDAQ"')
        }

        self.input__values_of_left_side_of_frame_two = {
            "dropdown_expiry": tk.StringVar(value="current"),
            "dropdown_spy_qqq_expiry": tk.StringVar(value="same as expiry"),
            "bot_start_time_input": tk.StringVar(value="15:45"),
            "close_time_input": tk.StringVar(value="09:35"),
            "vwap_on_off_input": tk.StringVar(value="ON"),
            "timer_in_order_input": tk.StringVar(value="15"),
            "order_expiry_timer_input": tk.StringVar(value="ON"),
            "candel_time_input": tk.StringVar(value=candle_time_set[0]),
            "max_contract_amount_input": tk.StringVar(value="350")
        }

        self.saver_json_file_dict = dict.fromkeys(['profit_increment', 'expiryToTrade', 'SPY_QQQ_EXPIRY', 'USE_DIFF_EXPIRY_INDEX', 'IP', 'PORT', 'CLIENTID', 'SWITCH_DB', 'ACCOUNT_ID', 'marketStartTime', 'scriptStartTime', 'scriptEndTime', 'VWAP_ON_OFF', 'ORDER_TRANSMIT', 'USE_TIMER_IN_ORDER', 'ORDER_EXPIRY_TIMER', 'CALL_DELTA_CHECK',
                                                  'PUT_DELTA_CHECK', 'VOLUME_CHECK', 'ATR_CHECKS', 'ACTIVE_VOLUME', 'MAX_CONTRACT_AMOUNT', 'ATR_VALUE', 'SHARE_VOLUME', 'BODY', 'MIDPOINT_OFFSET', 'QUANTITY', 'fetchValue', 'candleTime', 'distance_between_trade', 'AVG_VOLUMNS_CANDLES', 'stockData', 'stockListToTrade', 'ATR_CHECK', 'perDayTrades'], None)

        self.the_top_label = tk.Label(self.root, text="Tws Configuration", font=(
            "Helvetica", 14), bg="#282a36", fg="#f8f8f2")
        self.the_top_label.place(x=10, y=20)

        self.frame1 = tk.Frame(self.root, width=700, height=60, bg="#000000",
                               highlightthickness=1, highlightbackground="#f8f8f2")

        self.the_top_label_2 = tk.Label(self.root, text="System Configuration", font=(
            "Helvetica", 10), bg="#282a36", fg="#f8f8f2")
        self.the_top_label_2.place(x=10, y=120)

        self.frame2 = tk.Frame(self.root, width=700, height=500, bg="#000000",
                               highlightthickness=1, highlightbackground="#f8f8f2")
        self.setup_wws_Configuration()

        self.system_configuration_label()
        self.system_config_inputs()

        if self.cache_valeus.get() != 0:
            self.the_second_labes_of_options()

        self.frame2.place(x=11, y=140)

        self.the_top_label_3 = tk.Label(self.root, text="Logs ", font=(
            "Helvetica", 12, "bold"), bg="#282a36", fg="#f8f8f2")
        self.the_top_label_3.place(x=730, y=210)

        self.frame3 = tk.Frame(self.root, width=350, height=400, bg="#000000",
                               highlightthickness=1, highlightbackground="#f8f8f2")

        self.text_widget = tk.Text(self.frame3, font=("Arial", 12))

        self.text_widget.place(x=0, y=0)
        # text_widget.pack(fill=tk.BOTH, expand=True)

        self.frame3.place(x=730, y=238)

        self.add_the_frame_for_buttons()

        self.submit_and_save_buttons()

        self.frame6 = tk.Frame(self.frame2, width=400,
                               height=500, bg="#f8f8f2")

    def check_advance_options(self):

        # x-coordinate for labels
        x_labels = [370] * len(self.cache_of_advance_options_labes)
        # y-coordinates for labels
        y_labels = [
            20 + 50 * i for i in range(len(self.cache_of_advance_options_labes))]

        # x-coordinate for entry widgets
        x_entries = [530] * len(self.cache_of_advance_options_inputs)
        # y-coordinates for entry widgets
        y_entries = [
            15 + 50 * i for i in range(len(self.cache_of_advance_options_inputs))]

        if self.cache_valeus.get() == 1 and not self.onse_advance_option_display:
            self.the_second_labes_of_options()
        elif self.cache_valeus.get() == 1 and self.onse_advance_option_display:
            # self.the_second_labes_of_options();

            for index, labes in enumerate(self.cache_of_advance_options_labes):
                labes.place(x=x_labels[index], y=y_labels[index])

            for index, inputs in enumerate(self.cache_of_advance_options_inputs):
                inputs.place(x=x_entries[index], y=y_entries[index])

        elif self.onse_advance_option_display and self.cache_valeus.get() == 0:
            for labes_inputs in self.cache_of_advance_options_labes + self.cache_of_advance_options_inputs:
                # labes_inputs.destroy()
                labes_inputs.place(x=700, y=0)


    def run_main(self,new_read):
        # pool = QThreadPool.globalInstance()
        # runnable = Runnable()
        # pool.start(runnable)
        # Call the main function with the provided configuration data
        threadCount = QThreadPool.globalInstance().maxThreadCount()
        pool = QThreadPool.globalInstance()
        runnable = Runnable(new_read)
        pool.start(runnable)
        
        # with concurrent.futures.ThreadPoolExecutor() as executor:
        # # Submit the task and get a Future object
        #     future = executor.submit(main_call, new_read)

        
    def run_the_main_tws_code(self):
        
        self.disable_right_left_side_widgets()
        self.save_button.configure(state='disabled')
        self.submit_button.configure(state="disabled")
        
        with open("config.json", "r") as config_file_read:
            new_read = json.loads(config_file_read.read())
        
        # multiprocessing.Process(target=main_call,args=(new_read,))
        # # process2 = multiprocessing.Process(target=other_function)
        # # self.run_main()
        # thread_1 = threading.Thread(target=self.run_main,args=(new_read,))
        # thread_1.start()

        self.run_main(new_read)
        
    def submit_and_save_buttons(self):

        self.frame5 = tk.Frame(self.root, width=350, height=60, bg="#000000",
                               highlightthickness=1, highlightbackground="#f8f8f2")

        self.save_button = tk.Button(self.frame5, text="SAVE", width=10, font=(
            "Helvetica", 14, 'bold'), bg="#f1fa8c", command=self.save_the_data_to_json)
        # save_button.pack(side=tk.LEFT, padx=10)
        self.save_button.place(x=40, y=12)

        # Create a SUBMIT button and add it to the frame
        self.submit_button = tk.Button(self.frame5, text="START", width=10, font=("Helvetica", 14, 'bold'), command=self.run_the_main_tws_code,
                                       bg="#f1fa8c")
        self.submit_button.configure(state='disabled')
        # submit_button.pack(side=tk.LEFT, padx=10)
        self.submit_button.place(x=180, y=12)

        # self.widgets_to_disable.extend([submit_button])

        self.frame5.place(x=730, y=140)

    def save_the_data_to_json(self):
        self.text_widget.config(state="normal")
        PnL = 0
        tradesTaken = 0
        openTrades = 0

        """all_dict_values_ = self.input__values_of_left_side_of_frame_two | self.input_values_of_right_side_of_frame_two

        all_dict_values = {k: float(v.get()) if v.get().replace(".", "", 1).isdigit() else v.get()
                           for k, v in all_dict_values_.items()}

        all_dict_values = all_dict_values | {k: int(v.get()) if v.get().replace(".", "", 1).isdigit() else v.get()
                                             for k, v in self.string_vars_local_tws_local_tws.items()}"""

        all_dict_values_ = ChainMap(self.input__values_of_left_side_of_frame_two, self.input_values_of_right_side_of_frame_two)

        all_dict_values = {k: float(v.get()) if v.get().replace(".", "", 1).isdigit() else v.get()
                           for k, v in all_dict_values_.items()}


        all_dict_values = ChainMap(all_dict_values, {k: int(v.get()) if v.get().replace(".", "", 1).isdigit() else v.get()
                                             for k, v in self.string_vars_local_tws_local_tws.items()})

        values = {self.short_key[short]: all_dict_values[short]
                  for short in self.short_key}
        
        try:
            values['stocks_list'] = self.Stock_List.get("1.0", "end-1c");
        except:
            values['stocks_list'] = self.input_values_of_right_side_of_frame_two["Stock List"].get();
        # print(values)

        dataToDisplay = "**Trade Config Details **\n\n**Summary**\nStock Lists = {}\nExpiry = {}\nExpiry Timer = {}\nSPY_QQQ Expiry = {}\nMax Amount Per Contract = {}\n\n**Current Trades:**\nPnL = {}\nTrades Taken = {}\nOpen Trades = {}\n\n**Advance Configuration Details:**\nBOT Start Time = {}\nBOT End Time = {}\nVWAP = {}\nTimer On/Off = {}\nCandle Time = {}\nOrder Transmit = {}\nCall Delta = {}\nPut Delta = {}\nVolumn Check = {}\nATR Check = {}\nActive Volumn = {}\nGap Time In Same Stocks = {}"

        dataDisplay = dataToDisplay.format(
            values['stocks_list'], values['expiry'], values['timer_in_order'], values['spy_qqq_expiry'],
            values['contract_amount'], PnL, tradesTaken, openTrades, values['bot_startTime'], values['bot_endTime'],
            values['vwap_value'], values['order_timer'], values['candle_time'], values['order_transmit'],
            values['call_delta'], values['put_delta'], values['vol_check'], values['atr_check'],
            values['active_vol'], values['gap_in_trades']
        )

        self.text_widget.delete("1.0", "end")
        self.text_widget.insert("1.0", dataDisplay)
        self.text_widget.config(state="disabled")
        self.submit_button.configure(state='normal')

        self.return_and_save_update_the_data_to_config_json(values)

    def return_and_save_update_the_data_to_config_json(self, returnValues):
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
        perDayTrades = self.returnValues["perDayTrades"]
        gap_in_trades = self.returnValues["gap_in_trades"]
        stocks_list = self.returnValues["stocks_list"]

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
        data["scriptStartTime"] = bot_startTime.replace(":", "")
        data["scriptEndTime"] = bot_endTime.replace(":", "")
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
        data["perDayTrades"] = 3
        data["fetchValue"] = "1 D"
        data["candleTime"] = candle_time
        data["distance_between_trade"] = int(gap_in_trades)
        stock_amount_dict = {}
        stockListToTrade = {}
        stockList = stocks_list.split(",")
        for each in stockList:
            eachSplit = each.split(":")
            stock = eachSplit[0].replace('"', '').strip()
            stock_amount_dict.update({stock: {"amount": int(contract_amount)}})
        data["stockData"] = stock_amount_dict

        for each in stockList:
            eachSplit = each.split(":")
            stock = eachSplit[0].replace('"', '').strip()
            exchange = eachSplit[1].replace('"', '').strip()
            stockListToTrade.update({stock: exchange})

        data["stockListToTrade"] = stockListToTrade

        with open("config.json", "w") as config_file_wrt:
            config_file_wrt.write(json.dumps(data, indent=2).__str__())

        from pprint import pprint

        pprint(data)

        return True

    def add_the_frame_for_buttons(self):
        # Load the image
        frame4 = tk.Frame(self.root, width=350, height=100,
                          highlightthickness=1, highlightbackground="#f8f8f2")
        frame4.pack(fill=tk.BOTH, expand=True)

        # Load the image

        try:
            image_path = r"test-img\blakc_logo.jpg"
            self.image = Image.open(image_path).resize((340, 90))
            self.image = ImageTk.PhotoImage(self.image)
        except:
            image_path = r"test-img/blakc_logo.jpg"
            self.image = Image.open(image_path).resize((340, 90))
            self.image = ImageTk.PhotoImage(self.image)

        # Create a Label to display the image inside frame4
        image_label = tk.Label(frame4, image=self.image)
        image_label.place(x=0, y=0, relwidth=1, relheight=1)

        frame4.place(x=730, y=25)

    def system_config_inputs(self):

        # Create Combobox and Entry widgets using the dictionary values
        dropdown_expiry = ttk.Combobox(self.frame2,state="readonly", values=["current", "next"], font=(
            "Arial", 14), width=10, textvariable=self.input__values_of_left_side_of_frame_two["dropdown_expiry"],)
        dropdown_expiry.place(x=200, y=18)

        dropdown_spy_qqq_expiry = ttk.Combobox(self.frame2,state="readonly", values=["same as expiry"], font=(
            "Arial", 14), width=10, textvariable=self.input__values_of_left_side_of_frame_two["dropdown_spy_qqq_expiry"])
        dropdown_spy_qqq_expiry.place(x=200, y=18 + 50)

        bot_start_time_input = tk.Entry(self.frame2, width=11, font=(
            "Arial", 14), textvariable=self.input__values_of_left_side_of_frame_two["bot_start_time_input"])
        bot_start_time_input.place(x=200, y=18 + (50 * 2) - 5)

        # close_time_input
        close_time_input = tk.Entry(self.frame2, width=11, font=(
            "Arial", 14), textvariable=self.input__values_of_left_side_of_frame_two["close_time_input"])
        close_time_input.place(x=200, y=18 + (50 * 3) - 5)

        vwap_on_off_input = ttk.Combobox(self.frame2,state="readonly", values=["ON", "OFF"], font=(
            "Arial", 14), width=10, textvariable=self.input__values_of_left_side_of_frame_two["vwap_on_off_input"])
        vwap_on_off_input.place(x=200, y=18 + (50 * 4) - 5)

        timer_in_order_input = tk.Entry(self.frame2, width=11, font=(
            "Arial", 14), textvariable=self.input__values_of_left_side_of_frame_two["timer_in_order_input"])
        timer_in_order_input.place(x=200, y=18 + (50 * 5) - 5)

        order_expiry_timer_input = ttk.Combobox(self.frame2,state="readonly", values=order_expiry_timer, font=(
            "Arial", 14), width=10, textvariable=self.input__values_of_left_side_of_frame_two["order_expiry_timer_input"])
        order_expiry_timer_input.place(x=200, y=18 + (50 * 6) - 5)

        candel_time_input = ttk.Combobox(self.frame2,state="readonly", values=candle_time_set, font=(
            "Arial", 14), width=10, textvariable=self.input__values_of_left_side_of_frame_two["candel_time_input"])
        candel_time_input.place(x=200, y=18 + (50 * 7) - 5)

        max_contract_amount_input = tk.Entry(self.frame2, width=11, font=(
            "Arial", 14), textvariable=self.input__values_of_left_side_of_frame_two["max_contract_amount_input"])
        max_contract_amount_input.place(x=200, y=18 + (50 * 8) - 5)

        self.widgets_to_disable.extend([
            dropdown_expiry, dropdown_spy_qqq_expiry, bot_start_time_input,
            close_time_input, vwap_on_off_input, timer_in_order_input,
            order_expiry_timer_input, candel_time_input, max_contract_amount_input
        ])

    def the_second_labes_of_options(self):
        label_names = [
            "Order Transmit:",
            "CALL Delta:",
            "PUT Delta:",
            "Volumn Check:",
            "ATR Check:",
            "Active Volumn:",
            "Trades Per Day:",
            "Gap B/W Trades:",
            "Stock List:"]
        for i, label_name in enumerate(label_names):
            label = tk.Label(self.frame2, text=label_name, font=(
                "Helvetica", 11, 'bold'), bg="#000000", fg="#f8f8f2")
            label.place(x=370, y=20 + 50 * i)
            self.cache_of_advance_options_labes.append(label)

        Order_Transmit = ttk.Combobox(self.frame2,state="readonly", values=["True", "False"], font=(
            "Arial", 14), width=10, textvariable=self.input_values_of_right_side_of_frame_two["Order_Transmit"])
        Order_Transmit.place(x=530, y=15)

        # Create Entry widgets for other labels (CALL Delta to Gap B/W Trades)
        entry_CALL_Delta = tk.Entry(self.frame2, font=(
            "Arial", 14), width=11, textvariable=self.input_values_of_right_side_of_frame_two["CALL Delta"])
        entry_CALL_Delta.place(x=530, y=15 + 50)

        entry_PUT_Delta = tk.Entry(self.frame2, font=(
            "Arial", 14), width=11, textvariable=self.input_values_of_right_side_of_frame_two["PUT Delta"])
        entry_PUT_Delta.place(x=530, y=15 + 50 * 2)

        entry_Volumn_Check = tk.Entry(self.frame2, font=(
            "Arial", 14), width=11, textvariable=self.input_values_of_right_side_of_frame_two["Volumn Check"])
        entry_Volumn_Check.place(x=530, y=15 + 50 * 3)

        entry_ATR_Check = tk.Entry(self.frame2, font=(
            "Arial", 14), width=11, textvariable=self.input_values_of_right_side_of_frame_two["ATR Check"])
        entry_ATR_Check.place(x=530, y=15 + 50 * 4)

        entry_Active_Volumn = tk.Entry(self.frame2, font=(
            "Arial", 14), width=11, textvariable=self.input_values_of_right_side_of_frame_two["Active Volumn"])
        entry_Active_Volumn.place(x=530, y=15 + 50 * 5)

        entry_perDayTrades = tk.Entry(self.frame2, font=(
            "Arial", 14), width=11, textvariable=self.input_values_of_right_side_of_frame_two["perDayTrades"])
        entry_perDayTrades.place(x=530, y=15 + 50 * 6)

        entry_Gap_BW_Trades = tk.Entry(self.frame2, font=(
            "Arial", 14), width=11, textvariable=self.input_values_of_right_side_of_frame_two["Gap B/W Trades"])
        entry_Gap_BW_Trades.place(x=530, y=15 + 50 * 7)

        # Create Text widget for "Stock List"
        self.Stock_List = tk.Text(self.frame2, font=(
            "Arial", 10), wrap=tk.WORD, height=4, width=20)
        self.Stock_List.insert(
            "1.0", self.input_values_of_right_side_of_frame_two["Stock List"].get())
        self.Stock_List.place(x=530, y=15 + 50 * 8)

        self.cache_of_stock_list.append(self.Stock_List)

        self.widgets_to_disable.extend([
            Order_Transmit, entry_CALL_Delta, entry_PUT_Delta,
            entry_Volumn_Check, entry_ATR_Check, entry_Active_Volumn,
            entry_perDayTrades, entry_Gap_BW_Trades, self.Stock_List
        ])
        self.onse_advance_option_display = True
        self.cache_of_advance_options_inputs.extend([Order_Transmit, entry_CALL_Delta, entry_PUT_Delta,
                                                     entry_Volumn_Check, entry_ATR_Check, entry_Active_Volumn,
                                                     entry_perDayTrades, entry_Gap_BW_Trades, self.Stock_List
                                                     ])

    def get_stock_list_value(self, event):
        # Get the text from the Text widget
        stock_list_value = event.widget.get("1.0", "end-1c")
        self.input_values_of_right_side_of_frame_two["Stock List"].set(
            stock_list_value)

    def system_configuration_label(self):
        label_info = [
            ("Expiry:", 20),
            ("SPY/QQQ Expiry:", 70),
            ("BOT Start Time:", 120),
            ("Close Time:", 120 + 50),
            ("VWAP ON/OFF:", 120 + 50 + 50),
            ("Timer In Order:", 120 + 50 * 3),
            ("Order Expiry Timer:", 120 + 50 * 4),
            ("Candle Time:", 120 + 50 * 5),
            ("Max Contract Amount:", 120 + 50 * 6)
        ]

        for text, y in label_info:

            label = tk.Label(self.frame2, text=text, font=(
                "Helvetica", 11, 'bold'), bg="#000000", fg="#f8f8f2")
            label.place(x=10, y=y)

    def setup_wws_Configuration(self):

        tws_ip_label = tk.Label(self.frame1, text="TWS IP:", font=(
            "System", 10), bg="#000000", fg="#f8f8f2")
        tws_ip_label.place(x=10, y=20)

        tws_port_label = tk.Label(self.frame1, text="TWS PORT:", font=(
            "System", 10), bg="#000000", fg="#f8f8f2")
        tws_port_label.place(x=220, y=20)

        tws_id_label = tk.Label(self.frame1, text="TWS ID:", font=(
            "System", 10), bg="#000000", fg="#f8f8f2")
        tws_id_label.place(x=450, y=20)

        # Entry widgets
        tws_ip_entry = tk.Entry(
            self.frame1, width=10, textvariable=self.string_vars_local_tws_local_tws["tws_ip"], font=("Arial", 16))
        tws_ip_entry.place(x=70, y=15)

        tws_port_entry = tk.Entry(
            self.frame1, width=10, textvariable=self.string_vars_local_tws_local_tws["tws_port"], font=("Arial", 16))
        tws_port_entry.place(x=305, y=15)

        tws_id_entry = tk.Entry(
            self.frame1, width=10, textvariable=self.string_vars_local_tws_local_tws["tws_id"], font=("Arial", 16))
        tws_id_entry.place(x=515, y=15)

        self.frame1.place(x=11, y=45)

        self.widgets_to_disable.extend(
            [tws_ip_entry, tws_port_entry, tws_id_entry])

    def disable_right_left_side_widgets(self):
        for widget in self.widgets_to_disable:
            widget.configure(state='disabled')


def main():
    root = tk.Tk()
    app = MyApplication(root)
    root.protocol("WM_DELETE_WINDOW", at_exit_close_the_thread)
    root.mainloop()


def at_exit_close_the_thread():
    # atexit.register()
    print("")
    pid = os.getpid()
    target_pid = pid
    try:
        # Get the process object for the target PID
        process = psutil.Process(target_pid)
        print("**********************************************\n\t\t LevelUp = Terminate\n*******************************************")
        process.terminate()
        print(f"Process with PID {target_pid} has been terminated.")
    except psutil.NoSuchProcess:
        print(f"Process with PID {target_pid} does not exist.")

if __name__ == "__main__":
    gui_thread = threading.Thread(target=main)
    gui_thread.start()