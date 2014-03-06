
import sublime_plugin, sublime, json
import re, threading, time, os, webbrowser

class IntelliDocsCommand(sublime_plugin.TextCommand):
	
	last_function_name = None
	last_found = False
	cache = {}
	menu_links = {}
	def __init__(self, view):
		self.view = view
		self.settings = sublime.load_settings("IntelliDocs.sublime-settings")

	def run(self, edit):
		# Find db for lang
		lang = self.getLang()
		if lang not in self.cache: #DEBUG disable cache: or 1 == 1
			path_db = os.path.dirname(os.path.abspath(__file__))+"/db/%s.json" % lang
			self.debug("Loaded intelliDocs db:", path_db)
			if os.path.exists(path_db):
				self.cache[lang] = json.load(open(path_db))
			else:
				self.cache[lang] = {}

		completions = self.cache[lang]

		# Find in completions
		if completions:
			function_names = self.getFunctionNames(completions)
			found = False
			for function_name in function_names:
				completion = completions.get(function_name)
				if completion:
					found = completion
					break

			if found:
				self.view.set_status('hint', found["syntax"]+" | ")
				menus = []
				# Syntax
				menus.append(found["syntax"])

				# Description
				for descr in re.sub("(.{80,100}[\.]) ", "\\1||", found["descr"]).split("||"): #Spit long description lines
					menus.append(" "+descr)

				#Parameters
				if found["params"]:
					menus.append("Parameters:")
				for parameter in found["params"]:
					menus.append(" - "+parameter["name"]+": "+parameter["descr"])
					"""first = True
					for part in re.sub("(.{50,150}?)\. ", "\\1.|", parameter["descr"]).split("|"):
						if first:
							menus.append(parameter["name"]+": "+part.strip())
						else:
							menus.append("- "+part)
						first = False"""
				self.last_found = found

				menu = self.appendLinks(menus, found)
					
				self.view.show_popup_menu(menus, self.action)
			else:
				self.view.erase_status('hint')

	def getLang(self):
		scope = self.view.scope_name(self.view.sel()[0].b) #try to match against the current scope
		for match, lang in self.settings.get("docs").items():
			if re.match(".*"+match, scope): return lang
		self.debug(scope)
		return re.match(".*/(.*?).tmLanguage", self.view.settings().get("syntax")).group(1) #no match in predefined docs, return from syntax filename

	def getFunctionNames(self, completions):
		# Find function name
		word = self.view.word(self.view.sel()[0])
		word.a = word.a - 100 # Look back 100 character
		word.b = word.b + 1 # Ahead word +1 char
		buff = self.view.substr(word).strip()

		buff = " "+re.sub(".*\n", "", buff) # Keep only last line

		# find function names ending with (
		matches = re.findall("([A-Za-z0-9_\]\.\$\)]+\.[A-Za-z0-9_\.\$]+|[A-Za-z0-9_\.\$]+[ ]*\()", buff)
		matches.reverse()
		function_names = []
		for function_name in matches:
			function_name = function_name.strip(".()[] ")
			if len(function_name) < 2: continue
			function_names.append(function_name)
			if "." in function_name:
				function_names.append(re.sub(".*\.(.*?)$", "\\1", function_name))
		function_names.append(self.view.substr(self.view.word(self.view.sel()[0]))) #append current word
		self.debug(function_names)
		return function_names


	def appendLinks(self, menus, found):
		self.menu_links = {}
		for pattern, link in sorted(self.settings.get("help_links").items()):
			if re.match(pattern, found["path"]):
				host = re.match(".*?//(.*?)/", link).group(1)
				self.menu_links[len(menus)] = link % found
				menus.append(" > Goto: %s" % host)
		return menus

	def action(self, item):
		if item in self.menu_links:
			webbrowser.open_new_tab(self.menu_links[item])

	def debug(self, *text):
		if self.settings.get("debug"):
			print(*text)
