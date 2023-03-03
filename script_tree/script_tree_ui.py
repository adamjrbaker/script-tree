""" Script Editor UI"""
__author__ = "Richard Brenick - RichardBrenick@gmail.com"
__created__ = "2020-09-26"
__modified__ = "2022-03-01"

import os
import re
import runpy
import subprocess

from Qt import QtCore, QtWidgets

from script_tree import script_tree_utils as stu
from script_tree import ui_utils
from script_tree.logger import log

if ui_utils.maya_check():
    from script_tree import script_tree_dcc_maya as dcc_actions
else:
    from script_tree import script_tree_dcc_mobu as dcc_actions

lk = stu.ScriptTreeConstants


class ScriptTreeWindow(ui_utils.DockableWidget, QtWidgets.QMainWindow):
    docking_object_name = "ScriptTreeWindow"

    def __init__(self, *args, **kwargs):
        """ Script Tree window.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super(ScriptTreeWindow, self).__init__(*args, **kwargs)
        self.setWindowTitle(lk.window_text)

        self.ui = ScriptTreeWidget()
        self.apply_ui_widget(self.ui)

        self.recently_closed_scripts = []

        self.settings = stu.ScriptEditorSettings()

        self.context_menu_actions = [
            {"Run Script": self.action_run_script},
            {"Edit Script": self.action_open_script},
            "-",
            {"RADIO_SETTING": {"settings": self.settings,
                               "settings_key": self.settings.k_double_click_action,
                               "choices": [lk.run_script_on_click, lk.edit_script_on_click],
                               "default": lk.run_script_on_click,
                               "on_trigger_command": self.action_setup_double_click_connections
                               }},
            "-",
            {"Copy path": self.action_copy_path_to_clipboard},
            {"Show in explorer": self.action_open_path_in_explorer},
            {"Open backup folder": self.action_open_backup_folder},
            "-",
            {"Save all temporary tabs": dcc_actions.save_script_editor},
            {"Backup Script Tree": self.action_backup_tree}
        ]

        # MotionBuilder crashes on menuBar for some reason
        file_menu = self.menuBar().addMenu("File") if ui_utils.maya_check() else None
        edit_menu = self.menuBar().addMenu("Edit") if ui_utils.maya_check() else None

        # File Menu
        self.create_action("Ctrl+N", text="New Script",
                           command=self.action_new_tab, menu=file_menu)
        self.create_action("Ctrl+O", text="Open Script",
                           command=lambda: self.action_open_script(prompt_path=True), menu=file_menu)
        self.create_action("Ctrl+S", text="Save Script",
                           command=self.action_save_tab, menu=file_menu)
        self.create_action("Ctrl+Shift+S", text="Save Script as...",
                           command=lambda: self.action_save_tab(prompt_path=True), menu=file_menu)
        self.create_action("Ctrl+W", text="Close Script",
                           command=self.action_close_tab, menu=file_menu)
        self.create_action("Ctrl+Shift+T", text="Reopen closed Script",
                           command=self.action_reopen_recently_closed, menu=file_menu)
        self.create_action("F5", text="Reload Script",
                           command=dcc_actions.reload_selected_tab, menu=file_menu)

        # Edit Menu
        self.create_action("Ctrl+F", text="Find/Replace",
                           command=dcc_actions.open_search_dialog, menu=edit_menu)
        self.create_action("Ctrl+Shift+F", text="Find in ScriptTree",
                           command=self.open_script_search_dialog, menu=edit_menu)
        self.create_action("Alt+Shift+D", text="Clear Output",
                           command=dcc_actions.clear_script_output, menu=edit_menu)
        self.create_action("Ctrl+Alt+S", text="Insert pm.selected()[0]",
                           command=dcc_actions.insert_pm_selected, menu=edit_menu)
        self.create_action("Ctrl+/", text="Toggle Comment",
                           command=dcc_actions.toggle_comment_selected_lines, menu=edit_menu)

        self.setup_connections()

        # read folder from settings, otherwise set to default folder
        folder_path = self.settings.value(stu.ScriptEditorSettings.k_folder_path, defaultValue=lk.default_script_folder)
        self.action_set_folder(folder_path)

        # setup QTimer for script filtering (so we don't immediately search for every character)
        self.filter_timer = QtCore.QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.filter_results)

        # hook up shortcut actions to the script editor widget after everything is loaded and the widget might exist
        dcc_actions.eval_deferred(self.add_actions_to_script_editor)

    def create_action(self, shortcut, command=None, text="", menu=None):
        """ Create right click button action.

        Args:
            shortcut (str): shortcut to trigger command.
            command (function | None): Function to run on trigger.
            text (str | ""): Test name of command.
            menu (Qmenu | None): Name of menu to add action too.

        Returns:

        """
        shortcut_action = QtWidgets.QAction(self)
        shortcut_action.setShortcut(shortcut)
        shortcut_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.addAction(shortcut_action)
        if command:
            shortcut_action.triggered.connect(command)
        if text:
            shortcut_action.setText(text)
        if menu:
            menu.addAction(shortcut_action)

    def add_actions_to_script_editor(self):
        """ Add actions to script editor widget.

        Returns:
            None
        """
        dcc_script_editor_widget = dcc_actions.get_script_editor_widget() # type: QtWidgets.QTabWidget
        if not dcc_script_editor_widget:
            return
        for action in self.actions():
            dcc_script_editor_widget.addAction(action)

    def setup_connections(self):
        """ Setup connections for tree items.

        Returns:
            None
        """
        # buttons and widget signals
        self.ui.set_folder_btn.clicked.connect(self.action_set_folder)
        self.ui.search_bar.textChanged.connect(self._user_input_filter)

        # right click menu
        self.ui.tree_view.customContextMenuRequested.connect(self.context_menu)

        # double click script
        self.action_setup_double_click_connections()

    def context_menu(self):
        """ Build context menu.

        Returns:
            QMenu with items added.
        """
        return ui_utils.build_menu_from_action_list(self.context_menu_actions)

    # signaled from ui
    def _user_input_filter(self):
        """ User input filer.

        Returns:
            None
        """
        self.filter_timer.start(lk.user_input_filter_delay)

    def filter_results(self):
        """ get results of filter.

        Returns:
            None
        """

        filter_text = re.sub(r'[^\x00-\x7F]+', '', self.ui.search_bar.text())  # strip unicode characters until py3

        if not filter_text:
            self.ui.model.setNameFilters(self.ui.default_filter)
            self.ui.tree_view.collapseAll()
        else:
            filters = []
            for filter_string in filter_text.split(","):
                filter_string = filter_string.replace(" ", "")
                filters.append("*{}*.py".format(filter_string))
                filters.append("*{}*.mel".format(filter_string))
            self.ui.tree_view.expandAll()
            self.ui.model.setNameFilters(filters)

    def open_script_search_dialog(self):
        """ Open script editor search dialog.

        Returns:
            None
        """
        win = SearchDialog(self,
                           root_folder=self.ui.get_script_folder(),
                           search_string=dcc_actions.get_selected_script_text()
                           )
        win.show()
        win.resize(800, 300)

    # Actions
    @staticmethod
    def action_new_tab():
        """ Build new tab.

        Returns:
            None
        """
        dcc_actions.create_new_tab(default_script_content=lk.default_script_content)

    def action_open_script(self, prompt_path=False):
        """ Action to open script in script editor.

        Args:
            prompt_path (bool | False):  If prompt to open should come up.

        Returns:
            None
        """
        if prompt_path is True:
            script_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Script",
                                                                   dir=self.ui.get_script_folder(),
                                                                   filter="Script File (*.py *.mel)")
            if not script_path:
                return

        else:
            script_path = self.ui.get_selected_path()

        if os.path.isdir(script_path):
            return

        dcc_actions.open_script(script_path)
        log.info("Opened: {}".format(script_path))

    def action_save_tab(self, prompt_path=False):
        """ Action to save script in editor.

        Args:
            prompt_path (bool | False):  If prompt to open should come up.

        Returns:
            None
        """

        script_path = dcc_actions.get_selected_script_path()

        if prompt_path or not script_path:
            script_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Script",
                                                                   dir=self.ui.get_script_folder(),
                                                                   filter="Python File (*.py);;MEL File (*.mel)")
            if not script_path:
                return

        stu.backup_script(script_path)
        dcc_actions.save_selected_tab(script_path)

    def action_close_tab(self):
        """ Close tab of selected script.

        Returns:
            None
        """
        self.recently_closed_scripts.append(dcc_actions.get_selected_script_path())
        dcc_actions.delete_selected_tab()

    def action_open_path_in_explorer(self):
        """ Open selected script in file browser.

        Returns:
            None
        """
        stu.open_path_in_explorer(self.ui.get_selected_path())
        
    def action_copy_path_to_clipboard(self):
        """ Copy script path to clipboard.

        Returns:
            None
        """
        clipboard = QtWidgets.QApplication.clipboard()
        path = self.ui.get_selected_path()
        clipboard.setText(path)

    def action_open_backup_folder(self):
        """ Open up script backup folder.

        Returns:
            None
        """
        backup_folder = stu.get_backup_folder_for_script(self.ui.get_selected_path())
        if not os.path.exists(backup_folder):
            backup_folder = lk.script_backup_folder
        stu.open_path_in_explorer(backup_folder)

    def action_backup_tree(self):
        """ Back up script tree

        Returns:
            None
        """
        result = QtWidgets.QMessageBox.question(self, "Backup ScriptTree?",
                                                "This will make a local copy of the entire script tree folder",
                                                QtWidgets.QMessageBox.Ok,
                                                QtWidgets.QMessageBox.Cancel
                                                )
        if result == QtWidgets.QMessageBox.Ok:
            stu.backup_tree(self.ui.get_script_folder())

    def action_set_folder(self, folder_path=None):
        """ Set folder path.

        Args:
            folder_path (str | None): Path to script folder.

        Returns:
            None
        """
        if not folder_path:
            folder_path = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                                     "Choose Script Folder",
                                                                     dir=self.ui.get_script_folder())
            if not folder_path:
                return

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        self.ui.set_script_folder(folder_path)

        self.settings.setValue(stu.ScriptEditorSettings.k_folder_path, folder_path)

    def action_reopen_recently_closed(self):
        """ Reopen recently closed file.

        Returns:
            None
        """
        if not len(self.recently_closed_scripts):
            return
        recent_script_path = self.recently_closed_scripts.pop(-1)
        if recent_script_path:  # recent_script_path may be an empty string if it doesn't have a path defined
            dcc_actions.open_script(recent_script_path)

    def action_run_script(self):
        """ Run script.

        Returns:
            None
        """
        file_path = self.ui.get_selected_path()
        if os.path.isdir(file_path):
            return

        if file_path.endswith(".py"):
            cmd = "import runpy; runpy.run_path('{}', init_globals=globals(), run_name='__main__')".format(file_path)
            exec_command = 'python("{}")'.format(cmd)
            runpy.run_path(file_path, init_globals=globals(), run_name="__main__")

        elif file_path.endswith(".mel"):
            log.warning("TODO: add Mel support")
            exec_command = ""
        else:
            exec_command = ""

        log.info("Executed: {}".format(file_path))
        dcc_actions.add_to_repeat_commands(exec_command)

    def action_setup_double_click_connections(self):
        """ Switch between opening or running the script on double click.

        Returns:
            None
        """

        try:
            self.ui.tree_view.doubleClicked.disconnect()
        except RuntimeError:
            pass

        settings_value = self.settings.value(self.settings.k_double_click_action, defaultValue=lk.edit_script_on_click)

        if settings_value == lk.edit_script_on_click:
            self.ui.tree_view.doubleClicked.connect(self.action_open_script)
        else:
            self.ui.tree_view.doubleClicked.connect(self.action_run_script)


class ScriptTreeWidget(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        """ Script tree widget.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super(ScriptTreeWidget, self).__init__(*args, **kwargs)

        self.folder_path = QtWidgets.QLineEdit()

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("search")
        self.search_bar.setClearButtonEnabled(True)

        self.default_filter = ["*.py", "*.mel"]

        self.set_folder_btn = QtWidgets.QPushButton("...")

        self.model = QtWidgets.QFileSystemModel()
        # self.model.setRootPath(self.folder)
        self.model.setFilter(QtCore.QDir.AllDirs | QtCore.QDir.NoDotAndDotDot | QtCore.QDir.AllEntries)
        self.model.setNameFilters(self.default_filter)
        self.model.setNameFilterDisables(False)

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setModel(self.model)
        # self.tree_view.setRootIndex(self.model.index(self.folder))

        self.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        # self.tree_view.customContextMenuRequested.connect(self.context_menu_file_system)

        # self.treeView.setColumnWidth(0, 300)
        self.tree_view.hideColumn(1)
        self.tree_view.hideColumn(2)
        self.tree_view.hideColumn(3)
        self.tree_view.setHeaderHidden(True)

        # Add to main layout
        self.main_layout = QtWidgets.QVBoxLayout()
        file_line_layout = QtWidgets.QHBoxLayout()
        file_line_layout.addWidget(self.folder_path)
        file_line_layout.addWidget(self.set_folder_btn)

        self.main_layout.addLayout(file_line_layout)
        self.main_layout.addWidget(self.search_bar)
        self.main_layout.addWidget(self.tree_view)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

        self.setLayout(self.main_layout)

    def get_selected_path(self):
        """ Get path of selected item

        Returns:
            str of path of selected item.
        """
        index = self.tree_view.currentIndex()
        file_path = self.model.filePath(index)
        return file_path.replace("\\", "/")

    def get_script_folder(self):
        """ Get script folder path.

        Returns:
            str of script folder.
        """
        return self.folder_path.text()

    def set_script_folder(self, folder_path):
        """ Set script tree folder.

        Args:
            folder_path (str): Path to script folder to set.

        Returns:
            None
        """
        self.model.setRootPath(folder_path)
        self.tree_view.setRootIndex(self.model.index(folder_path))
        self.folder_path.setText(folder_path)


class SearchDialog(QtWidgets.QDialog):
    def __init__(self, parent=ui_utils.get_app_window(), root_folder="", search_string=""):
        """

        Args:
            parent (Qt Widget | ui_utils.get_app_window()):  Parent widget.
            root_folder (str | ""): foot script folder
            search_string (str | ""): Search value.
        """
        ui_utils.delete_window(self)
        super(SearchDialog, self).__init__(parent)

        main_layout = QtWidgets.QVBoxLayout()

        desc_text = "Search the entire ScriptTree folder for a specific string"
        desc_label = QtWidgets.QLabel(desc_text)

        self.folder_LE = QtWidgets.QLineEdit(root_folder)

        if not search_string:
            search_string = "SEARCH STRING"  # just to make sure it's not blank
        self.search_text_LE = QtWidgets.QLineEdit(search_string)
        self.search_text_LE.setPlaceholderText("search text")

        self.search_BTN = QtWidgets.QPushButton("Search")
        self.search_BTN.clicked.connect(self.start_search)

        main_layout.addWidget(desc_label)
        main_layout.addWidget(self.folder_LE)
        main_layout.addWidget(self.search_text_LE)
        main_layout.addWidget(self.search_BTN)

        self.setLayout(main_layout)
        self.setWindowTitle("Search ScriptTree")

    def start_search(self):
        """ Search for string using commandline findstr

        Returns:
            None
        """
        root_folder = self.folder_LE.text()
        str_to_find = self.search_text_LE.text()
        log.info("Searching {} for '{}'".format(root_folder, str_to_find))

        proc = subprocess.Popen("findstr /s /n " + str_to_find + " *.py *.mel",
                                cwd=root_folder,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        std_out_data, std_err_data = proc.communicate()
        log.info("Search Results:\n")
        log.info(std_out_data)


def main(restore=False, force_refresh=False):
    """ Launch widget creation.

    Args:
        restore (bool | False): if widget should be restored.
        force_refresh (bool | False): If widget should be forced refreshed.

    Returns:
        QtWidgets.QDockWidget
    """
    restore_script = "import script_tree; script_tree.main(restore=True)"

    return ui_utils.create_dockable_widget(ScriptTreeWindow,
                                           restore=restore,
                                           restore_script=restore_script,
                                           force_refresh=force_refresh
                                           )
