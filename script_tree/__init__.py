def main(*args, **kwargs):
    try:
        import Qt
    except ImportError:
        from PySide2 import QtWidgets, QtCore

        box = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Icon.Warning,
            'Script Editor Load',
            'Missing QT.py Package\nScript Tree is built on QT.py and unable to load wihtout it.',
            QtWidgets.QMessageBox.StandardButton.Cancel,
            None,
            QtCore.Qt.Dialog | QtCore.Qt.MSWindowsFixedSizeDialogHint | QtCore.Qt.WindowContextHelpButtonHint
        )
        box.setWhatsThis('Script Tree install error.')
        box.exec_()

    from . import script_tree_ui
    return script_tree_ui.main(*args, **kwargs)


def reload_module():
    import sys
    import os
    if sys.version_info[0] >= 3:
        from importlib import reload
    else:
        from imp import reload

    from . import ui_utils
    from . import script_tree_utils

    if os.path.basename(sys.executable) == "maya.exe":
        from . import script_tree_dcc_maya as dcc_actions
    else:
        from . import script_tree_dcc_mobu as dcc_actions

    from . import script_tree_ui

    # Remove all shortcuts from the cache so we can reload and let them go
    for shortcut in script_tree_utils.GlobalCache.shortcuts:
        shortcut.setEnabled(0)
        del shortcut

    reload(ui_utils)
    reload(script_tree_utils)
    reload(dcc_actions)
    reload(script_tree_ui)
