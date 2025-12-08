"""
Shared styles and theme definitions for the macOS-like UI.
"""

from PySide6.QtGui import QColor, QFont

class MacTheme:
    """macOS-inspired theme colors and fonts."""
    
    # Common Fonts
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_NORMAL = 13

    # Theme Colors
    class Colors:
        def __init__(self, is_dark: bool):
            if is_dark:
                self.BACKGROUND = "#1E1E1E"
                self.WINDOW_BG = "#2D2D2D"
                self.TEXT = "#FFFFFF"
                self.ACCENT = "#0A84FF"  # Lighter blue for dark mode
                self.ACCENT_HOVER = "#409CFF"
                self.SECONDARY_TEXT = "#A1A1A6"
                self.BORDER = "#424242"
                self.SIDEBAR_BG = "#262626"
                self.SIDEBAR_BORDER = "#333333"
                self.INPUT_BG = "#1E1E1E"
                self.HOVER_BG = "rgba(255, 255, 255, 0.1)"
            else:
                self.BACKGROUND = "#F5F5F7"
                self.WINDOW_BG = "#FFFFFF"
                self.TEXT = "#1D1D1F"
                self.ACCENT = "#007AFF"
                self.ACCENT_HOVER = "#0062CC"
                self.SECONDARY_TEXT = "#86868B"
                self.BORDER = "#D1D1D1"
                self.SIDEBAR_BG = "#F0F0F5"
                self.SIDEBAR_BORDER = "#E5E5E5"
                self.INPUT_BG = "#FFFFFF"
                self.HOVER_BG = "rgba(0, 0, 0, 0.05)"

    @staticmethod
    def get_stylesheet(dark_mode: bool = False) -> str:
        """Return the global stylesheet for the application."""
        c = MacTheme.Colors(dark_mode)
        
        return f"""
        QWidget {{
            font-family: '{MacTheme.FONT_FAMILY}';
            font-size: {MacTheme.FONT_SIZE_NORMAL}px;
            color: {c.TEXT};
            background-color: {c.BACKGROUND};
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {c.WINDOW_BG};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 5px 14px;
            min-height: 24px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c.HOVER_BG};
            border-color: {c.SECONDARY_TEXT};
        }}
        QPushButton:pressed {{
            background-color: {c.ACCENT};
            color: white;
            border-color: {c.ACCENT};
        }}
        QPushButton[class="primary"] {{
            background-color: {c.ACCENT};
            color: white;
            border: none;
            font-weight: 600;
        }}
        QPushButton[class="primary"]:hover {{
            background-color: {c.ACCENT_HOVER};
        }}
        
        /* Inputs & ComboBox */
        QLineEdit, QComboBox, QSpinBox {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 5px 10px;
            selection-background-color: {c.ACCENT};
            color: {c.TEXT};
            min-height: 22px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: 2px solid {c.ACCENT};
            padding: 4px 9px;
        }}
        
        /* ComboBox Dropdown */
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left-width: 0px;
            border-top-right-radius: 6px;
            border-bottom-right-radius: 6px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 2px solid {c.SECONDARY_TEXT};
            border-bottom: 2px solid {c.SECONDARY_TEXT};
            width: 6px;
            height: 6px;
            margin-right: 8px;
            margin-top: -2px;
            transform: rotate(-45deg);
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            background-color: {c.WINDOW_BG};
            selection-background-color: {c.ACCENT};
            selection-color: white;
            padding: 4px;
            outline: none;
            color: {c.TEXT};
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 10px;
            border-radius: 4px;
            min-height: 20px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {c.HOVER_BG};
            color: {c.TEXT};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {c.ACCENT};
            color: white;
        }}

        /* Menus */
        QMenu {{
            background-color: {c.WINDOW_BG};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 4px 20px;
            border-radius: 4px;
            color: {c.TEXT};
        }}
        QMenu::item:selected {{
            background-color: {c.ACCENT};
            color: white;
        }}

        /* CheckBox */
        QCheckBox {{
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            background: {c.INPUT_BG};
            border: 1px solid {c.BORDER};
            border-radius: 4px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {c.ACCENT};
            border-color: {c.ACCENT};
            image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIzIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiPjxwb2x5bGluZSBwb2ludHM9IjIwIDYgOSAxNyA0IDEyIi8+PC9zdmc+);
        }}
        
        /* QTextEdit */
        QTextEdit {{
            background-color: {c.INPUT_BG};
            color: {c.TEXT};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 8px;
            font-family: '{MacTheme.FONT_FAMILY}';
            font-size: {MacTheme.FONT_SIZE_NORMAL}px;
            selection-background-color: {c.ACCENT};
        }}
        QTextEdit:focus {{
            border: 2px solid {c.ACCENT};
            padding: 7px;
        }}

        /* QDoubleSpinBox */
        QDoubleSpinBox {{
            background-color: {c.INPUT_BG};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            padding: 5px 10px;
            selection-background-color: {c.ACCENT};
            color: {c.TEXT};
            min-height: 22px;
        }}
        QDoubleSpinBox:focus {{
            border: 2px solid {c.ACCENT};
            padding: 4px 9px;
        }}

        /* Placeholder Text */
        QLineEdit::placeholder, QTextEdit::placeholder {{
            color: {c.SECONDARY_TEXT};
            font-style: italic;
        }}

        /* GroupBox */
        QGroupBox {{
            background-color: {c.WINDOW_BG};
            border: 1px solid {c.BORDER};
            border-radius: 8px;
            margin-top: 16px;
            padding-top: 20px;
            padding-bottom: 16px;
            padding-left: 16px;
            padding-right: 16px;
            font-size: 14px;
            font-weight: 600;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 5px;
            color: {c.TEXT};
            font-weight: 600;
            left: 12px;
        }}
        
        /* Sidebar List */
        QListWidget {{
            background-color: {c.SIDEBAR_BG};
            border: none;
            border-right: 1px solid {c.SIDEBAR_BORDER};
            outline: none;
        }}
        QListWidget::item {{
            height: 38px;
            padding-left: 12px;
            color: {c.TEXT};
            border-radius: 6px;
            margin: 4px 12px;
            border: none;
        }}
        QListWidget::item:selected {{
            background-color: {c.HOVER_BG};
            color: {c.TEXT};
        }}
        QListWidget::item:selected:active {{
            background-color: {c.ACCENT};
            color: white;
        }}
        QListWidget::item:hover:!selected {{
            background-color: {c.HOVER_BG};
        }}
        
        /* Scrollbar */
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {c.SECONDARY_TEXT};
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        """
