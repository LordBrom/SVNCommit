import sublime
import sublime_plugin
import os.path
import subprocess
import functools
import datetime
import threading

sublime.avibeSVNCommitTicketNo = ""
sublime.avibeSVNCommitThisComment = ""
sublime.avibeSVNCommitLastComment = ""
sublime.avibeSVNCommitScopes = ['Commit Scope: Full Repository','Commit Scope: Current File','Commit Scope: Current Directory']
sublime.avibeSVNScopes = ['Full Repository','Current File','Current Directory']

threadLock = threading.Lock()
threads = []

def svn_settings():
    return sublime.load_settings( 'Preferences.sublime-settings' )

def svn_set_status_items(self):
    if self.view == None:
        self.view = self.active_window().active_view()
    view = self.view

    if svn_settings().get('SVN.show_status_bar_info', 1) == 1:
        self.svnDir = self.get_svn_dir()
        if len(self.svnDir) == 0:
            view.set_status('AAAsvnTool', 'SVN:' + u'\u2718')
            view.erase_status('AABsvnTool')
            view.erase_status('AACsvnTool')
        else:
            view.set_status('AAAsvnTool', 'SVN:' + u'\u2714')
            view.set_status('AABsvnTool', 'Scope: ' + str(svn_settings().get('SVN.commit_scope', 'repo')))

            if svn_settings().get('SVN.show_diff_in_status_bar', 0) == 1:
                self.svnDir = self.get_scoped_path('file')
                procText = self.run_svn_command([ "svn", "status", self.svnDir])

                if len(procText):
                    procText = procText.split( '\n' )[0].strip( )
                    procText = procText.split( )[0]

                    if procText == 'M':
                        view.set_status('AACsvnTool', 'diff:' + u'\u2260' )
                    else:
                        view.set_status('AACsvnTool', 'diff:' + u'\u003D' )
                else:
                    view.set_status('AACsvnTool', 'diff:' + u'\u003D' )


            else:
                view.erase_status('AACsvnTool')
    else:
        view.erase_status('AAAsvnTool')
        view.erase_status('AABsvnTool')
        view.erase_status('AACsvnTool')



class svnController():
    def get_svn_root_path(self):
        path = sublime.active_window().active_view().file_name( ).split( "\\" )

        svnFound = 0
        while 0 == svnFound and 0 != len( path ):
            path = path[:-1]
            currentDir = "\\".join( path )

            if os.path.isdir( currentDir + "\\.svn" ):
                return currentDir

        return ""

    def get_scoped_path(self, scope):
        filePath = sublime.active_window().active_view().file_name()
        repoPath = self.get_svn_root_path()

        if scope == 'repo':
            return repoPath
        elif scope == 'file':
            return filePath
        elif scope == 'dir':
            return os.path.dirname(filePath)
        else:
            return repoPath

    def get_svn_dir(self):
        try:
            self.svnDir = sublime.active_window().active_view().file_name( ).split( "\\" )

            svnFound = 0
            while 0 == svnFound and 0 != len( self.svnDir ):
                self.svnDir = self.svnDir[:-1]
                currentDir = "\\".join( self.svnDir )

                if os.path.isdir( currentDir + "\\.svn" ):
                    svnFound = 1

            if 0 == svnFound:
                return ""
        except:
            return ""

        return self.svnDir

    def run_svn_command(self, params):
        startupinfo = None
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        try:
            proc = subprocess.Popen(
                        params,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        startupinfo=startupinfo);
        except ValueError:
            print(ValueError)
            sublime.status_message( "SVN command failed." );
            return ""



        return proc.communicate()[0].strip( );

    def add_history(self, log):
        history = svn_settings().get('SVN.history', [])

        for item in list(history):
            if item == log:
                history.remove(item)

        history.reverse()
        history.append(log);
        history.reverse();
        svn_settings().set('SVN.history', history)
        sublime.save_settings('Preferences.sublime-settings')

    def show_output_panel(self, outputStr):
        window = sublime.active_window()
        output = window.get_output_panel("SVN");

        edit = output.begin_edit()

        output.insert(edit, 0, outputStr)
        window.run_command("show_panel", {"panel": "output.SVN"});
        edit = output.end_edit(edit)

    def do_commit(self, message):
        if self.svnDir == None:
            sublime.status_message( "No files selected to commit." );
            return

        if svn_settings().get('SVN.confirm_new_files_on_commit', 1):
            if self.first_commit(message):
                if sublime.ok_cancel_dialog("This file has not been commited to SVN using this message before. Would you like to continue?"):
                    test = 1
                else:
                    return

        procText = self.run_svn_command([ "svn", "commit", self.svnDir, "--message", message]);

        procText = procText.strip( ).split( '\n' )[-1].strip( );

        if not "Committed revision" in procText:
            procText = "Could not commit revision; check for conflicts or other issues."

        self.add_history(message)

        sublime.status_message( procText + " (" + message + ")" );

    def first_commit(self, message):
        is_first_commit = 1

        activeFile = self.get_scoped_path('file')
        logLimit = svn_settings().get('SVN.log_limit', 1000)
        procText = self.run_svn_command([ "svn", "log", "--limit", str(logLimit), activeFile]);
        lineArray = procText.strip( ).split( '\n' )

        for line in lineArray:
            if line[:1] == 'r':
                continue
            if line[:10] == '----------':
                continue
            if message in line:
                is_first_commit = 0
                break

        return is_first_commit



class svnUpdateStatusBarThread(threading.Thread, svnController):
    def __init__(self, view, name):
        threading.Thread.__init__(self)
        self.view = view
        self.name = name

    def start(self):
        self.run()

    def run(self):
        threadLock.acquire()
        # for num in range(100):
        #     print(str(num))
        svn_set_status_items(self)
        threadLock.release()

class ChangeLog(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        procText = self.run_svn_command([ "svn", "log", "-v", self.svnDir]);

        show_output_panel(procText)



class svnCommitCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir()
        if len(self.svnDir) == 0:
            return;

        self.svnDir = self.get_scoped_path(svn_settings().get('SVN.commit_scope', 'repo'))

        sublime.active_window().run_command("save")
        sublime.active_window().show_input_panel("Ticket number:", sublime.avibeSVNCommitTicketNo, self.on_ticket, None, None)
        pass

    def on_ticket(self, text):
        try:
            sublime.avibeSVNCommitTicketNo = text

            sublime.active_window().show_input_panel("Comment:", sublime.avibeSVNCommitThisComment, self.on_comment, None, None)
        except ValueError:
            pass

    def on_comment(self, text):
        sublime.avibeSVNCommitThisComment = text
        sublime.avibeSVNCommitLastComment = sublime.avibeSVNCommitTicketNo

        if len( sublime.avibeSVNCommitLastComment ):
            sublime.avibeSVNCommitLastComment = "#" + sublime.avibeSVNCommitLastComment + ": "

        sublime.avibeSVNCommitLastComment = sublime.avibeSVNCommitLastComment + sublime.avibeSVNCommitThisComment

        self.do_commit(sublime.avibeSVNCommitLastComment)

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0

class svnCommitLastCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir()
        if len(self.svnDir) == 0:
            return;

        if( 0 == len( sublime.avibeSVNCommitLastComment )):
            sublime.status_message( "Commit with comment (CTRL-ALT-B twice) to use this shortcut." );
            return

        self.svnDir = self.get_scoped_path(svn_settings().get('SVN.commit_scope', 'repo'))

        sublime.active_window().run_command("save")

        self.do_commit(sublime.avibeSVNCommitLastComment)

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0

class svnCommitBlankCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir()
        if len(self.svnDir) == 0:
            return;

        self.svnDir = self.get_scoped_path(svn_settings().get('SVN.commit_scope', 'repo'))

        sublime.active_window().run_command("save")

        self.do_commit("")

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0

class svnCommitHistoryCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir()
        if len(self.svnDir) == 0:
            return;

        self.svnDir = self.get_scoped_path(svn_settings().get('SVN.commit_scope', 'repo'))

        self.fileList = list(svn_settings().get('SVN.history', []))
        self.fileList.insert(min(len(self.fileList), 1), 'New Log')

        sublime.active_window().show_quick_panel(self.fileList, self.on_ticket)

    def on_ticket(self, index):
        try:
            message = self.fileList[index]

            if index == -1:
                pass
            elif message == 'New Log':
                sublime.active_window().run_command('svn_commit')
            else:
                self.do_commit(message)

        except ValueError:
            pass

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0



class svnShowChangesCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir();
        if len(self.svnDir) == 0:
            return;

        self.svnDir = self.get_scoped_path('file');

        procText = self.run_svn_command([ "svn", "diff", self.svnDir]);

        if len(procText):
            newView = sublime.active_window().new_file();
            newView.insert(edit, 0, procText);
            newView.set_syntax_file("Packages/Diff/Diff.tmLanguage");
            newView.set_scratch(1);
        else:
            sublime.status_message("The files match.");

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0

class svnDiscardChangesCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir();
        if len(self.svnDir) == 0:
            return;

        if sublime.ok_cancel_dialog("Are you sure you want to discard your changes?"):
            sublime.active_window().run_command("save")

            self.svnDir = self.get_scoped_path('file');

            sublime.status_message("file: " + str(self.svnDir));

            procText = self.run_svn_command([ "svn", "revert", self.svnDir]);
            procText = procText.strip( ).split( '\n' )[-1].strip( );

            if len(procText) == 0:
                procText = "There are no changes to discard."
            elif not "Reverted" in procText:
                procText = "Could not commit revision; check for conflicts or other issues."
            else:
                view = sublime.active_window().active_view();
                sublime.set_timeout(functools.partial(view.run_command, 'revert'), 0)

            sublime.status_message(procText);

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0

class svnUpdateRepoCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir();
        if len(self.svnDir) == 0:
            return;
        self.edit = edit;
        sublime.status_message("Select update scope");
        self.confirmList = list(sublime.avibeSVNScopes)
        sublime.active_window().show_quick_panel(self.confirmList, self.do_Update)

    def do_Update(self, index):
        self.scope = ''
        if index == -1 :
            return
        elif index == 0:
            self.svnDir = self.get_scoped_path('repo')
            self.scope = 'Repository'
        elif index == 1:
            self.svnDir = self.get_scoped_path('file')
            self.scope = 'File'
        else:
            self.svnDir = self.get_scoped_path('dir')
            self.scope = 'Directory'

        procTextPre = self.run_svn_command([ "svn", "update", self.svnDir]);
        procText = procTextPre.strip( ).split( '\n' )[-1].strip( );

        if "At revision" in procText:
            procText = self.scope + " is already up to date."
        elif "Updated" in procText:
            view = sublime.active_window().active_view();
            sublime.set_timeout(functools.partial(view.run_command, 'revert'), 0)

            self.show_output_panel(procTextPre)
        else:
            procText = "Could not commit revision; check for conflicts or other issues."

        sublime.status_message(procText);

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0

class svnAddFileCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_svn_dir();
        if len(self.svnDir) == 0:
            return;

        self.confirmList = ['Add current file to repo', 'Add current directory to repo']
        sublime.active_window().show_quick_panel(self.confirmList, self.do_Add)

    def do_Add(self, index):
        print('added')
        self.scope = ''
        if index == -1 :
            return
        elif index == 0:
            self.svnDir = self.get_scoped_path('file')
            self.scope = 'File'
        else:
            self.svnDir = self.get_scoped_path('dir')
            self.scope = 'Directory'

        self.svnDir = self.get_scoped_path('file')
        procText = self.run_svn_command([ "svn", "add", self.svnDir]);
        procText = procText.strip( ).split( '\n' )[-1].strip( );

        if "Illegal target" in procText:
            procText = "Could not add file(s); check for conflicts or other issues."
        else:
            print(procText)
            procText = "Added file(s) to repo"
        sublime.status_message(procText);

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0

class svnRepoStatusCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        self.svnDir = self.get_scoped_path('repo')
        procText = self.run_svn_command([ "svn", "status", self.svnDir]);
        self.show_output_panel(procText)

    def is_enabled(self):
        return len(str(self.get_svn_dir())) != 0


class svnSetScopeCommand(sublime_plugin.ApplicationCommand, svnController):
    def run(self, scope):
        svn_settings().set('SVN.commit_scope', scope)
        sublime.save_settings('Preferences.sublime-settings')

    def is_checked(self, scope):
        selScope = svn_settings().get('SVN.commit_scope', 'repo')
        return selScope == scope



class svnLogParser(svnController):
    def run(self):
        self.svnDir = self.get_scoped_path('repo')

        logLimit = svn_settings().get('SVN.log_limit', 1000)
        procText = self.run_svn_command([ "svn", "log", "-v", "--limit", str(logLimit), self.svnDir]);
        logList = procText.strip( ).split( '------------------------------------------------------------------------' );

        result = ''

        for log in logList:
            if len(log) == 0:
                continue

            splitLog = str(log + "|").strip().split( '\n' );
            print(splitLog)

            logDetails = splitLog[0].split('|')
            revision   = logDetails[0].strip( )
            author     = logDetails[1].strip( )
            timeStamp  = logDetails[2].strip( )
            msgLines   = logDetails[3].strip( )
            msgCount = int(msgLines.split(" ")[0])

            splitLogLength = len(splitLog) - 1

            fileList = [splitLog[num].strip( ) for num in range(2, splitLogLength - (1 + msgCount))]

            messageArray = [splitLog[num].strip( ) for num in range(splitLogLength - msgCount, (splitLogLength - msgCount) + msgCount)]
            message = '\n'.join([str(arrStr).strip( ) for arrStr in messageArray])

            if len(message) == 0:
                message = 'No Commit Message'

            result += '------------------------------------------------------------------------------------------------------------------------------------------------\n'
            result += revision + ": " + author + ": " + timeStamp + '\n'
            result += message + '\n\n'
            result += 'File List:\n'
            result += '\n'.join([str(arrStr) for arrStr in fileList]) + '\n'
            result += '\n\n'



        self.show_output_panel(result)


class svnEventListener(sublime_plugin.EventListener, svnController):
    def on_activated(self, view):
        thread = svnUpdateStatusBarThread(view, view.file_name())
        thread.start()
        threads.append(thread)

    def on_post_save(self, view):
        print(str(threads))
        thread = svnUpdateStatusBarThread(view, view.file_name())

        thread.start()
        threads.append(thread)

        # while thread.isAlive():
        #     print("alive")

        # print('finished')


class svnTestCommand(sublime_plugin.TextCommand, svnController):
    def run(self, edit):
        print('starting test command')
        for t in threads:
            if t.isAlive():
                print("Thread '" + t.name + "' is alive." )
            else:
                threads.remove(t)
                print("Thread '" + t.name + "' is dead." )

        print('ending test command')

