"""
Tradovate API client for futures trading
Handles authentication, order management, and position tracking
"""

import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

from utils.logger import trading_logger


class TradovateClient:
    def __init__(self, username, password, client_id, client_secret, app_id,
                 base_url="https://demo.tradovateapi.com/v1"):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret
        self.app_id = app_id
        self.base_url = base_url
        self.session = requests.Session()
        self.access_token_expiry_time = None
        self.auth_token = None
        self.account_id = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            'Authorization': '',
        }
        
        # Connection status
        self.is_authenticated = False
        self.last_auth_time = None
        
        trading_logger.info(f"Tradovate client initialized for {base_url}")

    def authenticate(self) -> bool:
        """Authenticate and obtain the API token"""
        for attempt in range(3):
            try:
                self.session = requests.Session()
                response = self.session.post(
                    f"{self.base_url}/auth/accesstokenrequest",
                    json={
                        "name": self.username,
                        "password": self.password,
                        "appId": self.app_id,
                        "sec": self.client_secret,
                        "deviceId": "",
                        "cid": self.client_id
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                auth_data = response.json()
                self.auth_token = auth_data["accessToken"]
                self.headers['Authorization'] = f'Bearer {self.auth_token}'
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                self.access_token_expiry_time = datetime.now() + timedelta(minutes=75)
                self.is_authenticated = True
                self.last_auth_time = datetime.now()
                
                trading_logger.info("Tradovate authentication successful")
                return True
                
            except Exception as e:
                trading_logger.error(f"Authentication attempt {attempt + 1} failed: {e}")
                time.sleep(3)
                
        self.is_authenticated = False
        return False

    def validate_token(self) -> bool:
        """Validate and refresh token if needed"""
        if not self.access_token_expiry_time or datetime.now() >= self.access_token_expiry_time:
            trading_logger.info("Token expired, re-authenticating...")
            return self.authenticate()
        return self.is_authenticated

    def get_account_list(self) -> Optional[List[Dict]]:
        """Get list of available accounts"""
        if not self.validate_token():
            return None
            
        for attempt in range(2):
            try:
                response = self.session.get(f'{self.base_url}/account/list', headers=self.headers, timeout=30)
                response.raise_for_status()
                accounts = response.json()
                trading_logger.info(f"Retrieved {len(accounts)} accounts")
                return accounts
            except Exception as e:
                trading_logger.error(f"Error getting account list (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def get_contract(self, symbol: str) -> Optional[Dict]:
        """Get contract information for a symbol"""
        if not self.validate_token():
            return None
            
        for attempt in range(2):
            try:
                response = self.session.get(
                    f'{self.base_url}/contract/find?name={symbol}', 
                    headers=self.headers, 
                    timeout=30
                )
                response.raise_for_status()
                contract = response.json()
                trading_logger.debug(f"Retrieved contract info for {symbol}")
                return contract
            except Exception as e:
                trading_logger.error(f"Error getting contract for {symbol} (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def get_positions(self) -> Optional[List[Dict]]:
        """Get current positions"""
        if not self.validate_token():
            return None
            
        for attempt in range(2):
            try:
                response = self.session.get(f'{self.base_url}/position/list', headers=self.headers, timeout=30)
                response.raise_for_status()
                positions = response.json()
                trading_logger.debug(f"Retrieved {len(positions)} positions")
                return positions
            except Exception as e:
                trading_logger.error(f"Error getting positions (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def get_order(self, order_id: int) -> Optional[Dict]:
        """Get order information by ID"""
        if not self.validate_token():
            return None
            
        for attempt in range(2):
            try:
                response = self.session.get(
                    f'{self.base_url}/order/item?id={order_id}', 
                    headers=self.headers, 
                    timeout=30
                )
                response.raise_for_status()
                order = response.json()
                trading_logger.debug(f"Retrieved order {order_id}")
                return order
            except Exception as e:
                trading_logger.error(f"Error getting order {order_id} (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def place_order(self, symbol: str, side: str, quantity: int, order_type: str = "Market", 
                   price: Optional[float] = None, stop_price: Optional[float] = None) -> Optional[Dict]:
        """Place a trading order"""
        if not self.validate_token():
            return None

        # Get contract info first
        contract = self.get_contract(symbol)
        if not contract:
            trading_logger.error(f"Cannot place order: contract not found for {symbol}")
            return None

        order_data = {
            "accountSpec": self.account_id,
            "accountId": self.account_id,
            "clOrdId": str(int(time.time() * 1000)),
            "action": "Buy" if side.upper() == "BUY" else "Sell",
            "symbol": symbol,
            "orderQty": quantity,
            "orderType": order_type,
            "timeInForce": "Day"
        }

        if order_type == "Limit" and price:
            order_data["price"] = price
        elif order_type == "Stop" and stop_price:
            order_data["stopPrice"] = stop_price

        for attempt in range(2):
            try:
                response = self.session.post(
                    f'{self.base_url}/order/placeorder',
                    json=order_data,
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                trading_logger.info(f"Order placed successfully: {side} {quantity} {symbol}")
                return result
            except Exception as e:
                trading_logger.error(f"Error placing order (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def place_oco_order(self, symbol: str, side: str, quantity: int, entry_price: float,
                       stop_loss: float, take_profit: float) -> Optional[Dict]:
        """Place OCO (One-Cancels-Other) bracket order"""
        if not self.validate_token():
            return None

        # First place the entry order
        entry_order = self.place_order(symbol, side, quantity, "Limit", entry_price)
        if not entry_order:
            return None

        # Then place OCO bracket orders
        try:
            # This is a simplified OCO implementation
            # Real implementation would depend on Tradovate's specific OCO API
            oco_data = {
                "accountId": self.account_id,
                "symbol": symbol,
                "quantity": quantity,
                "side": "Sell" if side.upper() == "BUY" else "Buy",
                "stopLoss": stop_loss,
                "takeProfit": take_profit,
                "parentOrderId": entry_order.get("orderId")
            }
            
            trading_logger.info(f"OCO bracket order setup for {symbol}: SL={stop_loss}, TP={take_profit}")
            return {"entry_order": entry_order, "oco_setup": oco_data}
            
        except Exception as e:
            trading_logger.error(f"Error setting up OCO order: {e}")
            return None

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order"""
        if not self.validate_token():
            return False
            
        for attempt in range(2):
            try:
                response = self.session.post(
                    f'{self.base_url}/order/cancelorder',
                    json={"orderId": order_id},
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                trading_logger.info(f"Order {order_id} cancelled successfully")
                return True
            except Exception as e:
                trading_logger.error(f"Error cancelling order {order_id} (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return False

    def modify_order(self, order_id: int, new_price: Optional[float] = None, 
                    new_quantity: Optional[int] = None) -> Optional[Dict]:
        """Modify an existing order"""
        if not self.validate_token():
            return None

        modify_data = {"orderId": order_id}
        if new_price:
            modify_data["price"] = new_price
        if new_quantity:
            modify_data["orderQty"] = new_quantity

        for attempt in range(2):
            try:
                response = self.session.post(
                    f'{self.base_url}/order/modifyorder',
                    json=modify_data,
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                result = response.json()
                trading_logger.info(f"Order {order_id} modified successfully")
                return result
            except Exception as e:
                trading_logger.error(f"Error modifying order {order_id} (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def get_account_balance(self) -> Optional[Dict]:
        """Get account balance and margin information"""
        if not self.validate_token():
            return None
            
        for attempt in range(2):
            try:
                response = self.session.get(
                    f'{self.base_url}/account/item?id={self.account_id}',
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
                balance = response.json()
                trading_logger.debug("Retrieved account balance")
                return balance
            except Exception as e:
                trading_logger.error(f"Error getting account balance (attempt {attempt + 1}): {e}")
                time.sleep(2)
        return None

    def set_account_id(self, account_id: int):
        """Set the trading account ID"""
        self.account_id = account_id
        trading_logger.info(f"Account ID set to: {account_id}")

    def get_connection_status(self) -> Dict:
        """Get connection status information"""
        return {
            "authenticated": self.is_authenticated,
            "last_auth_time": self.last_auth_time,
            "token_expires": self.access_token_expiry_time,
            "base_url": self.base_url,
            "account_id": self.account_id
        }

    def close_all_positions(self, reason: str = "Manual close") -> List[Dict]:
        """Close all open positions"""
        positions = self.get_positions()
        if not positions:
            return []

        closed_positions = []
        for position in positions:
            try:
                if position.get('netPos', 0) != 0:
                    # Close position by placing opposite order
                    side = "Sell" if position['netPos'] > 0 else "Buy"
                    quantity = abs(position['netPos'])
                    symbol = position['symbol']
                    
                    result = self.place_order(symbol, side, quantity, "Market")
                    if result:
                        closed_positions.append({
                            "symbol": symbol,
                            "quantity": quantity,
                            "side": side,
                            "reason": reason,
                            "order_result": result
                        })
                        trading_logger.info(f"Closed position: {side} {quantity} {symbol}")
                        
            except Exception as e:
                trading_logger.error(f"Error closing position {position}: {e}")

        return closed_positions
