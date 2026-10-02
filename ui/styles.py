"""
Modern dark-theme stylesheet and visual design tokens for LocalStudy (PySide6).
"""

DARK_THEME_QSS = """
/* Global Window & Theme */
QMainWindow, QDialog {
    background-color: #0F172A;
    color: #F8FAFC;
}

QWidget {
    color: #F8FAFC;
}

/* Sidebar Styling */
#SidebarFrame {
    background-color: #0B1120;
    border-right: 1px solid #1E293B;
}

#AppLogoTitle {
    font-size: 18px;
    font-weight: 700;
    color: #38BDF8;
    letter-spacing: 0.5px;
}

#AppLogoSubtitle {
    font-size: 11px;
    color: #64748B;
}

/* Navigation Buttons */
QPushButton.NavBtn {
    background-color: transparent;
    color: #94A3B8;
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
    border: none;
}

QPushButton.NavBtn:hover {
    background-color: #1E293B;
    color: #F1F5F9;
}

QPushButton.NavBtn:checked, QPushButton.NavBtn.active {
    background-color: #0369A1;
    color: #FFFFFF;
    font-weight: 600;
}

/* Content Container Cards */
QFrame.CardFrame {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 16px;
}

QFrame.CardFrame:hover {
    border-color: #475569;
}

/* Section Headers */
QLabel.SectionTitle {
    font-size: 17px;
    font-weight: 600;
    color: #F8FAFC;
}

QLabel.SectionSubtitle {
    font-size: 12px;
    color: #94A3B8;
}

/* Primary Action Buttons */
QPushButton.PrimaryBtn {
    background-color: #0284C7;
    color: #FFFFFF;
    font-weight: 600;
    padding: 9px 18px;
    border-radius: 6px;
    border: none;
}

QPushButton.PrimaryBtn:hover {
    background-color: #0369A1;
}

QPushButton.PrimaryBtn:pressed {
    background-color: #075985;
}

QPushButton.SecondaryBtn {
    background-color: #334155;
    color: #E2E8F0;
    font-weight: 500;
    padding: 9px 16px;
    border-radius: 6px;
    border: 1px solid #475569;
}

QPushButton.SecondaryBtn:hover {
    background-color: #475569;
    color: #FFFFFF;
}

QPushButton.DangerBtn {
    background-color: #DC2626;
    color: #FFFFFF;
    font-weight: 600;
    padding: 9px 16px;
    border-radius: 6px;
    border: none;
}

QPushButton.DangerBtn:hover {
    background-color: #B91C1C;
}

/* Text Inputs, ComboBoxes, and Spinners */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0F172A;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #0284C7;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #38BDF8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    selection-background-color: #0284C7;
}

/* Tables and Tree Views */
QTableWidget, QTreeWidget, QListWidget {
    background-color: #1E293B;
    alternate-background-color: #162032;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #334155;
    color: #F8FAFC;
    selection-background-color: #0369A1;
}

QHeaderView::section {
    background-color: #0F172A;
    color: #94A3B8;
    padding: 6px 10px;
    border: none;
    border-bottom: 1px solid #334155;
    font-weight: 600;
}

/* Progress Bars */
QProgressBar {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    color: #F8FAFC;
    font-weight: 600;
    height: 20px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #38BDF8);
    border-radius: 5px;
}

/* Scrollbars */
QScrollBar:vertical {
    background-color: #0F172A;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #334155;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
