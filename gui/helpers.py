# gui/helpers.py
import re
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt

class NumericTableWidgetItem(QTableWidgetItem):
    """
    Custom QTableWidgetItem for proper numeric sorting in a QTableWidget.
    Assumes that the data for sorting is set using Qt.ItemDataRole.EditRole.
    """
    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            self_data_val = self.data(Qt.ItemDataRole.EditRole)
            other_data_val = other.data(Qt.ItemDataRole.EditRole)

            # Handle cases where data might be None (e.g., empty cells or not set)
            if self_data_val is None and other_data_val is None:
                return False # Consider them equal for sorting if both are None
            if self_data_val is None:
                return True  # None is considered "less than" any actual number
            if other_data_val is None:
                return False # Any actual number is "greater than" None

            # Proceed with float conversion if data is present
            self_data_float = float(self_data_val)
            other_data_float = float(other_data_val)
            return self_data_float < other_data_float
        except (ValueError, TypeError, AttributeError):
            # Fallback to default string comparison if data isn't numeric,
            # convertible, or if an attribute error occurs (e.g. on non-item comparison)
            return super().__lt__(other)

def strip_ansi_codes(text_with_codes: str) -> str:
    """
    Removes ANSI escape sequences (used for color codes, etc.) from a string.
    """
    if not text_with_codes:
        return ""
    # Regular expression to match ANSI escape sequences
    # \x1B is ESC, [ is the Control Sequence Introducer (CSI)
    # [0-?]* matches any number of parameter bytes
    # [ -/]* matches any number of intermediate bytes
    # [@-~] matches the final byte
    ansi_escape_pattern = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape_pattern.sub('', text_with_codes)