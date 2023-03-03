""" Tools to build Script tree UI """

# Standard
import functools
import os
import sys

if sys.version_info[0] >= 3:
    long = int

# Not even going to pretend to have Maya 2016 support
from PySide2 import QtCore
from PySide2 import QtGui
from PySide2 import QtWidgets

from script_tree.logger import log

UI_FILES_FOLDER = os.path.dirname(__file__)
ICON_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icons")


def maya_check():
    """ Add a simple way to check if we are using maya or not.

    Returns:
        True if maya is the current DCC
    """
    try:
        # Simply check to see if maya.cmds exists
        import maya.cmds
        return True
    except ImportError:
        # If not we know we are in another program like motion builder
        return False


def get_app_window():
    """ Get top window of DCC

    Returns:
        Qt Widget
    """
    top_window = None
    if maya_check():
        try:
            from shiboken2 import wrapInstance
            from maya import OpenMayaUI as omui
            maya_main_window_ptr = omui.MQtUtil().mainWindow()
            top_window = wrapInstance(long(maya_main_window_ptr), QtWidgets.QWidget)
            return top_window
        except ImportError as e:
            pass

    else:
        # Motionbuilder
        from pyfbsdk import FBSystem

        mb_window = None
        app = QtWidgets.QApplication.instance()
        for widget in app.topLevelWidgets():
            if ("MotionBuilder 20" + str(FBSystem().Version)[0:2]) in widget.windowTitle() \
                    or "MotionBuilder 2017" in widget.windowTitle() \
                    or "Untitled" in widget.windowTitle():
                mb_window = widget
                break

        if mb_window is None:
            log.warning("No motionbuilder window instance found")
        else:
            return mb_window

    return top_window


def delete_window(object_to_delete):
    """ Delete window

    Args:
        object_to_delete (QWidget): Widget to delete.

    Returns:
        None
    """
    qApp = QtWidgets.QApplication.instance()
    if not qApp:
        return

    for widget in qApp.topLevelWidgets():
        if "__class__" in dir(widget):
            if str(widget.__class__) == str(object_to_delete.__class__):
                widget.deleteLater()
                widget.close()


def create_qicon(icon_name):
    """ Create QIcon.

    Args:
        icon_name (str): Icon name including file extension in the icon folder.

    Returns:
        QtGui.QIcon if icon exists else none.
    """
    icon_path = os.path.join(ICON_FOLDER, icon_name)  # find in icons folder if not full path
    if not os.path.exists(icon_path):
        return

    return QtGui.QIcon(icon_path)


class WindowHandler(object):
    pass


wh = WindowHandler()

# Setup dockable widget for Maya
if maya_check():

    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
    from maya import OpenMayaUI as omui
    from maya import cmds


    class DockableWidget(MayaQWidgetDockableMixin, QtWidgets.QMainWindow):
        docking_object_name = "DockableWidget"

        def __init__(self, parent=None):
            """ Dockable widget for Maya

            Args:
                parent (QWindow | None): Apps parent widget
            """
            super(DockableWidget, self).__init__(parent=parent)
            self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setObjectName(self.docking_object_name)  # this one is important
            self.setWindowTitle('Custom Maya Mixin Workspace Control')

        def apply_ui_widget(self, widget):
            """ Apply Ui to widget.

            Args:
                widget (QWidget): Widget to set.

            Returns:
                None
            """
            self.setCentralWidget(widget)


    def create_dockable_widget(widget_class,
                               restore=False, restore_script="create_dockable_widget(restore=True)",
                               force_refresh=False
                               ):
        """ Create dockable widget

        Args:
            widget_class (Class):  Widget Class
            restore (Bool | False): If widget should be restored.
            restore_script (str | create_dockable_widget(restore=True)): Restore script
            force_refresh (Bool | False): If refresh should be forced

        Returns:
            Class of widget instance
        """
        if force_refresh:
            if widget_class.docking_object_name in wh.__dict__.keys():
                wh.__dict__.pop(widget_class.docking_object_name)

            workspace_control_name = widget_class.docking_object_name + "WorkspaceControl"
            if cmds.workspaceControl(workspace_control_name, q=True, exists=True):
                cmds.workspaceControl(workspace_control_name, e=True, close=True)
                cmds.deleteUI(workspace_control_name, control=True)

        if restore:
            # Grab the created workspace control with the following.
            restored_control = omui.MQtUtil.getCurrentParent()

        widget_instance = wh.__dict__.get(widget_class.docking_object_name)

        if widget_instance is None:
            # Create a custom mixin widget for the first time
            widget_instance = widget_class()  # type: DockableWidget
            wh.__dict__[widget_class.docking_object_name] = widget_instance

        if restore:
            # Add custom mixin widget to the workspace control
            mixin_ptr = omui.MQtUtil.findControl(widget_class.docking_object_name)
            omui.MQtUtil.addWidgetToMayaLayout(long(mixin_ptr), long(restored_control))
        else:
            # Create a workspace control for the mixin widget by passing all the needed parameters.
            # See workspaceControl command documentation for all available flags.
            widget_instance.show(dockable=True, height=600, width=480, uiScript=restore_script)

        return widget_instance

else:
    # Create dockable widget for MotionBuilder
    class DockableWidget(QtWidgets.QDockWidget):
        docking_object_name = "DockableWidget"

        def __init__(self, parent=get_app_window()):
            """ Dockable widget for Motion Builder

            Args:
                parent (QWindow): Apps parent widget
            """
            delete_window(self)
            super(DockableWidget, self).__init__(parent=parent)
            # self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
            self.setObjectName(self.docking_object_name)  # this one is important
            self.setWindowTitle('MotionBuilder Dockable Widget')
            self.setFloating(True)

        def apply_ui_widget(self, widget):
            """ Apply Ui to widget.

            Args:
                widget (QWidget): Widget to set.

            Returns:
                None
            """
            self.setWidget(widget)


    def create_dockable_widget(widget_class,
                               restore=False, restore_script="create_dockable_widget(restore=True)",
                               force_refresh=False
                               ):
        """ Create dockable widget

        Args:
            widget_class (Class):  Widget Class
            restore (Bool | False): If widget should be restored.
            restore_script (str | create_dockable_widget(restore=True)): Restore script
            force_refresh (Bool | False): If refresh should be forced

        Returns:
            Class of widget instance
        """
        widget_instance = widget_class()
        widget_instance.show()
        return widget_instance


def build_menu_from_action_list(actions, menu=None, is_sub_menu=False):
    """ Build menu action list.

    Args:
        actions (list): list of strings of actions.
        menu (QMenu | None): Qmenu to add object to.
        is_sub_menu (Bool | False): if menu is a sub menu.

    Returns:
        QMenu with actions.
    """
    if not menu:
        menu = QtWidgets.QMenu()

    for action in actions:
        if action == "-":
            menu.addSeparator()
            continue

        for action_title, action_command in action.items():
            if action_title == "RADIO_SETTING":
                # Create RadioButtons for QSettings object
                settings_obj = action_command.get("settings")  # type: QtCore.QSettings
                settings_key = action_command.get("settings_key")  # type: str
                choices = action_command.get("choices")  # type: list
                default_choice = action_command.get("default")  # type: str
                on_trigger_command = action_command.get("on_trigger_command")  # function to trigger after setting value

                # Has choice been defined in settings?
                item_to_check = settings_obj.value(settings_key)

                # If not, read from default option argument
                if not item_to_check:
                    item_to_check = default_choice

                grp = QtWidgets.QActionGroup(menu)
                for choice_key in choices:
                    action = QtWidgets.QAction(choice_key, menu)
                    action.setCheckable(True)

                    if choice_key == item_to_check:
                        action.setChecked(True)

                    action.triggered.connect(functools.partial(set_settings_value,
                                                               settings_obj,
                                                               settings_key,
                                                               choice_key,
                                                               on_trigger_command))
                    menu.addAction(action)
                    grp.addAction(action)

                grp.setExclusive(True)
                continue

            if isinstance(action_command, list):
                sub_menu = menu.addMenu(action_title)
                build_menu_from_action_list(action_command, menu=sub_menu, is_sub_menu=True)
                continue

            atn = menu.addAction(action_title)
            atn.triggered.connect(action_command)

    if not is_sub_menu:
        cursor = QtGui.QCursor()
        menu.exec_(cursor.pos())

    return menu


def set_settings_value(settings_obj, key, value, post_set_command):
    """ Set settings value.

    Args:
        settings_obj (QtCore.QSettings): QSetting.
        key (str): Setting name.
        value (list): list of actions.
        post_set_command (function): on trigger command.

    Returns:
        None
    """
    settings_obj.setValue(key, value)
    post_set_command()
