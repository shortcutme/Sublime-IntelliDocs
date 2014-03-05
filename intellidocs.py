
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
		# Find function name
		word = self.view.word(self.view.sel()[0])
		word.a = word.a - 100 # Look back 100 character
		word.b = word.b + 1 # Ahead word +1 char
		buff = self.view.substr(word).strip()

		buff = " "+re.sub(".*\n", "", buff) # Keep only last line
		match = re.match(".*[^A-Za-z0-9_\.\$]([A-Za-z0-9_\.\$]+)[ ]{0,1}\(.*?", buff)
		if not match: # No match
			self.view.erase_status('hint')
			self.last_function_name = None
			return
		function_name = match.group(1).strip(".")
		#if function_name == self.last_function_name: return # Skip if not cahanged
		self.last_function_name = function_name

		# Find db for lang
		lang = re.match(".*/(.*?).tmLanguage", self.view.settings().get("syntax")).group(1)
		if lang not in self.cache: #DEBUG disable cache: or 1 == 1
			path_db = os.path.dirname(os.path.abspath(__file__))+"/db/%s.json" % lang
			print("Loaded intelliDocs db:", path_db)
			if os.path.exists(path_db):
				self.cache[lang] = json.load(open(path_db))
			else:
				self.cache[lang] = {}

		completions = self.cache[lang]

		# Find in completions
		if completions:
			found = completions.get(function_name)
			if not found and "." in function_name: #If no match try to get without package
				found = completions.get(re.sub(".*\.", "", function_name))
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
