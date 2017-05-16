import sublime
import sublime_plugin
import os.path
import subprocess
import functools

sublime.avibeSVNCommitTicketNo = ""
sublime.avibeSVNCommitThisComment = ""
sublime.avibeSVNCommitLastComment = ""
sublime.avibeSVNCommitScopes = ['Commit Scope: Full Repository','Commit Scope: Current File','Commit Scope: Current Directory']
sublime.avibeSVNScopes = ['Full Repository','Current File','Current Directory']

class svnController():
	def get_commit_scope(self):
		s = sublime.load_settings('Preferences.sublime-settings')
		if not s.has('SVN.commit_scope'):
			return 'repo'
		else:
			return s.get('SVN.commit_scope')

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
		except:
			sublime.status_message( "SVN command failed." );
			return ""
		return proc.communicate()[0];

	def get_history(self):
		s = sublime.load_settings('Preferences.sublime-settings')

		if not s.has('SVN.history'):
			s.set('SVN.history', [])
			sublime.save_settings('Preferences.sublime-settings')

		return s.get('SVN.history')

	def add_history(self, log):
		s = sublime.load_settings('Preferences.sublime-settings')
		history = s.get('SVN.history')

		for item in list(history):
			if item == log:
				history.remove(item)

		history.reverse()
		history.append(log);
		history.reverse();
		s.set('SVN.history', history)
		sublime.save_settings('Preferences.sublime-settings')
		
class svnCommitCommand(sublime_plugin.TextCommand, svnController):
	def run(self, edit):
		self.svnDir = self.get_svn_dir()
		if len(self.svnDir) == 0:
			return;

		self.svnDir = self.get_scoped_path(self.get_commit_scope())

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

		procText = self.run_svn_command([ "svn", "commit", self.svnDir, "--message", sublime.avibeSVNCommitLastComment]);

		procText = procText.strip( ).split( '\n' )[-1].strip( );

		if not "Committed revision" in procText:
			procText = "Could not commit revision; check for conflicts or other issues."

		self.add_history(sublime.avibeSVNCommitLastComment)

		sublime.status_message( procText + " (" + sublime.avibeSVNCommitLastComment + ")" );

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

		self.svnDir = self.get_scoped_path(self.get_commit_scope())

		sublime.active_window().run_command("save")

		procText = self.run_svn_command([ "svn", "commit", self.svnDir, "--message", sublime.avibeSVNCommitLastComment]);

		procText = procText.strip( ).split( '\n' )[-1].strip( );

		if not "Committed revision" in procText:
			procText = "Could not commit revision; check for conflicts or other issues."

		sublime.status_message( procText + " (" + sublime.avibeSVNCommitLastComment + ")" );

	def is_enabled(self):
		return len(str(self.get_svn_dir())) != 0

class svnCommitBlankCommand(sublime_plugin.TextCommand, svnController):
	def run(self, edit):
		self.svnDir = self.get_svn_dir()
		if len(self.svnDir) == 0:
			return;

		self.svnDir = self.get_scoped_path(self.get_commit_scope())

		sublime.active_window().run_command("save")
		procText = self.run_svn_command([ "svn", "commit", self.svnDir, "--message", ""]);

		procText = procText.strip( ).split( '\n' )[-1].strip( );

		if not "Committed revision" in procText:
			procText = "Could not commit revision; check for conflicts or other issues."

		sublime.status_message( procText );

	def is_enabled(self):
		return len(str(self.get_svn_dir())) != 0

class svnCommitHistoryCommand(sublime_plugin.TextCommand, svnController):
	def run(self, edit):
		self.svnDir = self.get_svn_dir()
		if len(self.svnDir) == 0:
			return;

		self.svnDir = self.get_scoped_path(self.get_commit_scope())	

		self.fileList = list(self.get_history())
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

				procText = self.run_svn_command([ "svn", "commit", self.svnDir, "--message", message]);

				procText = procText.strip( ).split( '\n' )[-1].strip( );

				if not "Committed revision" in procText:
					procText = "Could not commit revision; check for conflicts or other issues."

				self.add_history(message)

				sublime.status_message( procText + " (" + message + ")" );

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
			newWindow = sublime.active_window().new_file();
			newWindow.insert(edit, 0, procText);
			newWindow.set_syntax_file("Packages/Diff/Diff.tmLanguage");
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

			newWindow = sublime.active_window().new_file();
			newWindow.insert(self.edit, 0, procTextPre);
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

class svnSetScopeCommand(sublime_plugin.ApplicationCommand, svnController):
	def run(self, scope):
		s = sublime.load_settings('Preferences.sublime-settings')
		s.set('SVN.commit_scope', scope)
		sublime.save_settings('Preferences.sublime-settings')

	def is_checked(self, scope):
		selScope = self.get_commit_scope()
		return selScope == scope



class svnEventListener(sublime_plugin.EventListener, svnController):
	def on_activated(self, view):
		self.svnDir = self.get_svn_dir()
		if len(self.svnDir) == 0:
			view.set_status('AAAsvnTool', 'SVN:' + u'\u2718')
		else:
			view.set_status('AAAsvnTool', 'SVN:' + u'\u2714' )






class svnTestCommand(sublime_plugin.TextCommand, svnController):
	def run(self, edit):
		print('starting test command')

		test = sublime.ok_cancel_dialog('test')
		print(test)

		# self.svnDir = self.get_scoped_path('file')
		# procText = self.run_svn_command([ "svn", "log", self.svnDir]);
		# # procText = procText.strip( ).split( '\n' )[0].strip( );
		# newWindow = sublime.active_window().new_file();
		# newWindow.insert(edit, 0, procText);

		# print(procText)
		print('ending test command')

	def do_ok(self):
		print('test')


class testEventListener(sublime_plugin.EventListener, svnController):
	def on_new(self, view):
		print(view.window().id())
