"""qt_helper - PySide6 Qt application bootstrap for MDS Viewer.

Standalone version of ui/qt/__init__.py (simplified).
"""
import importlib.util as _ilu
import logging
import sys

_LOG = logging.getLogger("mds_viewer.qt")

HAS_PYSIDE6 = _ilu.find_spec("PySide6") is not None
QT_BACKEND = "PySide6" if HAS_PYSIDE6 else None

_qt_app = None
_last_traceback = None


def _set_traceback(tb):
    global _last_traceback
    _last_traceback = tb


def get_last_traceback():
    return _last_traceback


def get_qt():
    """Return dict with QtWidgets/QtCore/QtGui/app/backend; None on failure."""
    global _qt_app
    if not HAS_PYSIDE6:
        try:
            import PySide6  # noqa: F401
        except ImportError as e:
            _set_traceback(f"PySide6 not installed: {e}")
            return None

    try:
        from PySide6 import QtWidgets, QtCore, QtGui
    except ImportError as e:
        _set_traceback(f"PySide6 import fail: {e}")
        _LOG.error("[get_qt] PySide6 import FAILED: %s", e)
        return None

    try:
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication(
                sys.argv if hasattr(sys, "argv") else [])
            _qt_app = app
    except Exception as e:
        _set_traceback(f"QApplication create fail: {e}")
        _LOG.error("[get_qt] QApplication FAIL: %s", e)
        return None

    return {
        "QtWidgets": QtWidgets, "QtCore": QtCore, "QtGui": QtGui,
        "app": app, "backend": "PySide6",
    }
