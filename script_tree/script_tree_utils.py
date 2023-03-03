import logging
import os
import shutil
import subprocess
import time

from PySide2 import QtCore, QtWidgets, QtGui

from script_tree import ui_utils

if ui_utils.maya_check():
    from . import script_tree_dcc_maya as dcc_actions
    dcc_name = "Maya"
else:
    from . import script_tree_dcc_mobu as dcc_actions
    dcc_name = "Motionbuilder"

settings_name = "script_tree_" + dcc_name.lower()


class GlobalCache:
    shortcuts = []


class ScriptTreeConstants:
    """ Script tree constants"""
    window_text = "Script Tree"
    script_tree_folder_name = "ScriptTree"
    default_folder_name = "Scripts"

    user_documents_folder = os.path.expanduser('~/')
    if "documents" not in user_documents_folder.lower():  # Standalone interpreter goes to username folder not documents
        user_documents_folder += "/Documents"

    script_tree_folder = os.path.join(user_documents_folder, script_tree_folder_name, dcc_name).replace("\\", "/")
    default_script_folder = os.path.join(script_tree_folder, default_folder_name).replace("\\", "/")
    # default_script_folder = "M:/Art/Tools/{}/Scripts".format(dcc_name)
    script_backup_folder = os.path.join(script_tree_folder, "ScriptTree_ScriptBackup").replace("\\", "/")
    tree_backup_folder = os.path.join(script_tree_folder, "ScriptTree_TreeBackup").replace("\\", "/")

    user_input_filter_delay = 200

    default_script_content = "import pymel.core as pm"

    run_script_on_click = "Run Script on Double-Click"
    edit_script_on_click = "Edit Script on Double-Click"


class ScriptEditorSettings(QtCore.QSettings):
    """ Script Tree Settings """
    k_window_layout = "window/layout"
    k_folder_path = "script_tree/folder_path"
    k_double_click_action = "script_tree/double_click_action"

    def __init__(self):
        super(ScriptEditorSettings, self).__init__(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            'ScriptTree',
            settings_name  # saves in %APPDATA%\ScriptTree\script_tree_maya.ini
        )


def open_path_in_explorer(file_path):
    """ Open file in file manager.

    Args:
        file_path (str): Path ot launch from.

    Returns:
        None
    """
    if os.path.isdir(file_path):
        file_path += "/"

    file_path = file_path.replace("/", "\\")  # wow, I don't think I've done this intentionally before

    # Try and launch like we are in windows and cycle all OS.
    try:
        try:
            subprocess.Popen(r'open /select, "{}"'.format(file_path))

        except OSError:
            subprocess.Popen(['xdg-open', file_path])

    except OSError:
        subprocess.Popen(['open', file_path])


def get_backup_folder_for_script(script_path):
    """ Get backup script folder for script.

    Args:
        script_path (str): Script path.

    Returns:
        str to backup script directory.
    """
    file_name, file_extension = os.path.splitext(os.path.basename(script_path))
    backup_dir = os.path.join(ScriptTreeConstants.script_backup_folder, file_name)
    return backup_dir


def backup_script(script_path):
    """ Backup script

    Args:
        script_path (str): Path of script.

    Returns:
        None
    """
    if not os.path.exists(script_path):
        return

    try:
        file_name, file_extension = os.path.splitext(os.path.basename(script_path))

        unique_time = str(int(time.time()))
        backup_file_name = file_name + "_BACKUP_{}".format(unique_time) + file_extension

        backup_file_path = os.path.join(get_backup_folder_for_script(script_path), backup_file_name)

        if not os.path.exists(os.path.dirname(backup_file_path)):
            os.makedirs(os.path.dirname(backup_file_path))

        shutil.copy2(script_path, backup_file_path)

    except Exception as e:
        logging.error(e)


def backup_tree(script_folder):
    """ Backup script tree by copying folder to backup location.

    Args:
        script_folder (str): Path of script folder

    Returns:
        None
    """
    unique_time = str(int(time.time()))
    backup_directory_name = "ScriptTree_BACKUP_{}".format(unique_time)
    backup_directory_path = os.path.join(ScriptTreeConstants.tree_backup_folder, backup_directory_name)

    copy_directory(script_folder, backup_directory_path)

    logging.info("ScriptTree Network Folder Saved: {}".format(backup_directory_path))


def copy_directory(src, dst, symlinks=False, ignore=None):
    """ Copy directory

    Args:
        src (str): Path to script.
        dst (str): Path of script directory
        symlinks (bool | False):
        ignore (list | None): List of files to ignore.

    Returns:
        None
    """
    if not os.path.exists(dst):
        os.makedirs(dst)

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)

        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


'''
def check_script_tree_in_focus():
    script_tree_is_in_focus = False

    valid_tab_texts = (ScriptTreeConstants.window_text, "Script Editor")

    app = QtWidgets.QApplication.instance()
    widget = app.focusWidget()

    for i in range(20):  # Don't like while loops since it might get stuck in recursion. 20 feels like enough.
        widget_parent = widget.parent()
        if not widget_parent:
            continue

        if isinstance(widget, QtWidgets.QTabWidget):
            if widget.tabText(0) in valid_tab_texts:
                script_tree_is_in_focus = True
                break

        widget = widget_parent

    return script_tree_is_in_focus


def create_script_tree_hotkey(shortcut_seq=None, command=None, *args, **kwargs):
    """
    Create shortcut that only triggers when Script Tree is focused
    This exists because QtCore.Qt.WindowShortcut context also triggers when ScriptTree is docked to the main window

    Doesn't really work because it overwrites other QT Shortcuts, but hey, I tried.

    Credit to: https://bindpose.com/custom-global-hotkey-maya/ for the idea

    :param shortcut_seq:
    :param command:
    :param args:
    :param kwargs:
    :return:
    """
    if not command:
        return

    shortcut = QtWidgets.QShortcut(QtGui.QKeySequence.fromString(shortcut_seq), ui_utils.get_app_window())
    shortcut.setContext(QtCore.Qt.ApplicationShortcut)

    non_specific_command = partial(non_specific_hotkey, shortcut, shortcut_seq)
    hotkey_command = partial(script_tree_command, command, non_specific_command, *args, **kwargs)
    shortcut.activated.connect(hotkey_command)

    # add to cache so it can be disabled in reload_modules
    GlobalCache.shortcuts.append(shortcut)


def script_tree_command(cmd, non_specific_command):
    if check_script_tree_in_focus():
        cmd()
    else:
        non_specific_command()


def non_specific_hotkey(shortcut, shortcut_seq):
    shortcut.setEnabled(0)

    key_str = shortcut_seq.split("+")[-1]
    key_code = QtGui.QKeySequence.fromString(key_str)[0]

    keyboard_modifiers = QtCore.Qt.KeyboardModifier.NoModifier

    # woah, bitwise operators
    if "ctrl" in shortcut_seq.lower():
        keyboard_modifiers = keyboard_modifiers | QtCore.Qt.KeyboardModifier.ControlModifier

    if "shift" in shortcut_seq.lower():
        keyboard_modifiers = keyboard_modifiers | QtCore.Qt.KeyboardModifier.ShiftModifier

    if "alt" in shortcut_seq.lower():
        keyboard_modifiers = keyboard_modifiers | QtCore.Qt.KeyboardModifier.AltModifier

    # keyboard_modifiers = QtCore.Qt.KeyboardModifiers(*key_event_args) # I guess this works?
    # nope it did not work, turns out Python Bitwise operators are weird but cool

    e = QtGui.QKeyEvent(QtCore.QEvent.KeyPress, key_code, keyboard_modifiers)
    QtCore.QCoreApplication.postEvent(ui_utils.get_app_window(), e)

    dcc_actions.eval_deferred(partial(shortcut.setEnabled, 1))  # re-active the shortcut after evaluation has finished
'''