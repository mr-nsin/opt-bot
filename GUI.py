import sys, json, os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QProgressBar, QSpinBox, QDoubleSpinBox, QFrame,
    QSplitter, QScrollArea, QCheckBox, QComboBox, QSizePolicy, QTimeEdit
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QPropertyAnimation, QEasingCurve, QTime, QSize
from PyQt5.QtGui import QPixmap, QFont, QPalette, QColor, QPainter
try:
    import qtawesome as qta
except Exception:
    qta = None
from utils.ui_animations import ThemeTransitionManager

import BOT
from multiprocessing import Process


import hashlib
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


LICENSE_FILE = "license.json"
LICENSE_STATE = "license_state.json"

###################### LICENSE VALIDATE VARIABLE #######################################
########################################################################################
IP_Validate = "192.168.0.100"
email_validate = "longnguyen347@yahoo.com"
key_to_validate = "quant-drift-$987$-&x1$(-*0#!("
starting_date = "2025-08-17"
days_to_validate = 10

########################################################################################
########################################################################################


_process = None


########################################################################################
########################################################################################


def generate_fixed_license_key(ip, email, key, days_valid, starting_date):
    license_data = {
        'ip': ip,
        'email': email,
        'key': key,
        'start': starting_date,
        'days': days_valid
    }

    # Convert to string and encode
    json_string = json.dumps(license_data, sort_keys=True)
    encoded = json_string.encode()

    # Use SHA-256 hash to get fixed-length license key
    license_hash = hashlib.sha256(encoded).hexdigest()
    return license_hash
    
def get_expiry_date(starting_date, days_valid):
    start_dt = datetime.strptime(starting_date, "%Y-%m-%d")
    expiry_date = (start_dt + timedelta(days=days_valid)).strftime('%Y-%m-%d')
    return expiry_date

class TradingThread(QThread):
    log_signal = pyqtSignal(str)
    stats_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    price_signal = pyqtSignal(str, float)  # symbol, price

    def __init__(self, profit_limit, loss_limit, trading_mode="demo"):
        super().__init__()
        try:
            self.trader = BOT.main_call()
            self.trader.set_callbacks(
                log_callback=self.log_signal.emit,
                stats_callback=self.stats_signal.emit,
                price_callback=self.price_signal.emit
            )
            
            # Set trading limits in config
            self.trader.config['trading']['daily_profit_limit'] = profit_limit
            self.trader.config['trading']['daily_loss_limit'] = abs(loss_limit)  # Ensure positive
            
            self.trading_mode = trading_mode
            self._running = True
            self.session_started = False
        except Exception as e:
            self.error_signal.emit(f"Failed to initialize trading controller: {str(e)}")

    def run(self):
        try:
            # Start trading system with specified mode
            success = self.trader.start_trading(self.trading_mode)
            if not success:
                self.error_signal.emit("Failed to initialize trading connections")
                return
            
            self.session_started = True
            self.log_signal.emit(f"Trading started in {self.trading_mode} mode")
            
            # Run the main trading loop
            self.trader.run_trading_loop()
            
        except Exception as e:
            self.error_signal.emit(f"Trading error: {str(e)}")

    def stop(self):
        self._running = False
        if hasattr(self, 'trader'):
            # Check for active positions
            active_positions = self.trader.get_current_positions()
            if active_positions:
                self.log_signal.emit(f"Warning: {len(active_positions)} active positions detected")
            
            self.trader.stop_trading()

    def emergency_stop(self):
        self._running = False
        if hasattr(self, 'trader'):
            self.trader.close_all_positions("Emergency stop")
            self.trader.stop_trading()

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LevelUP-PROFESSIONAL OPIONS TRADING SOFTWARE")
        #self.setWindowTitle("QuantDrift-PROFESSIONAL OPIONS TRADING SOFTWARE")
        self.resize(1200, 800)
        # Initialize state
        self.trading_thread = None
        self.connection_status = False
        self.dark_theme = True  # Default to dark theme
        self.license_validated_this_session = False  # Track session validation
        self.trading_mode = "demo"  # Default to demo mode
        self.config = self.load_config()
        self.apply_config_to_ui()
        self.theme_transition = ThemeTransitionManager(self, duration=300)
        if self.dark_theme:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
        self.color = "#17191B"
        print(f"*************COLOR is {self.color}")
        self.init_ui()
        self.update_logo("dark" if self.dark_theme else "white")
        self.setup_timers()
        self.set_controls_enabled(True)
        self.check_license_on_startup()
        
    def update_logo(self, theme="dark"):
        if theme == "dark":
            pixmap = QPixmap("logo/levelup1.png")
            #pixmap = QPixmap("logo/bwquantDrift.png")
            self.color = "#17191B"
        else:
            #pixmap = QPixmap("logo/levelup.jpg")
            self.color = "white"
        self.logo_label.setPixmap(pixmap)

    def check_license_on_startup(self):
        license_path = "config/license.txt"
        show_license_section = True
        if os.path.exists(license_path):
            with open(license_path, "r") as f:
                license_key = f.read().strip()
            valid, message = validate_license(license_key)
            if valid:
                self.license_validated_this_session = True
                show_license_section = False
                self.log_message(f"License check: {message}")
            else:
                self.log_message(f"License check failed: {message}")
        if show_license_section:
            self.license_container.show()
        else:
            self.license_container.hide()

    def load_config(self):
        try:
            with open("config/settings.json", 'r') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_config(self):
        try:
            with open("config/settings.json", 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log_message(f"Failed to save config: {str(e)}")

    def apply_config_to_ui(self):
        # Load all config values into UI state
        trading = self.config.get('trading', {})
        ui = self.config.get('ui', {})
        self.trading_mode = trading.get('mode', 'demo')
        self.dark_theme = (ui.get('theme', 'dark') == 'dark')
        # Example: set other UI properties if present
        self.font_size = ui.get('font_size', 9)
        self.update_interval = ui.get('update_interval', 1000)
        self.animation_duration = ui.get('animation_duration', 300)
        self.smooth_transitions = ui.get('smooth_transitions', True)
        self.show_charts = ui.get('show_charts', True)
        # Risk management
        self.daily_profit_limit = trading.get('daily_profit_limit', 500)
        self.daily_loss_limit = trading.get('daily_loss_limit', -300)
        self.risk_per_trade = trading.get('risk_per_trade', 0.02)
        # Add more as needed

    def sync_ui_to_config(self):
        # Save all UI state to config dict
        self.config.setdefault('trading', {})['mode'] = self.trading_mode
        self.config.setdefault('trading', {})['daily_profit_limit'] = getattr(self, 'profit_input', None).value() if hasattr(self, 'profit_input') else self.daily_profit_limit
        self.config.setdefault('trading', {})['daily_loss_limit'] = getattr(self, 'loss_input', None).value() if hasattr(self, 'loss_input') else self.daily_loss_limit
        self.config.setdefault('trading', {})['risk_per_trade'] = getattr(self, 'risk_input', None).value() if hasattr(self, 'risk_input') else self.risk_per_trade
        self.config.setdefault('ui', {})['theme'] = 'dark' if self.dark_theme else 'light'
        self.config.setdefault('ui', {})['font_size'] = self.font_size if hasattr(self, 'font_size') else 9
        self.config.setdefault('ui', {})['update_interval'] = self.update_interval if hasattr(self, 'update_interval') else 1000
        self.config.setdefault('ui', {})['animation_duration'] = self.animation_duration if hasattr(self, 'animation_duration') else 300
        self.config.setdefault('ui', {})['smooth_transitions'] = self.smooth_transitions if hasattr(self, 'smooth_transitions') else True
        self.config.setdefault('ui', {})['show_charts'] = self.show_charts if hasattr(self, 'show_charts') else True
        # Add more as needed
        self.save_config()

    def save_trading_mode_preference(self):
        """Save trading mode preference to config"""
        self.sync_ui_to_config()

    def save_theme_preference(self):
        """Save theme preference to config"""
        self.sync_ui_to_config()

    def apply_dark_theme(self):
        """Apply professional dark theme"""
        self.setStyleSheet("""
            QWidget {
                background-color: #17191B;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QPushButton {
                background-color: #404040;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px;
                min-width: 100px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            
            QPushButton:pressed {
                background-color: #333;
            }
            
            QPushButton#start_button {
                background-color: #1e5f1e;
                border-color: #2d8f2d;
            }
            
            QPushButton#start_button:hover {
                background-color: #267326;
            }
            
            QPushButton#stop_button {
                background-color: #5f1e1e;
                border-color: #8f2d2d;
            }
            
            QPushButton#stop_button:hover {
                background-color: #732626;
            }
            
            QPushButton#emergency_button {
                background-color: #8b0000;
                border-color: #ff0000;
                color: #ffffff;
            }
            
            QPushButton#theme_button {
                background-color: #0e5db3;
                border-color: #1a73e8;
                color: #ffffff;
                max-width: 160px;
                border-radius: 18px;
                padding: 8px 14px;
            }
            
            QPushButton#theme_button:hover {
                background-color: #1a73e8;
            }
            
            QPushButton#mode_toggle {
                background-color: #2d2f33;
                border-color: #3a3c41;
                color: #e6e6e6;
                font-weight: 600;
                border-radius: 18px;
                padding: 8px 14px;
            }
            
            QPushButton#mode_toggle:hover {
                background-color: #3a3c41;
            }
            
            QPushButton#mode_toggle[mode="live"] {
                background-color: #28a745;
                border-color: #1e7e34;
            }
            
            QPushButton#mode_toggle[mode="live"]:hover {
                background-color: #1e7e34;
            }
            
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #404040;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border-color: #0078d4;
            }
            
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 5px;
            }
            
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2a2a2a;
                border: 1px solid #555;
                gridline-color: #555;
            }
            
            QTableWidget::item {
                padding: 5px;
            }
            
            QLabel#status_connected {
                color: #00ff00;
                font-weight: bold;
            }
            
            QLabel#status_disconnected {
                color: #ff0000;
                font-weight: bold;
            }
            
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #17191B;
            }
            
            QTabBar::tab {
                background-color: #17191B;
                border: 1px solid #555;
                padding: 8px 32px;
                margin-right: 2px;
                color: #ffffff;
                min-width: 150px;
                min-height: 40px;
            }
            
            QTabBar::tab:selected {
                background-color: #17191B;
                border-bottom: 2px solid #0078d4;
            }
            
            QTabBar::tab:hover {
                background-color: #17191B;
            }
        """)

    def apply_light_theme(self):
        """Apply professional light theme"""
        self.color = "#ffffff"
        

        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                color: #17191B;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 8px;
                min-width: 100px;
                font-weight: bold;
                color: #17191B;
            }
            
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #999999;
            }
            
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            
            QPushButton#start_button {
                background-color: #d4edda;
                border-color: #28a745;
                color: #155724;
            }
            
            QPushButton#start_button:hover {
                background-color: #c3e6cb;
            }
            
            QPushButton#stop_button {
                background-color: #f8d7da;
                border-color: #dc3545;
                color: #721c24;
            }
            
            QPushButton#stop_button:hover {
                background-color: #f5c6cb;
            }
            
            QPushButton#emergency_button {
                background-color: #dc3545;
                border-color: #dc3545;
                color: #ffffff;
            }
            
            QPushButton#emergency_button:hover {
                background-color: #c82333;
            }
            
            QPushButton#theme_button {
                background-color: #1a73e8;
                border-color: #1a73e8;
                color: #ffffff;
                max-width: 160px;
                border-radius: 18px;
                padding: 8px 14px;
            }
            
            QPushButton#theme_button:hover {
                background-color: #2b7de9;
            }
            
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
                color: #17191B;
            }
            QPushButton#mode_toggle {
                background-color: #f1f3f4;
                border: 1px solid #dadce0;
                color: #202124;
                font-weight: 600;
                border-radius: 18px;
                padding: 8px 14px;
            }
            QPushButton#mode_toggle:hover {
                background-color: #e8eaed;
            }
            
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 5px;
                color: #17191B;
            }
            
            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8f9fa;
                border: 1px solid #cccccc;
                gridline-color: #cccccc;
                color: #17191B;
            }
            
            QTableWidget::item {
                padding: 5px;
            }
            
            QLabel#status_connected {
                color: #28a745;
                font-weight: bold;
            }
            
            QLabel#status_disconnected {
                color: #dc3545;
                font-weight: bold;
            }
            
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
            
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                padding: 8px 32px;
                margin-right: 2px;
                color: #17191B;
                min-width: 150px;
                min-height: 40px;
            }
            
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 2px solid #0078d4;
            }
        """)

    def toggle_theme(self):
        """Toggle between dark and light themes with smooth animation"""
        try:
            self.dark_theme = not self.dark_theme
            
            # Update button text immediately
            if self.dark_theme:
                self.theme_button.setText("🌙 Dark Theme ")
                self.update_logo("dark")
                self.color = "#17191B"
            else:
                self.theme_button.setText("☀️ Light Theme ")
                self.update_logo("white")
                self.color = "white"
            
            # Try smooth transition first
            try:
                # Set up theme stylesheets for transition
                dark_stylesheet = self.get_dark_theme_stylesheet()
                light_stylesheet = self.get_light_theme_stylesheet()
                self.theme_transition.set_theme_stylesheets(dark_stylesheet, light_stylesheet)
                
                # Start smooth transition
                self.theme_transition.transition_to_theme(self.dark_theme)
                self.theme_transition.transition_completed.connect(self._on_theme_transition_complete)
                
            except Exception as e:
                # Fallback to direct theme application
                print(f"Theme transition failed, applying directly: {e}")
                if self.dark_theme:
                    self.apply_dark_theme()
                else:
                    self.apply_light_theme()
                self._on_theme_transition_complete()
                # Update charts for direct theme application
                self.update_chart_theme()
                
        except Exception as e:
            print(f"Error in toggle_theme: {e}")
            # Revert dark_theme state if error
            self.dark_theme = not self.dark_theme
            try:
                self._apply_theme_button_icon()
            except Exception:
                pass
        
    def _on_theme_transition_complete(self):
        """Called when theme transition animation completes"""
        try:
            # Save preference
            self.save_theme_preference()
            
            # Update stats label colors based on current theme
            if hasattr(self, 'stats_label'):
                if self.dark_theme:
                    self.stats_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ff00;")
                else:
                    self.stats_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #28a745;")
            
            # Refresh connection status styling
            if hasattr(self, 'connection_label'):
                self.connection_label.style().unpolish(self.connection_label)
                self.connection_label.style().polish(self.connection_label)
            
            # Update modern clock icon color and theme button icon
            try:
                self._apply_theme_button_icon()
                icon_color = "#ffffff" if self.dark_theme else "#17191B"
                if hasattr(self, 'time_icon') and qta is not None:
                    self.time_icon.setPixmap(qta.icon("mdi.clock-time-four-outline", color=icon_color).pixmap(QSize(18, 18)))
            except Exception as _:
                pass
            
            # Update chart backgrounds and colors for new theme
            self.update_chart_theme()
            
            # Safely disconnect signal to avoid multiple connections
            try:
                self.theme_transition.transition_completed.disconnect(self._on_theme_transition_complete)
            except:
                pass  # Signal might not be connected
                
        except Exception as e:
            print(f"Error in theme transition complete: {e}")

    def update_chart_theme(self):
        """Update chart backgrounds and colors when theme changes"""
        try:
            # Update the color variable based on current theme
            if self.dark_theme:
                self.color = "#17191B"
                text_color = "#ffffff"
                grid_color = "#555555"
            else:
                self.color = "#ffffff"
                text_color = "#17191B"
                grid_color = "#cccccc"
            
            # Update pie chart
            if hasattr(self, 'pie_fig') and hasattr(self, 'pie_ax'):
                self.pie_fig.patch.set_facecolor(self.color)
                self.pie_ax.set_facecolor(self.color)
                self.pie_ax.tick_params(colors=text_color)
                self.pie_ax.xaxis.label.set_color(text_color)
                self.pie_ax.yaxis.label.set_color(text_color)
                self.pie_ax.title.set_color(text_color)
                # Update spines (borders)
                for spine in self.pie_ax.spines.values():
                    spine.set_color(grid_color)
                self.pie_canvas.draw()
            
            # Update bar chart
            if hasattr(self, 'bar_fig') and hasattr(self, 'bar_ax'):
                self.bar_fig.patch.set_facecolor(self.color)
                self.bar_ax.set_facecolor(self.color)
                self.bar_ax.tick_params(colors=text_color)
                self.bar_ax.xaxis.label.set_color(text_color)
                self.bar_ax.yaxis.label.set_color(text_color)
                self.bar_ax.title.set_color(text_color)
                # Update grid
                self.bar_ax.grid(True, color=grid_color, alpha=0.3)
                # Update spines (borders)
                for spine in self.bar_ax.spines.values():
                    spine.set_color(grid_color)
                self.bar_canvas.draw()
                
        except Exception as e:
            print(f"Error updating chart theme: {e}")

    def get_dark_theme_stylesheet(self):
        """Get dark theme stylesheet"""
        return """
            QWidget {
                background-color: #17191B;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px;
                min-width: 100px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton#start_button {
                background-color: #1e5f1e;
                border-color: #2d8f2d;
            }
            QPushButton#theme_button {
                background-color: #0078d4;
                border-color: #106ebe;
                color: #ffffff;
                max-width: 150px;
            }
            QPushButton#mode_toggle {
                background-color: #ff8c00;
                border-color: #ff7700;
                color: #ffffff;
                font-weight: bold;
            }
            QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background-color: #404040;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QLabel#status_connected {
                color: #00ff00;
                font-weight: bold;
            }
            QLabel#status_disconnected {
                color: #ff0000;
                font-weight: bold;
            }
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #17191B;
            }
            QTabBar::tab {
                background-color: #17191B;
                border: 1px solid #555;
                padding: 8px 32px;
                margin-right: 2px;
                color: #ffffff;
                min-width: 150px;
                min-height: 40px;
            }
            QTabBar::tab:selected {
                background-color: #17191B;
                border-bottom: 2px solid #0078d4;
            }
            QTabBar::tab:hover {
                background-color: #222;
            }
        """

    def get_light_theme_stylesheet(self):
        """Get light theme stylesheet"""
        self.color = "#ffffff"
        return """
            QWidget {
                background-color: #ffffff;
                color: #17191B;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 8px;
                min-width: 100px;
                font-weight: bold;
                color: #17191B;
            }
            
            QPushButton:hover {
                background-color: #e0e0e0;
                border-color: #999999;
            }
            
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
            
            QPushButton#start_button {
                background-color: #d4edda;
                border-color: #28a745;
                color: #155724;
            }
            
            QPushButton#theme_button {
                background-color: #0078d4;
                border-color: #106ebe;
                color: #ffffff;
                max-width: 150px;
            }
            
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
                color: #17191B;
            }
            
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 5px;
                color: #17191B;
            }
            
            QLabel#status_connected {
                color: #28a745;
                font-weight: bold;
            }
            
            QLabel#status_disconnected {
                color: #dc3545;
                font-weight: bold;
            }
            
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
            }
            
            QTabBar::tab {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                padding: 8px 32px;
                margin-right: 2px;
                color: #17191B;
                min-width: 150px;
                min-height: 40px;
            }
            
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 2px solid #0078d4;
            }
        """

    def _apply_theme_button_icon(self):
        """Set a modern icon on the theme button based on current theme"""
        try:
            if not hasattr(self, 'theme_button'):
                return
            if qta is not None:
                icon_name = "mdi.white-balance-sunny" if self.dark_theme else "mdi.moon-waning-crescent"
                icon_color = "#ffffff" if self.dark_theme else "#17191B"
                icon = qta.icon(icon_name, color=icon_color)
                self.theme_button.setIcon(icon)
                self.theme_button.setIconSize(QSize(18, 18))
        except Exception as _:
            pass

    def toggle_trading_mode(self):
        """Toggle between demo and live trading modes"""
        if self.trading_mode == "demo":
            # Confirm switch to live mode
            reply = QMessageBox.question(
                self, 'Switch to Live Trading',
                '⚠️ WARNING: You are about to switch to LIVE TRADING mode.\n\n'
                'This means:\n'
                '• Real money will be at risk\n'
                '• All trades will use your live account\n'
                '• Losses will be real financial losses\n\n'
                'Are you absolutely sure you want to continue?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.trading_mode = "live"
                self.mode_toggle.setText("LIVE MODE")
                self.mode_toggle.setProperty("mode", "live")
                self.log_message("⚠️ SWITCHED TO LIVE TRADING MODE - Real money at risk!")
            else:
                return
        else:
            self.trading_mode = "demo"
            self.mode_toggle.setText("DEMO MODE ")
            self.mode_toggle.setProperty("mode", "demo")
            self.log_message("✅ Switched to Demo mode - Safe trading environment")
        
        # Update button styling
        self.mode_toggle.style().unpolish(self.mode_toggle)
        self.mode_toggle.style().polish(self.mode_toggle)
        try:
            if qta is not None:
                icon_color = "#ffffff" if self.dark_theme else "#17191B"
                if self.trading_mode == "live":
                    icon = qta.icon("mdi.toggle-switch", color=icon_color)
                else:
                    icon = qta.icon("mdi.toggle-switch-off-outline", color=icon_color)
                self.mode_toggle.setIcon(icon)
        except Exception:
            pass
        
        # Save mode preference
        self.save_trading_mode_preference()

    def save_trading_mode_preference(self):
        """Save trading mode preference to config"""
        try:
            with open("config/settings.json", 'r') as f:
                config = json.load(f)
            
            config.setdefault('trading', {})['mode'] = self.trading_mode
            
            with open("config/settings.json", 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.log_message(f"Failed to save trading mode preference: {str(e)}")

    def load_trading_mode_preference(self):
        """Load trading mode preference from config"""
        try:
            with open("config/settings.json", 'r') as f:
                config = json.load(f)
                self.trading_mode = config.get('trading', {}).get('mode', 'demo')
        except:
            self.trading_mode = "demo"  # Default to demo mode

    def init_ui(self):
        """Initialize the user interface"""
        main_layout = QVBoxLayout()
        #text = "QuantDrift - Trade Smarter Not Harder"
        #color = QColor("green")
        
        # Header with logo and status
        header_layout = self.create_header()
        main_layout.addLayout(header_layout)
        
        # License section (shown only when needed)
        self.license_container = self.create_license_section()
        main_layout.addWidget(self.license_container)
        
        # Main content with tabs
        self.tab_widget = QTabWidget()    
        
        # Trading tab
        self.trading_tab = self.create_trading_tab()
        self.tab_widget.addTab(self.trading_tab, "Trading")
        
        # Analytics tab
        self.analytics_tab = self.create_analytics_tab()
        self.tab_widget.addTab(self.analytics_tab, "Analytics")
        
        # Positions tab
        self.positions_tab = self.create_positions_tab()
        self.tab_widget.addTab(self.positions_tab, "Positions")
        
        # Logs tab
        self.logs_tab = self.create_logs_tab()
        self.tab_widget.addTab(self.logs_tab, "Logs")
        
        main_layout.addWidget(self.tab_widget)
        
        self.setLayout(main_layout)

    def create_header(self):
        """Create header with logo and status"""
        layout = QHBoxLayout()
        
        # Logo
        self.logo_label = QLabel()
        try:
            self.logo_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.logo_label.setScaledContents(True)  # Let QLabel scale image
            self.logo_label.setFixedHeight(300)
            self.logo_label.setFixedWidth(1700)
            #pixmap = QPixmap("logo/levelup1.png")
            #pixmap = QPixmap("logo/quantDrift.jpg")
            #pixmap = QPixmap("logo/bwquantDrift.png")
            #self.logo_label.setPixmap(pixmap)
            #pixmap = pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            self.logo_label.setAlignment(Qt.AlignCenter)
        except:
            self.logo_label.setText("LevelUP")
            self.logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #0078d4;")

        
        self.logo_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.logo_label, alignment=Qt.AlignTop)
        
        # Spacer
        layout.addStretch()
        
        # Right-side status panel (modern stacked column)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(6)
        
        # Welcome label at the very top
        self.welcome_label = QLabel("Welcome User!")
        self.welcome_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self.welcome_label)
        
        # Clock at top of column (modern)
        clock_row = QHBoxLayout()
        icon_color = "#ffffff" if self.dark_theme else "#17191B"
        self.time_icon = QLabel()
        try:
            if qta is not None:
                self.time_icon.setPixmap(qta.icon("mdi.clock-time-four-outline", color=icon_color).pixmap(QSize(18, 18)))
        except Exception:
            pass
        clock_row.addWidget(self.time_icon)
        
        self.time_label = QLabel(datetime.now().strftime("%I:%M:%S %p"))
        self.time_label.setAlignment(Qt.AlignLeft)
        self.time_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        clock_row.addWidget(self.time_label)
        clock_row.addStretch()
        status_layout.addLayout(clock_row)

        # Date just below time
        self.date_label = QLabel(datetime.now().strftime("%a, %b %d, %Y"))
        self.date_label.setStyleSheet("font-size: 11px; opacity: 0.85;")
        status_layout.addWidget(self.date_label)
        
        # Connection status below clock
        self.connection_label = QLabel("● DISCONNECTED")
        self.connection_label.setObjectName("status_disconnected")
        status_layout.addWidget(self.connection_label)
        
        # Buttons below status in same column
        buttons_col = QHBoxLayout()
        
        # Demo/Live Mode Toggle with modern icon
        self.mode_toggle = QPushButton("DEMO MODE ")
        self.mode_toggle.setObjectName("mode_toggle")
        self.mode_toggle.clicked.connect(self.toggle_trading_mode)
        self.mode_toggle.setProperty("mode", "demo")
        try:
            play_icon = qta.icon("mdi.toggle-switch-off-outline", color=icon_color)
            self.mode_toggle.setIcon(play_icon)
            self.mode_toggle.setIconSize(QSize(18, 18))
        except Exception:
            pass
        self.mode_toggle.setCursor(Qt.PointingHandCursor)
        buttons_col.addWidget(self.mode_toggle)
        
        # Theme toggle button with modern icon
        self.theme_button = QPushButton("Dark Theme" if self.dark_theme else "Light Theme")
        self.theme_button.setObjectName("theme_button")
        self.theme_button.clicked.connect(self.toggle_theme)
        buttons_col.addWidget(self.theme_button)
        
        # Apply theme-specific icon styling
        self._apply_theme_button_icon()
        self.theme_button.setCursor(Qt.PointingHandCursor)
        
        status_layout.addLayout(buttons_col)
        
        layout.addLayout(status_layout)
        layout.setAlignment(status_layout, Qt.AlignTop)
        
        return layout

    def create_license_section(self):
        """Create license validation section"""
        container = QGroupBox("License Validation")
        layout = QVBoxLayout()
        
        self.license_input = QLineEdit()
        self.license_input.setPlaceholderText("Enter your license key...")
        
        self.login_button = QPushButton("Validate License")
        self.login_button.clicked.connect(self.validate_license)
        
        layout.addWidget(QLabel("License Key:"))
        layout.addWidget(self.license_input)
        layout.addWidget(self.login_button)
        
        container.setLayout(layout)
        return container
        
    def create_trading_tab(self):
        """Create main trading interface"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # middle panel - Controls
        middel_panel = QVBoxLayout()
        
        # Risk Management
        trade_group = QGroupBox("Trade Parameters")
        trade_layout = QGridLayout()
        
        trade_layout.addWidget(QLabel("Trade Expiry\n(Stock):"), 0, 0)
        self.trade_expiry = QComboBox()
        self.trade_expiry.setEditable(True)
        self.trade_expiry.addItems(["Current", "Next"])
        self.trade_expiry.setCurrentText("Current")
        trade_layout.addWidget(self.trade_expiry, 0, 1)
        
        trade_layout.addWidget(QLabel("Trade Expiry\n(ETF/Index):"), 1, 0)
        self.index_trade_expiry = QComboBox()
        self.index_trade_expiry.setEditable(True)
        self.index_trade_expiry.addItems(["0 DTE", "1 DTE"])
        self.index_trade_expiry.setCurrentText("0 DTE")
        trade_layout.addWidget(self.index_trade_expiry, 1, 1)
        
        trade_layout.addWidget(QLabel("Max Contract \nAmount ($):"), 2, 0)
        self.max_contract_amount = QDoubleSpinBox()
        self.max_contract_amount.setRange(1, 10000)
        self.max_contract_amount.setValue(350)
        trade_layout.addWidget(self.max_contract_amount, 2, 1)
        
        trade_layout.addWidget(QLabel("Gap Between Same\nRight Trades (S):"), 3, 0)
        self.gap_between_trades = QDoubleSpinBox()
        self.gap_between_trades.setRange(1, 3600)
        self.gap_between_trades.setValue(300)
        trade_layout.addWidget(self.gap_between_trades, 3, 1)
        
        trade_layout.addWidget(QLabel("Call DELTA:"), 4, 0)
        self.call_delta = QDoubleSpinBox()
        self.call_delta.setRange(0.1, 1.0)
        self.call_delta.setValue(0.35)
        #self.risk_input.setSuffix("%")
        trade_layout.addWidget(self.call_delta, 4, 1)
        
        trade_layout.addWidget(QLabel("Put DELTA:"), 5, 0)
        self.put_delta = QDoubleSpinBox()
        self.put_delta.setRange(0.1, 1.0)
        self.put_delta.setValue(0.35)
        trade_layout.addWidget(self.put_delta, 5, 1)
        
        trade_layout.addWidget(QLabel("Start Time:"), 6, 0)
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("hh:mm AP")
        self.start_time.setTime(QTime(9, 35))
        trade_layout.addWidget(self.start_time, 6, 1)
        
        trade_layout.addWidget(QLabel("End Time:"), 7, 0)
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("hh:mm AP")
        self.end_time.setTime(QTime(15, 45))
        trade_layout.addWidget(self.end_time, 7, 1)
        
        trade_layout.addWidget(QLabel("Candle Time\nFrame:"), 8, 0)
        self.candle_time = QComboBox()
        self.candle_time.addItems(["1 min", "3 mins", "5 mins", "15 mins", "30 mins", "1 hour", "2 hours", "4 hours"])
        self.candle_time.setCurrentText("5 mins")
        trade_layout.addWidget(self.candle_time, 8, 1)
        
        trade_group.setLayout(trade_layout)
        middel_panel.addWidget(trade_group)
        
        middel_panel.addStretch()
        layout.addLayout(middel_panel, 1)
        
        # middle panel 2 - Controls
        middel_panel_2 = QVBoxLayout()
        
        stock_group = QGroupBox("Stock Parameters")
        stock_layout = QGridLayout()
        
        stock_layout.addWidget(QLabel("Stock List:"), 1, 0)
        self.stock_list = QTextEdit()
        self.stock_list.setPlaceholderText("Enter stocks, e.g., AAPL:NASDAQ, MSFT:NASDAQ, TSLA:NASDAQ")
        self.stock_list.setText("AAPL:NASDAQ,\nMSFT:NASDAQ,\nTSLA:NASDAQ,\nAMZN:NASDAQ,\nGOOGL:NASDAQ")
        self.stock_list.setLineWrapMode(QTextEdit.NoWrap)   # avoid breaking stock codes
        self.stock_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        stock_layout.addWidget(self.stock_list, 1, 1)
        
        stock_group.setLayout(stock_layout)
        middel_panel_2.addWidget(stock_group)
        
        tws_group = QGroupBox("TWS Config")
        tws_layout = QGridLayout()
        
        tws_layout.addWidget(QLabel("TWS IP:"), 1, 0)
        self.tws_ip = QLineEdit()
        self.tws_ip.setPlaceholderText("TWS IP")
        self.tws_ip.setText("127.0.0.1")
        tws_layout.addWidget(self.tws_ip, 1, 1)
        
        tws_layout.addWidget(QLabel("TWS PORT:"), 2, 0)
        self.tws_port = QLineEdit()
        self.tws_port.setPlaceholderText("TWS PORT")
        self.tws_port.setText("7497")
        tws_layout.addWidget(self.tws_port, 2, 1)
        
        tws_layout.addWidget(QLabel("TWS CLIENT ID:"), 3, 0)
        self.tws_clientid = QLineEdit()
        self.tws_clientid.setPlaceholderText("TWS CLIENT ID")
        self.tws_clientid.setText("25")
        tws_layout.addWidget(self.tws_clientid, 3, 1)
        
        tws_group.setLayout(tws_layout)
        middel_panel_2.addWidget(tws_group)
        
        middel_panel_2.addStretch()
        layout.addLayout(middel_panel_2, 2)
        
        # Left panel - Controls
        left_panel = QVBoxLayout()
        
        # Risk Management
        risk_group = QGroupBox("Risk Management")
        risk_layout = QGridLayout()
        
        risk_layout.addWidget(QLabel("Daily Profit Target ($):"), 0, 0)
        self.profit_input = QDoubleSpinBox()
        self.profit_input.setRange(1, 10000)
        self.profit_input.setValue(500)
        risk_layout.addWidget(self.profit_input, 0, 1)
        
        risk_layout.addWidget(QLabel("Daily Loss Limit ($):"), 1, 0)
        self.loss_input = QDoubleSpinBox()
        self.loss_input.setRange(-10000, -1)
        self.loss_input.setValue(-300)
        risk_layout.addWidget(self.loss_input, 1, 1)
        
        risk_layout.addWidget(QLabel("Risk per Trade (%):"), 2, 0)
        self.risk_input = QDoubleSpinBox()
        self.risk_input.setRange(0.1, 10.0)
        self.risk_input.setValue(2.0)
        self.risk_input.setSuffix("%")
        risk_layout.addWidget(self.risk_input, 2, 1)
        
        risk_group.setLayout(risk_layout)
        left_panel.addWidget(risk_group)
        
        # Trading Controls
        controls_group = QGroupBox("Trading Controls")
        controls_layout = QVBoxLayout()
        
        self.start_button = QPushButton("🚀 Start Trading")
        self.start_button.setObjectName("start_button")
        self.start_button.clicked.connect(self.start_trading)
        self.start_button.setEnabled(True)  # Initially disabled
        self.start_button.setToolTip("Validate license to enable trading controls")
        
        self.stop_button = QPushButton("⏹ Stop Trading")
        self.stop_button.setObjectName("stop_button")
        self.stop_button.clicked.connect(self.stop_trading)
        self.stop_button.setEnabled(True)  # Initially disabled
        self.stop_button.setToolTip("Validate license to enable trading controls")
        
        self.emergency_button = QPushButton("🚨 EMERGENCY STOP")
        self.emergency_button.setObjectName("emergency_button")
        self.emergency_button.clicked.connect(self.emergency_stop)
        self.emergency_button.setEnabled(True)  # Initially disabled
        self.emergency_button.setToolTip("Validate license to enable trading controls")
        
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.emergency_button)
        
        controls_group.setLayout(controls_layout)
        left_panel.addWidget(controls_group)
        
        # Statistics
        stats_group = QGroupBox("Real-time Statistics")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("Daily P&L: $0.00 | Trades: 0 | Win Rate: 0%")
        if self.dark_theme:
            self.stats_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #00ff00;")
        else:
            self.stats_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #28a745;")
        self.stats_label.setAlignment(Qt.AlignCenter)
        
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        left_panel.addWidget(stats_group)
        
        left_panel.addStretch()
        layout.addLayout(left_panel, 3)
        

        # Right panel - Activity log
        right_panel = QVBoxLayout()
        
        log_group = QGroupBox("Trading Activity")
        log_layout = QVBoxLayout()
        
        self.text_log = QTextEdit()
        self.text_log.setReadOnly(True)
        self.text_log.setFont(QFont("Consolas", 9))
        
        log_layout.addWidget(self.text_log)
        log_group.setLayout(log_layout)
        right_panel.addWidget(log_group)
        
        layout.addLayout(right_panel, 4)
        
        widget.setLayout(layout)
        return widget

    def update_charts(self):
        self.frame += 1

        # Set theme-appropriate colors
        if self.dark_theme:
            text_color = "#ffffff"
            grid_color = "#555555"
            zero_line_color = "#ffffff"
        else:
            text_color = "#17191B"
            grid_color = "#cccccc"
            zero_line_color = "#17191B"

        # Pie chart animation
        self.pie_ax.clear()
        sizes = [self.stats['win_rate'], 1 - self.stats['win_rate']]
        colors = ['green', 'red']
        explode = (0.05, 0)
        self.pie_ax.pie(sizes, colors=colors, startangle=90, explode=explode,
                        autopct=lambda p: f"{p:.1f}%" if p > 0 else "")
        self.pie_ax.set_title("Winning vs Losing Trades", color=text_color)

        # Bar chart animation
        self.bar_ax.clear()
        profits = self.stats['profits'][:self.frame % len(self.stats['profits'])]
        colors = ['green' if p >= 0 else 'red' for p in profits]
        self.bar_ax.bar(range(len(profits)), profits, color=colors)
        self.bar_ax.axhline(0, color=zero_line_color, linewidth=1)
        self.bar_ax.set_title("Trade P/L Distribution", color=text_color)
        
        # Set theme-appropriate styling for bar chart
        self.bar_ax.tick_params(colors=text_color)
        self.bar_ax.grid(True, color=grid_color, alpha=0.3)
        for spine in self.bar_ax.spines.values():
            spine.set_color(grid_color)

        self.pie_canvas.draw()
        self.bar_canvas.draw()

    def create_analytics_tab(self, stats={}):
        """Create analytics dashboard"""
        print(f"THEME {self.dark_theme}")
        self.stats = stats
        if self.stats == {}:
            self.stats = {
                "gross_pl": 20.0,
                "trades": 21,
                "contracts": 42,
                "avg_time": "6min 3sec",
                "longest_time": "19min 58sec",
                "win_rate": 0.619,  # 61.9%
                "profits": [120, -50, 200, -100, 425, -345, 90, -120, 60]}
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Performance metrics
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QGridLayout()
        
        self.total_trades_label = QLabel("0")
        self.win_rate_label = QLabel("0%")
        self.avg_win_label = QLabel("$0.00")
        self.avg_loss_label = QLabel("$0.00")
        self.net_pnl_label = QLabel("$0.00")
        
        # Stats panel
        stats_group = QGroupBox("ALL TRADES")
        stats_layout = QVBoxLayout()
        stats_layout.addWidget(QLabel(f"Gross P/L: ${self.stats['gross_pl']:.2f}"))
        stats_layout.addWidget(QLabel(f"# of Trades: {self.stats['trades']}"))
        stats_layout.addWidget(QLabel(f"# of Contracts: {self.stats['contracts']}"))
        stats_layout.addWidget(QLabel(f"Avg. Trade Time: {self.stats['avg_time']}"))
        stats_layout.addWidget(QLabel(f"Longest Trade Time: {self.stats['longest_time']}"))
        stats_layout.addWidget(QLabel(f"% Profitable Trades: {self.stats['win_rate']*100:.2f}%"))

        self.refresh_analytics_button = QPushButton("Refresh")
        #self.refresh_analytics_button.clicked.connect(self.refresh_anayltics)
        stats_layout.addWidget(self.refresh_analytics_button)
        stats_group.setLayout(stats_layout)

        # Pie Chart
        #piecharts_layout = QGridLayout()
        """color = '#17191B'
        if self.dark_theme:
            color = '#17191B'
        else:
            color = 'white'"""
        print(f"*************CHANGED COLOR {self.color}")
        self.pie_fig = Figure(figsize=(3, 3), facecolor=self.color)
        self.pie_canvas = FigureCanvas(self.pie_fig)
        #piecharts_layout.addWidget(FigureCanvas(self.pie_fig))
        self.pie_ax = self.pie_fig.add_subplot(111, facecolor=self.color)
        #stats_group.setLayout(self.pie_ax)

        # Bar Chart
        self.bar_fig = Figure(figsize=(3, 3), facecolor=self.color)
        self.bar_canvas = FigureCanvas(self.bar_fig)
        self.bar_ax = self.bar_fig.add_subplot(111, facecolor=self.color)
        
        metrics_layout.addWidget(QLabel("Total Trades:"), 0, 0)
        metrics_layout.addWidget(self.total_trades_label, 0, 1)
        metrics_layout.addWidget(QLabel("Win Rate:"), 0, 2)
        metrics_layout.addWidget(self.win_rate_label, 0, 3)
        
        metrics_layout.addWidget(QLabel("Average Win:"), 1, 0)
        metrics_layout.addWidget(self.avg_win_label, 1, 1)
        metrics_layout.addWidget(QLabel("Average Loss:"), 1, 2)
        metrics_layout.addWidget(self.avg_loss_label, 1, 3)
        
        metrics_layout.addWidget(QLabel("Net P&L:"), 2, 0)
        metrics_layout.addWidget(self.net_pnl_label, 2, 1)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Three-section layout: All Trades | Graph | Graph
        three_layout = QHBoxLayout()
        
        pie_group = QGroupBox("Performance")
        pie_group_layout = QVBoxLayout()
        pie_group_layout.addWidget(self.pie_canvas)
        pie_group.setLayout(pie_group_layout)
        
        bar_group = QGroupBox("Trade Chart")
        bar_group_layout = QVBoxLayout()
        bar_group_layout.addWidget(self.bar_canvas)
        bar_group.setLayout(bar_group_layout)
        
        three_layout.addWidget(stats_group)
        three_layout.addWidget(pie_group)
        three_layout.addWidget(bar_group)
        
        layout.addLayout(three_layout)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        # Animate Charts
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_charts)
        self.frame = 0
        self.timer.start(100)
        
        # Apply current theme to charts
        self.update_chart_theme()

        return widget

    def create_positions_tab(self):
        """Create positions management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Positions table
        positions_group = QGroupBox("Active Positions")
        positions_layout = QVBoxLayout()
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(8)
        self.positions_table.setHorizontalHeaderLabels([
            "Trade ID", "Side", "Entry Price", "Current P&L", 
            "Stop Loss", "Take Profit", "Entry Time", "Actions"
        ])
        
        positions_layout.addWidget(self.positions_table)
        
        # Position controls
        controls_layout = QHBoxLayout()
        
        self.close_all_button = QPushButton("Close All Positions")
        self.close_all_button.clicked.connect(self.close_all_positions)
        self.refresh_positions_button = QPushButton("Refresh")
        self.refresh_positions_button.clicked.connect(self.refresh_positions)
        
        controls_layout.addWidget(self.close_all_button)
        controls_layout.addWidget(self.refresh_positions_button)
        controls_layout.addStretch()
        
        positions_layout.addLayout(controls_layout)
        positions_group.setLayout(positions_layout)
        layout.addWidget(positions_group)
        
        widget.setLayout(layout)
        return widget

    def create_logs_tab(self):
        """Create logs viewing tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Log filters
        filter_group = QGroupBox("Log Filters")
        filter_layout = QHBoxLayout()
        
        self.log_type_combo = QLineEdit("All")
        self.log_type_combo.setPlaceholderText("Log type (All, Trading, Errors, System)")
        
        self.refresh_logs_button = QPushButton("Refresh Logs")
        self.refresh_logs_button.clicked.connect(self.refresh_logs)
        
        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.log_type_combo)
        filter_layout.addWidget(self.refresh_logs_button)
        filter_layout.addStretch()
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # Logs display
        logs_group = QGroupBox("System Logs")
        logs_layout = QVBoxLayout()
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setFont(QFont("Consolas", 8))
        
        logs_layout.addWidget(self.logs_text)
        logs_group.setLayout(logs_layout)
        layout.addWidget(logs_group)
        
        widget.setLayout(layout)
        return widget

    def set_controls_enabled(self, enabled):
        """Enhanced control state management - only enable if license validated"""
        # Additional safety check - only enable if license was validated this session
        if enabled and not self.license_validated_this_session:
            enabled = True
            
        self.start_button.setEnabled(enabled)
        self.stop_button.setEnabled(enabled)
        self.emergency_button.setEnabled(enabled)
        self.text_log.setEnabled(True)  # Always keep log enabled for status messages
        
        # Update connection status
        if enabled:
            self.connection_label.setText("● CONNECTED")
            self.connection_label.setObjectName("status_connected")
            self.connection_status = True
        else:
            self.connection_label.setText("● DISCONNECTED")
            self.connection_label.setObjectName("status_disconnected")
            self.connection_status = False
        
        # Refresh style
        self.connection_label.style().unpolish(self.connection_label)
        self.connection_label.style().polish(self.connection_label)

    def show_license_status(self):
        """Show license status but don't auto-enable controls"""
        self.license_container.show()  # Always show license validation initially
        
        if os.path.exists(LICENSE_STATE):
            try:
                with open(LICENSE_STATE) as f:
                    state = json.load(f)
                    expiry = datetime.strptime(state['valid_until'], "%Y-%m-%d")
                    days_left = (expiry - datetime.today()).days
                    if days_left >= 0:
                        self.text_log.append(f"💡 License file found (valid for {days_left} days). Please validate to enable trading.")
                    else:
                        self.text_log.append("⚠️ Stored license has expired. Please enter a valid license key.")
            except Exception as e:
                self.text_log.append("⚠️ Error reading license state. Please validate your license.")
        else:
            self.text_log.append("🔑 Please enter your license key to enable trading controls.")

    def validate_license_old(self):
        """Validate license key and enable trading controls"""
        key = self.license_input.text().strip()
        
        if not key:
            QMessageBox.warning(self, "Invalid Input", "Please enter a license key.")
            return
            
        valid, message = validate_license(key)
        
        if valid:
            # Save license to config/license.txt
            with open("config/license.txt", "w") as f:
                f.write(key)
            self.license_validated_this_session = True
            self.set_controls_enabled(True)
            self.license_container.hide()
            self.start_button.setToolTip("Start automated trading")
            self.stop_button.setToolTip("Stop trading and manage positions")
            self.emergency_button.setToolTip("Emergency stop - immediately close all positions")
            self.license_input.clear()
            self.text_log.append(f"✅ License validated successfully!")
            self.text_log.append(message)
            self.text_log.append("🚀 Trading controls are now enabled.")
        else:
            QMessageBox.warning(self, "Invalid License", message or "The entered license key is invalid. Please check and try again.")
            self.license_input.clear()
            self.text_log.append("❌ License validation failed.")

    def auto_validate_if_stored(self):
        if os.path.exists(LICENSE_FILE):
            with open(LICENSE_FILE) as fil_lic:
                state = json.load(fil_lic)
                license_key_stored = expiry = state['key']
                license_key_generated = generate_fixed_license_key(IP_Validate, email_validate, key_to_validate, days_to_validate, starting_date)
                if license_key_stored == license_key_generated:
                    expiry_days_end = get_expiry_date(starting_date, days_to_validate)
                    expiry_date_obj = datetime.datetime.strptime(expiry_days_end, "%Y-%m-%d")
                    days_left = (expiry_date_obj - datetime.datetime.today()).days
                    if days_left >= 0:
                        self.set_controls_enabled(True)
                        self.license_container.hide()
                        self.text_log.append(f" *** License valid. Days left: {days_left} ***\n\n")
                    else:
                        self.text_log.append("\nLicense expired. Please revalidate.\nContact Support Team \nEmail: quantdrift@gmail.com\nWhatsApp: +91-9461651867")
                else:
                    self.text_log.append("\nIf License File is not Present or Key Mismatched.\nPlease Contact Support Team \nEmail: quantdrift@gmail.com\nWhatsApp: +91-9461651867")
        else:
            self.license_container.show()
        
    def validate_license(self):
        input_key = self.license_input.text().strip()
        license_key = generate_fixed_license_key(IP_Validate, email_validate, key_to_validate, days_to_validate, starting_date)
        try:
            if input_key.__str__() == license_key.__str__():
                with open(LICENSE_FILE, 'w') as lic_file_wr:
                    json.dump({"key": license_key}, lic_file_wr)
                self.text_log.append(f"License validated. Expires on {get_expiry_date(starting_date, days_to_validate)}")
                self.set_controls_enabled(True)
                self.license_container.hide()
            else:
                raise Exception
        except Exception as err:
            print(f"{err}")
            QMessageBox.warning(self, "Invalid", "License key is invalid.\nContact Support Team \nEmail: quantdrift@gmail.com\nWhatsApp: +91-9461651867")
            
    def get_ui_config(self):
        self.dailyprofit = self.profit_input.value()
        self.dailyloss = self.loss_input.value()
        self.riskpertrade = self.risk_input.value()
        
        self.twsip = self.tws_ip.text()
        self.twsport = self.tws_port.text()
        self.twsclientid = self.tws_clientid.text()
        
        self.tradeexpiry = self.trade_expiry.currentText()
        self.indextradeexpiry = self.index_trade_expiry.currentText()
        self.maxcontractamount = self.max_contract_amount.value()
        self.gapbetweentrades = self.gap_between_trades.value()
        self.calldelta = self.call_delta.value()
        self.putdelta = self.put_delta.value()
        #self.starttime = self.start_time.time().toString("HH:mm")
        #self.endtime = self.end_time.time().toString("HH:mm")
        self.starttime = self.start_time.time()
        self.endtime = self.end_time.time()
        self.candletime = self.candle_time.currentText()
        self.stocklist = self.stock_list.toPlainText()
        
        # Update Config.Json File.
        with open("config.json", "r") as config_file:
            self.data = json.loads(config_file.read())
            
        print(f"Start time {self.starttime} and End time {self.end_time}")
        
        self.data["expiryToTrade"] = self.tradeexpiry
        self.data["SPY_QQQ_EXPIRY"] = self.indextradeexpiry
        self.data["USE_DIFF_EXPIRY_INDEX"] = "yes"
        self.data["IP"] = self.twsip
        self.data["PORT"] = int(self.twsport)
        self.data["CLIENTID"] = int(self.twsclientid)
        self.data["marketStartTime"] = "19:00:00"
        self.data["scriptStartTime"] = self.starttime
        self.data["scriptEndTime"] = self.endtime
        self.data["loss_amount_day"] = int(self.dailyloss)
        self.data["ORDER_TRANSMIT"] = True
        self.data["USE_TIMER_IN_ORDER"] = "YES"
        self.data["ORDER_EXPIRY_TIMER"] = int(15)
        self.data["CALL_DELTA_CHECK"] = float(self.calldelta)
        self.data["PUT_DELTA_CHECK"] = float(self.putdelta)
        self.data["VOLUME_CHECK"] = int(5)
        self.data["ATR_CHECK"] = float(0.047)
        self.data["ACTIVE_VOLUME"] = int(25)
        self.data["MAX_CONTRACT_AMOUNT"] = int(self.maxcontractamount)
        self.data["profit_amount_day"] = int(self.dailyprofit)
        self.data["fetchValue"] = "2 D"
        self.data["candleTime"] = self.candletime
        self.data["distance_between_trade"] = int(self.gapbetweentrades)
        
        #with open("config.json", "w") as config_file:
        #    json.dump(self.data, config_file, indent=2)

    def start_trading(self):
        """Enhanced start trading with better validation"""
        print("Enhanced start trading with better validation")
        self.get_ui_config()
        """try:
            # Double-check license validation
            if not self.license_validated_this_session:
                QMessageBox.warning(self, "License Required", 
                                  "Please validate your license key before starting trading.")
                self.license_container.show()
                return
            
            # Validate inputs
            #profit = self.profit_input.value()
            #loss = self.loss_input.value()
            self.get_ui_config()
            
            if self.dailyprofit <= 0 or self.dailyloss >= 0:
                QMessageBox.warning(self, "Invalid Input", "Please check profit/loss values")
                return
            
            # Sync all UI state to config and save before trading
            #self.sync_ui_to_config()
            
            # Log config for verification
            self.log_message(f"Config used for trading: {json.dumps(self.config, indent=2)}")
            
            # Check if trading thread already exists
            if self.trading_thread and self.trading_thread.isRunning():
                reply = QMessageBox.question(
                    self, 'Trading Active',
                    'Trading is already active. Do you want to restart?',
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    self.stop_trading()
                else:
                    return
            
            # Create and start trading thread, pass config
            self.trading_thread = TradingThread(self.dailyprofit, self.dailyloss, self.trading_mode)
            # Optionally, you can pass config to TradingThread if needed
            if hasattr(self.trading_thread, 'trader'):
                self.trading_thread.trader.config = self.config
            self.trading_thread.log_signal.connect(self.log_message)
            self.trading_thread.stats_signal.connect(self.update_stats)
            self.trading_thread.error_signal.connect(self.handle_error)
            self.trading_thread.price_signal.connect(self.update_price_display)
            
            # Check for existing positions
            if hasattr(self.trading_thread, 'trader'):
                existing_positions = self.trading_thread.trader.get_active_positions()
                if existing_positions:
                    reply = QMessageBox.question(
                        self, 'Existing Positions',
                        f'Found {len(existing_positions)} existing positions. Continue monitoring them?',
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.No:
                        return
            
            self.trading_thread.start()
            self.log_message("🚀 Trading system started successfully")
            self.log_message(f"📊 Daily targets: Profit ${profit:.2f}, Loss ${loss:.2f}")
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.emergency_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start trading: {str(e)}")
            self.log_message(f"❌ Error starting trading: {str(e)}")"""

        BOT.start_trading(self.data)
        self.log_message("Trading Started")

    def stop_trading(self):
        """Enhanced stop trading with position handling"""
        BOT.stop_trading()
        self.log_message("Trading Stopped")
        if not self.trading_thread:
            self.log_message("⚠️ No active trading session to stop\n")
            return
        
        try:
            # Check for active positions
            if hasattr(self.trading_thread, 'trader'):
                active_positions = self.trading_thread.trader.get_active_positions()
                
                if active_positions:
                    reply = QMessageBox.question(
                        self, 'Active Positions',
                        f'There are {len(active_positions)} active positions.\n\n'
                        'Choose action:\n'
                        '• Yes: Stop new trades, keep monitoring positions\n'
                        '• No: Close all positions and stop\n'
                        '• Cancel: Continue trading',
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Cancel:
                        return
                    elif reply == QMessageBox.No:
                        # Close all positions
                        self.trading_thread.trader.close_all_positions("Stop trading - close all")
                        self.log_message("🔄 Closing all positions...")
            
            # Stop the trading thread
            self.trading_thread.stop()
            self.trading_thread.quit()
            self.trading_thread.wait(5000)  # Wait up to 5 seconds
            
            if self.trading_thread.isRunning():
                self.log_message("⚠️ Force terminating trading thread...")
                self.trading_thread.terminate()
            
            self.log_message("⏹ Trading stopped successfully")
            
            # Update UI state - respect license validation
            if self.license_validated_this_session:
                self.start_button.setEnabled(True)
            else:
                self.start_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.emergency_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error stopping trading: {str(e)}")
            self.log_message(f"❌ Error stopping trading: {str(e)}")

    def emergency_stop(self):
        """Emergency stop - immediate halt of all trading"""
        reply = QMessageBox.critical(
            self, 'EMERGENCY STOP',
            '🚨 EMERGENCY STOP will immediately:\n\n'
            '• Close ALL active positions\n'
            '• Stop all trading activities\n'
            '• Disconnect from broker\n\n'
            'This action cannot be undone. Continue?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self.trading_thread and hasattr(self.trading_thread, 'trader'):
                    self.trading_thread.emergency_stop()
                    self.log_message("🚨 EMERGENCY STOP ACTIVATED - All positions closed")
                
                # Force UI reset - respect license validation
                if self.license_validated_this_session:
                    self.start_button.setEnabled(True)
                else:
                    self.start_button.setEnabled(False)
                self.stop_button.setEnabled(False)
                self.emergency_button.setEnabled(False)
                
            except Exception as e:
                self.log_message(f"❌ Error during emergency stop: {str(e)}")

    def handle_error(self, error_message):
        """Handle errors from trading thread"""
        self.log_message(f"❌ ERROR: {error_message}")
        QMessageBox.critical(self, "Trading Error", error_message)

    def log_message(self, msg):
        """Enhanced logging with timestamps and formatting"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {msg}"
        self.text_log.append(formatted_msg)
        
        # Auto-scroll to bottom
        cursor = self.text_log.textCursor()
        cursor.movePosition(cursor.End)
        self.text_log.setTextCursor(cursor)

    def update_stats(self, stats):
        """Enhanced statistics display"""
        pnl = stats.get('pnl', 0)
        total = stats.get('total', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        win_rate = stats.get('win_rate', 0)
        avg_win = stats.get('avg_win', 0)
        avg_loss = stats.get('avg_loss', 0)
        active_positions = stats.get('active_positions', 0)
        
        # Color based on theme and PnL
        if self.dark_theme:
            pnl_color = "#00ff00" if pnl >= 0 else "#ff0000"
            net_color = "color: #00ff00;" if pnl >= 0 else "color: #ff0000;"
        else:
            pnl_color = "#28a745" if pnl >= 0 else "#dc3545"
            net_color = "color: #28a745;" if pnl >= 0 else "color: #dc3545;"
        
        # Main stats display
        self.stats_label.setText(
            f"Daily P&L: <span style='color: {pnl_color}; font-weight: bold;'>${pnl:.2f}</span> | "
            f"Trades: {total} | Win Rate: {win_rate:.1f}% | Active: {active_positions}"
        )
        
        # Update analytics tab
        self.total_trades_label.setText(str(total))
        self.win_rate_label.setText(f"{win_rate:.1f}%")
        self.avg_win_label.setText(f"${avg_win:.2f}")
        self.avg_loss_label.setText(f"${avg_loss:.2f}")
        
        self.net_pnl_label.setText(f"<span style='{net_color} font-weight: bold;'>${pnl:.2f}</span>")

    def setup_timers(self):
        """Setup update timers"""
        # Time update timer
        self.time_timer = QTimer()
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # Update every second
        
        # Position refresh timer
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.refresh_positions)
        self.position_timer.start(5000)  # Update every 5 seconds

    def update_time(self):
        """Update time display"""
        # Modern clock format
        try:
            self.time_label.setText(datetime.now().strftime("%I:%M:%S %p"))
            if hasattr(self, 'date_label'):
                self.date_label.setText(datetime.now().strftime("%a, %b %d, %Y"))
        except Exception:
            self.time_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def refresh_positions(self):
        """Refresh positions table"""
        if self.trading_thread and hasattr(self.trading_thread, 'trader'):
            try:
                positions = self.trading_thread.trader.get_active_positions()
                self.positions_table.setRowCount(len(positions))
                
                for row, pos in enumerate(positions):
                    self.positions_table.setItem(row, 0, QTableWidgetItem(pos.get('trade_id', '')[:8]))
                    self.positions_table.setItem(row, 1, QTableWidgetItem(pos.get('side', '')))
                    self.positions_table.setItem(row, 2, QTableWidgetItem(f"${pos.get('entry_price', 0):.2f}"))
                    self.positions_table.setItem(row, 3, QTableWidgetItem(f"${pos.get('pnl', 0):.2f}"))
                    self.positions_table.setItem(row, 4, QTableWidgetItem(f"${pos.get('stop_loss', 0):.2f}"))
                    self.positions_table.setItem(row, 5, QTableWidgetItem(f"${pos.get('take_profit', 0):.2f}"))
                    
                    entry_time = pos.get('entry_time', '')
                    if isinstance(entry_time, datetime):
                        entry_time = entry_time.strftime("%H:%M:%S")
                    self.positions_table.setItem(row, 6, QTableWidgetItem(str(entry_time)))
                    
                    # Add close button
                    close_button = QPushButton("Close")
                    close_button.clicked.connect(lambda checked, tid=pos.get('trade_id'): self.close_position(tid))
                    self.positions_table.setCellWidget(row, 7, close_button)
                    
            except Exception as e:
                self.log_message(f"Error refreshing positions: {str(e)}")

    def close_position(self, trade_id):
        """Close a specific position"""
        if self.trading_thread and hasattr(self.trading_thread, 'trader'):
            try:
                # This would require implementing a close_specific_position method in trader
                self.log_message(f"Closing position {trade_id}")
                # self.trading_thread.trader.close_position(trade_id)
            except Exception as e:
                self.log_message(f"Error closing position: {str(e)}")

    def close_all_positions(self):
        """Close all active positions"""
        if self.trading_thread and hasattr(self.trading_thread, 'trader'):
            reply = QMessageBox.question(
                self, 'Confirm Close All',
                'Are you sure you want to close all active positions?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    closed = self.trading_thread.trader.close_all_positions("Manual close all")
                    self.log_message(f"Closed {len(closed)} positions")
                except Exception as e:
                    self.log_message(f"Error closing all positions: {str(e)}")

    def refresh_logs(self):
        """Refresh log display"""
        try:
            from utils.logger import trading_logger
            log_type = self.log_type_combo.text().lower()
            if log_type == "all" or log_type == "":
                log_type = "trading"
            
            recent_logs = trading_logger.get_recent_logs(log_type, 200)
            self.logs_text.clear()
            self.logs_text.append("".join(recent_logs))
            
            # Scroll to bottom
            cursor = self.logs_text.textCursor()
            cursor.movePosition(cursor.End)
            self.logs_text.setTextCursor(cursor)
            
        except Exception as e:
            self.logs_text.append(f"Error loading logs: {str(e)}")

    def load_theme_preference(self):
        """Load theme preference from config"""
        try:
            with open("config/settings.json", 'r') as f:
                config = json.load(f)
                theme = config.get('ui', {}).get('theme', 'dark')
                self.dark_theme = (theme == 'dark')
        except:
            self.dark_theme = True  # Default to dark theme

    def save_theme_preference(self):
        """Save theme preference to config"""
        try:
            with open("config/settings.json", 'r') as f:
                config = json.load(f)
            
            config.setdefault('ui', {})['theme'] = 'dark' if self.dark_theme else 'light'
            
            with open("config/settings.json", 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            self.log_message(f"Failed to save theme preference: {str(e)}")

    def update_price_display(self, symbol: str, price: float):
        """Update real-time price display"""
        try:
            # Update the main price display label if it exists
            if hasattr(self, 'price_label'):
                self.price_label.setText(f"{symbol}: ${price:.2f}")
            
            # Update any price displays in tables or other UI elements
            self.log_message(f"💰 {symbol}: ${price:.2f}")
            
        except Exception as e:
            self.log_message(f"Error updating price display: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont("Arial", 9))  # You can increase to 13 or 14 if needed
    window = MainApp()
    window.show()
    sys.exit(app.exec_())
