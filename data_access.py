import sqlite3
from typing import List
from threading import Thread, Lock
from queue import Queue
from common import OptionOrder, logger


class DAL:
    def __init__(self) -> None:
        # Create the SQLite database
        self.orders_queue = Queue()
        self.lock = Lock()
        self.keep_running = False
        self.orders_thread = Thread(target=self.handle_orders_queue)
        self.orders_thread.start()

    def handle_orders_queue(self) -> None:
        """
        Continuously listens to the orders queue and handles incoming orders.

        The function listens for new orders, updates to existing orders, and deletions
        of orders from the queue. It takes appropriate action for each type of item
        received, including inserting new orders into the database, updating existing
        orders in the database, and deleting orders from the database.

        Returns:
            None
        """

        # logs a message to indicate that the function has started
        logger.info("starting handle orders queue")

        # connects to the orders database and initializes it
        self.conn = sqlite3.connect('db/orders.db')
        self.init()

        # sets up the initial state of the function
        self.keep_running = True
        self.orders = self.get_all_option_orders()

        # continuously listens to the orders queue and handles incoming orders
        while self.keep_running:

            # gets the next item from the orders queue
            item_data = self.orders_queue.get()

            # takes appropriate action depending on the type of item received
            if item_data["item_type"] == "new":
                # inserts a new order into the database
                self.insert_order(new_order=item_data["order"])
            elif item_data["item_type"] == "update":
                # updates an existing order in the database
                self.update_option_order(option_order=item_data["order"])
            elif item_data["item_type"] == "delete":
                # deletes an order from the database
                self.delete_option_order(order_id=item_data["id"])

            # signals to the orders queue that the item has been processed
            self.orders_queue.task_done()


    def put(self, item_data)-> None:
        self.orders_queue.put(item=item_data)

    def update(self, order: OptionOrder)-> None:
        self.orders_queue.put(item={"item_type":"update", "order": order})

    def delete(self, order: OptionOrder)-> None:
        self.orders_queue.put(item={"item_type": "delete", "id": order.id})

    def init(self) -> None:
        try:
            cursor = self.conn.cursor()
            # Create the table if it does not already exist
            cursor.execute('''CREATE TABLE IF NOT EXISTS option_orders
                        (id INTEGER PRIMARY KEY,
                        conId INTEGER,
                        symbol TEXT,
                        expiration TEXT,
                        strike REAL,
                        right TEXT,
                        order_type TEXT,
                        order_side TEXT,
                        order_qty INTEGER,
                        order_price REAL,
                        order_status TEXT,
                        executed_qty INTEGER,
                        average_price REAL,
                        profit_price REAL,
                        stoploss_price REAL,
                        profit_trigger INTEGER,
                        current_profit_price REAL,
                        profit_increment REAL,
                        contract TEXT,
                        exit_placed INTEGER,
                        exit_order INTEGER,
                        active INTEGER,
                        ref_order_id INTEGER)''')

            # Save the changes and close the connection
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"An error occurred: {e.args[0]}")

    def insert_order(self, new_order: OptionOrder)-> None:
        try:
            logger.info(f"insert_order: {new_order}")
            with self.lock:
                cursor = self.conn.cursor()
                cursor.execute('''INSERT INTO option_orders (
                                id,
                                conId,
                                symbol,
                                expiration,
                                strike,
                                right,
                                order_type,
                                order_side,
                                order_qty,
                                order_price,
                                order_status,
                                executed_qty,
                                average_price,
                                profit_price,
                                stoploss_price,
                                profit_trigger,
                                current_profit_price,
                                profit_increment,
                                exit_placed,
                                exit_order,
                                active,
                                ref_order_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (new_order.id,
                        new_order.conId,
                        new_order.symbol,
                        new_order.expiration,
                        new_order.strike,
                        new_order.right,
                        new_order.order_type,
                        new_order.order_side,
                        new_order.order_qty,
                        new_order.order_price,
                        new_order.order_status,
                        new_order.executed_qty,
                        new_order.average_price,
                        new_order.profit_price,
                        new_order.stoploss_price,
                        new_order.profit_trigger,
                        new_order.current_profit_price,
                        new_order.profit_increment,
                        # new_order.contract,
                        new_order.exit_placed,
                        new_order.exit_order,
                        new_order.active,
                        new_order.ref_order_id))

                # Save the changes and close the connection
                self.conn.commit()
        except sqlite3.Error as ex:
            logger.error(f"An error occurred while inserting order into the database: {ex}", exc_info=True)

    def get_all_option_orders(self) -> List[OptionOrder]:
        logger.info("get all option orders")
        c = self.conn.cursor()
        # Retrieve all rows from the option_orders table
        c.execute("SELECT * FROM option_orders")
        rows = c.fetchall()

        # Create a list of OptionOrder objects from the retrieved rows
        option_orders = []
        for row in rows:
            option_order = OptionOrder(
                id=row[0],
                conId=row[1],
                symbol=row[2],
                expiration=row[3],
                strike=row[4],
                right=row[5],
                order_type=row[6],
                order_side=row[7],
                order_qty=row[8],
                order_price=row[9],
                order_status=row[10],
                executed_qty=row[11],
                average_price=row[12],
                profit_price=row[13],
                stoploss_price=row[14],
                profit_trigger=row[15],
                current_profit_price=row[16],
                profit_increment=row[17],
                # contract=row[18],
                exit_placed=row[19],
                exit_order=row[20],
                active=row[21],
                ref_order_id=row[22])
            logger.info(option_order)
            option_orders.append(option_order)

        return option_orders
    
    from typing import Union

    def update_option_order(self, option_order: OptionOrder) -> bool:
        """
        Updates an existing option order in the database based on its ID.

        Args:
            option_order (OptionOrder): The option order to update.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        try:
            with self.lock:
                cursor = self.conn.cursor()
                # Update the option order in the database
                query = f"UPDATE option_orders SET order_status = '{option_order.order_status}', executed_qty = {option_order.executed_qty}, average_price = {option_order.average_price},profit_price = {option_order.profit_price},profit_trigger = {option_order.profit_trigger}, current_profit_price = {option_order.current_profit_price},profit_increment = {option_order.profit_increment} WHERE id = {option_order.id}"
                logger.info(f"update_option_order: {query}")
                cursor.execute(query)
                # Save the changes and close the connection
                self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"An error occurred: {e.args[0]}")
            return False

    def delete_option_order(self, order_id: int) -> bool:
        """
        Deletes an existing option order from the database based on its ID.

        Args:
            order_id (int): The ID of the option order to delete.

        Returns:
            bool: True if the delete was successful, False otherwise.
        """
        try:
            logger.info(f"delete_option_order: OrderID: {order_id}")
            with self.lock:
                cursor = self.conn.cursor()
                # Delete the option order from the database
                cursor.execute('''DELETE FROM option_orders WHERE id = ?''', (order_id,))
                if cursor.rowcount == 0:
                    # No rows were affected, i.e. there was no matching record in the database
                    print(f"No option order with ID {order_id} found in the database")
                    return False

                # Save the changes and close the connection
                self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.info(f"An error occurred: {e.args[0]}")
            return False