"""
UI Animation utilities for smooth theme transitions and visual effects
"""

from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPalette, QColor


class ThemeTransitionManager(QObject):
    """Manages theme transitions with safe, reliable implementation"""
    
    transition_completed = pyqtSignal()
    
    def __init__(self, main_widget: QWidget, duration: int = 300):
        super().__init__()
        self.main_widget = main_widget
        self.duration = duration
        
        # Theme stylesheets storage
        self.dark_theme_stylesheet = ""
        self.light_theme_stylesheet = ""
        
    def set_theme_stylesheets(self, dark_stylesheet: str, light_stylesheet: str):
        """Set the dark and light theme stylesheets"""
        self.dark_theme_stylesheet = dark_stylesheet
        self.light_theme_stylesheet = light_stylesheet
    
    def transition_to_theme(self, is_dark_theme: bool):
        """Apply theme transition (immediate for stability)"""
        try:
            # Apply theme directly - this is the most stable approach
            if is_dark_theme:
                self.main_widget.setStyleSheet(self.dark_theme_stylesheet)
            else:
                self.main_widget.setStyleSheet(self.light_theme_stylesheet)
            
            # Use a timer to emit completion signal asynchronously
            QTimer.singleShot(50, self.transition_completed.emit)
            
        except Exception as e:
            # Ensure completion signal is always emitted
            QTimer.singleShot(50, self.transition_completed.emit)


class ButtonPressAnimation:
    """Provides press animation effects for buttons"""
    
    @staticmethod
    def animate_button_press(button: QWidget, duration: int = 150):
        """Animate button press with scale effect"""
        try:
            # Create scale animation
            animation = QPropertyAnimation(button, b"geometry")
            animation.setDuration(duration)
            
            original_geometry = button.geometry()
            pressed_geometry = original_geometry.adjusted(2, 2, -2, -2)
            
            animation.setStartValue(original_geometry)
            animation.setEndValue(pressed_geometry)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            
            # Return to original size
            def return_to_normal():
                try:
                    return_animation = QPropertyAnimation(button, b"geometry")
                    return_animation.setDuration(duration)
                    return_animation.setStartValue(pressed_geometry)
                    return_animation.setEndValue(original_geometry)
                    return_animation.setEasingCurve(QEasingCurve.InCubic)
                    return_animation.start()
                except:
                    pass
            
            animation.finished.connect(return_to_normal)
            animation.start()
        except:
            pass  # Ignore animation errors


class StatusIndicatorAnimation:
    """Provides status indicator effects without graphics effects"""
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self.timer = QTimer()
        self.is_animating = False
        self.opacity_state = 1.0
        self.fade_direction = -1  # -1 for fade out, 1 for fade in
        
    def start_pulse_animation(self, min_opacity: float = 0.3, max_opacity: float = 1.0, duration: int = 1000):
        """Start pulsing animation using stylesheet opacity"""
        if self.is_animating:
            return
            
        self.min_opacity = min_opacity
        self.max_opacity = max_opacity
        self.opacity_state = max_opacity
        self.fade_direction = -1
        
        # Use timer-based animation instead of graphics effects
        self.timer.timeout.connect(self._update_opacity)
        self.timer.start(50)  # Update every 50ms
        self.is_animating = True
    
    def stop_pulse_animation(self):
        """Stop pulsing animation"""
        if self.is_animating:
            self.timer.stop()
            self.timer.timeout.disconnect()
            self.is_animating = False
            # Reset to full opacity
            self.widget.setStyleSheet(f"QWidget {{ opacity: 1.0; }}")
    
    def _update_opacity(self):
        """Update opacity state"""
        try:
            step = 0.05
            self.opacity_state += step * self.fade_direction
            
            if self.opacity_state <= self.min_opacity:
                self.opacity_state = self.min_opacity
                self.fade_direction = 1
            elif self.opacity_state >= self.max_opacity:
                self.opacity_state = self.max_opacity
                self.fade_direction = -1
            
            # Apply opacity through stylesheet
            current_style = self.widget.styleSheet()
            # Remove existing opacity rule if present
            lines = current_style.split('\n')
            filtered_lines = [line for line in lines if 'opacity:' not in line]
            new_style = '\n'.join(filtered_lines)
            
            # Add new opacity
            if new_style.strip():
                new_style += f"\nQWidget {{ opacity: {self.opacity_state:.2f}; }}"
            else:
                new_style = f"QWidget {{ opacity: {self.opacity_state:.2f}; }}"
            
            self.widget.setStyleSheet(new_style)
        except:
            pass  # Ignore opacity update errors


class LoadingSpinner:
    """Creates a loading spinner animation"""
    
    def __init__(self, parent_widget: QWidget):
        self.parent = parent_widget
        self.timer = QTimer()
        self.angle = 0
        self.is_spinning = False
        
    def start_spinning(self):
        """Start the spinning animation"""
        if not self.is_spinning:
            self.timer.timeout.connect(self._rotate)
            self.timer.start(50)  # Update every 50ms
            self.is_spinning = True
    
    def stop_spinning(self):
        """Stop the spinning animation"""
        if self.is_spinning:
            self.timer.stop()
            self.timer.timeout.disconnect()
            self.is_spinning = False
            self.angle = 0
    
    def _rotate(self):
        """Rotate the spinner"""
        self.angle = (self.angle + 10) % 360
        self.parent.update()  # Trigger repaint


class SlideTransition:
    """Provides slide transition effects for widgets"""
    
    @staticmethod
    def slide_in_from_right(widget: QWidget, duration: int = 300):
        """Slide widget in from the right"""
        try:
            start_pos = widget.pos()
            start_pos.setX(widget.parent().width())
            end_pos = widget.pos()
            
            animation = QPropertyAnimation(widget, b"pos")
            animation.setDuration(duration)
            animation.setStartValue(start_pos)
            animation.setEndValue(end_pos)
            animation.setEasingCurve(QEasingCurve.OutCubic)
            animation.start()
            
            return animation
        except:
            return None
    
    @staticmethod
    def slide_out_to_left(widget: QWidget, duration: int = 300):
        """Slide widget out to the left"""
        try:
            start_pos = widget.pos()
            end_pos = widget.pos()
            end_pos.setX(-widget.width())
            
            animation = QPropertyAnimation(widget, b"pos")
            animation.setDuration(duration)
            animation.setStartValue(start_pos)
            animation.setEndValue(end_pos)
            animation.setEasingCurve(QEasingCurve.InCubic)
            animation.start()
            
            return animation
        except:
            return None


class ColorTransition:
    """Provides smooth color transitions for widgets"""
    
    def __init__(self, widget: QWidget, property_name: str = "color"):
        self.widget = widget
        self.property_name = property_name
        self.animation = None
    
    def transition_color(self, start_color: QColor, end_color: QColor, duration: int = 300):
        """Transition from one color to another"""
        try:
            self.animation = QPropertyAnimation(self.widget, self.property_name.encode())
            self.animation.setDuration(duration)
            self.animation.setStartValue(start_color)
            self.animation.setEndValue(end_color)
            self.animation.setEasingCurve(QEasingCurve.InOutCubic)
            self.animation.start()
            
            return self.animation
        except:
            return None


class SafeAnimationManager:
    """Manages animations safely with proper cleanup"""
    
    def __init__(self):
        self.active_animations = []
        
    def add_animation(self, animation: QPropertyAnimation):
        """Add animation to manager"""
        if animation:
            self.active_animations.append(animation)
            animation.finished.connect(lambda: self._remove_animation(animation))
    
    def _remove_animation(self, animation: QPropertyAnimation):
        """Remove animation from manager"""
        if animation in self.active_animations:
            self.active_animations.remove(animation)
    
    def stop_all_animations(self):
        """Stop all active animations"""
        for animation in self.active_animations[:]:
            try:
                animation.stop()
            except:
                pass
        self.active_animations.clear()
