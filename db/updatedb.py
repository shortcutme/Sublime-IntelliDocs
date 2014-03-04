from __future__ import print_function
import os, re, json

# Update DB from local devdocs.io dump: https://github.com/Thibaut/devdocs
# (Tested on Python 2.7 win7)

path_devdocs = "../var/devdocs"
path_db = "."
docs = {
	"php": "PHP",
	"python": "Python",
	"javascript": "Javascript",
	"dom": "Javascript",
	"jquery": "Javascript"
}

patterns = {
	"PHP": {
		#"skip"	: '.*::',
		"syntax": ".*?methodsynopsis.*?>(.*?)</div>",
		"descr"	: ".*rdfs-comment.*?>(.*?)</p>",
		"params": "<dt>(.*?)<dd>(.*?)</dd>"
	},
	"Python": {
		"doc"	: '.*(<dt.*?id=.%(name)s[^a-zA-Z]*?>.*?</dd>)',
		"alias"	: '^(str|dict|int|float|list|bytes|bytearray|array.array|array|re.match)\.',
		"syntax": "<dt.*?>(.*?)</dt>",
		"descr"	: ".*?<p>(.*?)</p>",
	},
	"Javascript": {
		"alias"	: '^(Array|String|Date|Function|Object|RegExp|Number|window)\.',
		"syntax": ".*?(?:[sS]yntax|section).*?<(?:code|pre|span).*?>(.*?\).*?)</(?:p|pre|code|h2)>",
		"descr"	: ".*?h1.*?<p>(.*?)</p>",
		"params": "(?:<dt>(.*?)<dd>(.*?)</dd>|<li>.{5,30}<strong>(.*?)</strong>(.*?)</li>)"
	}
}

def stripTags(s):
	s = re.sub("<[a-zA-Z/]+.*?>", "", s)
	s = s.replace("&amp;", "&")
	s = s.replace("&gt;", ">")
	s = s.replace("&lt;", "<")
	s = s.replace("\n", "")
	s = s.strip()
	return s

class Parser:
	def __init__(self, directory, name):
		self.name = name
		self.directory = directory
		self.patterns = patterns[name]
		path = path_devdocs+"/public/docs/"+directory+"/"
		self.updateDoc(path)


	def getPattern(self, pattern_name):
		self.patterns[pattern_name].format(name = entry["name"])


	def getDescr(self, doc):
		match_descr = re.match(self.patterns["descr"], doc, re.DOTALL)
		if match_descr:
			descr = match_descr.group(1)
		else:
			descr = ""
		return stripTags(descr)


	def getParams(self, doc):
		params = []
		if "params" not in self.patterns: return params
		for match in re.findall(self.patterns["params"], doc, re.DOTALL):
			name, descr = [group for group in match if group]
			descr = re.sub("^(.{30,200}?)(\. |$).*", "\\1\\2", stripTags(descr))
			params.append({"name": stripTags(name), "descr": descr})
		return params


	def updateDoc(self, path):
		index = json.load(open(path+"/index.json"))
		db = json.load(open(path_db+"/"+self.name+".json"))
		no_match = []
		for entry in index["entries"]:
			# Open doc file
			entry["name"] = entry["name"].replace(" (class)", "").strip("().")
			if "skip" in self.patterns and re.match(self.patterns["skip"], entry["name"]): 
				print("S", end="")
				continue

			path_doc = path+re.sub("#.*$", "", entry["path"])+".html"
			try:
				doc = open(path_doc).read()
			except Exception, err:
				print(err)

			#if entry["name"] != "removeClass": continue # DEBUG

			if "doc" in self.patterns: # Prefilter doc
				match = re.match(self.patterns["doc"] % entry, doc, re.DOTALL)
				if match:
					doc = match.group(1)
				else:
					doc = ""

			# Match sytax
			match = re.match(self.patterns["syntax"], doc, re.DOTALL)

			# Add to db
			if match:
				syntax = stripTags(match.group(1))
				syntax = syntax.replace(")Returns:", ") Returns:") # jQuery doc returns fix

				#multiple syntax possible
				if ");" in syntax:
					parts = syntax.split(");")
					syntax = ");\n or ".join( [part for part in parts if part.strip()] )+");"

				db[entry["name"]] = {
					"name"	: entry["name"],
					"path"	: self.directory+"/"+entry["path"],
					"type"	: entry["type"],
					"syntax": syntax,
					"descr"	: self.getDescr(doc),
					"params": self.getParams(doc)
				}
				print(".", end="")

				# Create alias like str.replace -> replace
				if "alias" in self.patterns:
					name_alias = re.sub(self.patterns["alias"], "", entry["name"])
					if name_alias != entry["name"]:
						db[name_alias] = db[entry["name"]]
						print("A", end="")

				# jQuery.* -> $.* alias
				if entry["name"].startswith("jQuery"):
					name_alias = entry["name"].replace("jQuery.", "$.")
					db[name_alias] = db[entry["name"]]

			else:
				print("-", end="")
				no_match.append(entry["name"])
		open(path_db+"/"+self.name+".json", "w").write(json.dumps(db, sort_keys=True, indent=4))
		print("No match:", no_match)
		print("Done!")

# Create empty files
for directory, name in docs.items():
	open(path_db+"/"+name+".json", "w").write("{}")


# Fill db
for directory, name in docs.items():
	print(" * Updating", directory, "->", name)
	Parser(directory, name)
