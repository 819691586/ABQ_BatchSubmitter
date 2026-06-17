from abaqusGui import *
from abaqusConstants import *
import os
import sys


class BatchSubmitterForm(AFXForm):

    def __init__(self, owner):
        AFXForm.__init__(self, owner)

        self.cmd = AFXGuiCommand(
            self, 'create_jobs', 'abq_batch_submitter_kernel',
            registerQuery=False
        )
        self.folderKw = AFXStringKeyword(self.cmd, 'folder', TRUE)
        self.filesKw = AFXStringKeyword(self.cmd, 'files', TRUE)
        self.cpusKw = AFXIntKeyword(self.cmd, 'cpus', TRUE)
        self.userSubKw = AFXStringKeyword(self.cmd, 'userSubroutine', FALSE)
        self.submitKw = AFXBoolKeyword(
            self.cmd, 'submitNow', AFXBoolKeyword.TRUE_FALSE, TRUE, False
        )

        self.folderPickKw = AFXStringKeyword(None, '', FALSE)
        self.subPickKw = AFXStringKeyword(None, '', FALSE)
        self.folderPatternIndexTgt = AFXIntTarget(0)
        self.subPatternIndexTgt = AFXIntTarget(0)

        self.folderKw.setValue('')
        self.filesKw.setValue('[]')
        self.cpusKw.setValue(8)
        self.userSubKw.setValue('')

    def getFirstDialog(self):
        self.folderKw.setValue('')
        self.filesKw.setValue('[]')
        self.userSubKw.setValue('')
        self.mainDB = BatchSubmitterDB(self)
        return self.mainDB

    def doCustomChecks(self):
        dialog = self.getCurrentDialog()
        folder = self.folderKw.getValue().strip().strip('"')
        user_sub = self.userSubKw.getValue().strip().strip('"')
        files = self.mainDB.getSelectedFiles()

        if not os.path.isdir(folder):
            showAFXErrorDialog(dialog, 'Input Folder does not exist.')
            dialog.onKeywordError(self.folderKw)
            return False
        if not [f for f in os.listdir(folder) if f.lower().endswith('.inp')]:
            showAFXErrorDialog(dialog, 'No .inp files found in Input Folder.')
            dialog.onKeywordError(self.folderKw)
            return False
        if self.cpusKw.getValue() < 1:
            showAFXErrorDialog(dialog, 'CPUs / Job must be at least 1.')
            dialog.onKeywordError(self.cpusKw)
            return False
        if user_sub and not os.path.isfile(user_sub):
            showAFXErrorDialog(dialog, 'User Subroutine file does not exist.')
            dialog.onKeywordError(self.userSubKw)
            return False
        if not files:
            showAFXErrorDialog(dialog, 'Select at least one .inp file.')
            return False
        self.filesKw.setValue(repr(files))
        return True


class BatchSubmitterDB(AFXDataDialog):

    [
        ID_PICK_FOLDER, ID_FOLDER_SELECTED, ID_RELOAD, ID_SELECT_ALL, ID_SELECT_NONE,
        ID_PICK_SUB, ID_SUB_SELECTED,
    ] = range(AFXDataDialog.ID_LAST, AFXDataDialog.ID_LAST + 7)

    def __init__(self, form):
        AFXDataDialog.__init__(
            self, form, 'Batch Submit INP Jobs',
            self.OK | self.CANCEL, DIALOG_ACTIONS_SEPARATOR | DECOR_RESIZE
        )
        self.form = form
        self.folderDb = None
        self.subFileDb = None
        self.getActionButton(self.ID_CLICKED_OK).setText('Run')

        FXMAPFUNC(self, SEL_COMMAND, self.ID_PICK_FOLDER, BatchSubmitterDB.onPickFolder)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_FOLDER_SELECTED, BatchSubmitterDB.onFolderSelected)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_RELOAD, BatchSubmitterDB.onReload)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_SELECT_ALL, BatchSubmitterDB.onSelectAll)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_SELECT_NONE, BatchSubmitterDB.onSelectNone)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_PICK_SUB, BatchSubmitterDB.onPickSub)
        FXMAPFUNC(self, SEL_COMMAND, self.ID_SUB_SELECTED, BatchSubmitterDB.onSubSelected)

        note = (
            'Choose the input files to create and submit. Monitor, results, '
            'and kill are handled by the native Abaqus Job Manager.'
        )
        AFXNote(self, note)

        box = FXGroupBox(self, 'Settings', FRAME_GROOVE | LAYOUT_FILL_X)
        row = FXHorizontalFrame(box, LAYOUT_FILL_X)
        AFXTextField(row, 76, 'Input Folder:', form.folderKw, 0)
        FXButton(row, 'Browse Folder...', None, self, self.ID_PICK_FOLDER)

        row = FXHorizontalFrame(box, LAYOUT_FILL_X)
        AFXTextField(row, 76, 'User Subroutine:', form.userSubKw, 0)
        FXButton(row, 'Browse Fortran...', None, self, self.ID_PICK_SUB)

        row = FXHorizontalFrame(box, LAYOUT_FILL_X)
        AFXTextField(row, 10, 'CPUs / Job:', form.cpusKw, 0)
        FXCheckButton(row, 'Submit After Creation', form.submitKw, 0, CHECKBUTTON_NORMAL)

        listBox = FXGroupBox(self, 'Input Files', FRAME_GROOVE | LAYOUT_FILL_X | LAYOUT_FILL_Y)
        buttons = FXHorizontalFrame(listBox, LAYOUT_FILL_X)
        FXButton(buttons, 'Refresh File List', None, self, self.ID_RELOAD)
        FXButton(buttons, 'Select All', None, self, self.ID_SELECT_ALL)
        FXButton(buttons, 'Select None', None, self, self.ID_SELECT_NONE)
        vf = FXVerticalFrame(
            listBox, FRAME_SUNKEN | FRAME_THICK | LAYOUT_FILL_X | LAYOUT_FILL_Y,
            0, 0, 0, 0, 0, 0, 0, 0
        )
        self.tree = AFXOptionTreeList(vf, 1, LAYOUT_FILL_X | LAYOUT_FILL_Y)
        self.tree.setNumVisible(18)

    def onPickFolder(self, sender, sel, ptr):
        self.form.folderPickKw.setValue(self.form.folderKw.getValue())
        patterns = 'Directories (*)\nAll files (*.*)'
        self.folderDb = AFXFileDialog(
            self, 'Select Input Folder',
            self.form.folderPickKw, None, None, 0,
            AFXSELECTFILE_DIRECTORY, patterns, self.form.folderPatternIndexTgt
        )
        self.folderDb.setTarget(self)
        self.folderDb.setSelector(self.ID_FOLDER_SELECTED)
        self.folderDb.create()
        self.folderDb.showModal()
        return 1

    def onFolderSelected(self, sender, sel, ptr):
        if self.folderDb.getPressedButtonId() == AFXDialog.ID_CLICKED_OK:
            folder = self.form.folderPickKw.getValue().strip().strip('"')
            if folder:
                self.form.folderKw.setValue(folder)
                self.reloadInpList()
        self.folderDb.setTarget(None)
        return 1

    def onPickSub(self, sender, sel, ptr):
        patterns = (
            'Abaqus Fortran (*.for)\n'
            'Fortran source (*.f)\n'
            'Fortran 90 (*.f90)\n'
            'Fortran 95 (*.f95)\n'
            'All files (*.*)'
        )
        self.subFileDb = AFXFileDialog(
            self, 'Pick User Subroutine',
            self.form.subPickKw, None, None, 0,
            AFXSELECTFILE_EXISTING, patterns, self.form.subPatternIndexTgt
        )
        self.subFileDb.setTarget(self)
        self.subFileDb.setSelector(self.ID_SUB_SELECTED)
        self.subFileDb.create()
        self.subFileDb.showModal()
        return 1

    def onSubSelected(self, sender, sel, ptr):
        if self.subFileDb.getPressedButtonId() == AFXDialog.ID_CLICKED_OK:
            path = self.form.subPickKw.getValue().strip().strip('"')
            if path:
                self.form.userSubKw.setValue(path)
        self.subFileDb.setTarget(None)
        return 1

    def onReload(self, sender, sel, ptr):
        self.reloadInpList()
        return 1

    def onSelectAll(self, sender, sel, ptr):
        self.setAllChecks(True)
        return 1

    def onSelectNone(self, sender, sel, ptr):
        self.setAllChecks(False)
        return 1

    def show(self):
        AFXDataDialog.show(self)
        self.reloadInpList()

    def reloadInpList(self):
        self.tree.clearItems()
        folder = self.form.folderKw.getValue().strip().strip('"')
        if os.path.isdir(folder):
            files = [f for f in os.listdir(folder) if f.lower().endswith('.inp')]
            files.sort()
            for name in files:
                self.tree.addItemLast(name)
        if self.shown():
            self.tree.create()
            self.resize(self.getDefaultWidth(), self.getDefaultHeight())

    def setAllChecks(self, checked):
        item = self.tree.getFirstItem()
        while item:
            item.setCheck(checked)
            item = item.getNext()

    def getSelectedFiles(self):
        files = []
        item = self.tree.getFirstItem()
        while item:
            if item.getCheck():
                files.append(item.getText())
            item = item.getNext()
        return files


thisPath = os.path.abspath(__file__)
thisDir = os.path.dirname(thisPath).replace('\\', '/')
if thisDir not in sys.path:
    sys.path.append(thisDir)

kernelInit = (
    "import sys\n"
    "p = r'%s'\n"
    "if p not in sys.path: sys.path.append(p)\n"
    "import abq_batch_submitter_kernel\n"
    "reload(abq_batch_submitter_kernel)\n"
) % thisDir

toolset = getAFXApp().getAFXMainWindow().getPluginToolset()
toolset.registerGuiMenuButton(
    object=BatchSubmitterForm(toolset),
    buttonText='Jobs|Batch Submit INP Jobs...',
    kernelInitString=kernelInit,
    version='1.0',
    author='Codex',
    applicableModules=ALL,
    description='Select input files from a folder, create Abaqus jobs, and submit them.'
)


