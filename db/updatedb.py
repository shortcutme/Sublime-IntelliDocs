from __future__ import print_function
import os, re, json

# Update DB from local devdocs.io dump: https://github.com/Thibaut/devdocs
# (Tested on Python 2.7 win7)

path_devdocs = "./devdocs"
path_db = "."
docs = ["PHP", "Python"]
patterns = {
	"PHP": {
		#"skip"	: '.*::',
		"args"	: ".*?methodsynopsis.*?>(.*?)</div>",
		"descr"	: ".*rdfs-comment.*?>(.*?)</p>",
		"params": "<dt>(.*?)<dd>(.*?)</dd>"
	},
	"Python": {
		"doc"	: '.*(<dt.*?id=.%(name)s[^a-zA-Z]*?>.*?</dd>)',
		"alias"	: '^(str|dict|int|float|list|bytes|bytearray|array.array|array)\.',
		"args"	: "<dt.*?>(.*?)</dt>",
		"descr"	: ".*?<p>(.*?)</p>",
	}
}

def stripTags(s):
	s = re.sub("<[a-zA-Z/]+.*?>", "", s)
	s = s.replace("&amp;", "&").strip()
	s = s.replace("&gt;", ">").strip()
	s = s.replace("&lt;", "<").strip()
	s = s.replace("\n", "").strip()
	return s

class Parser:
	def __init__(self, name, lang):
		self.name = name
		self.lang = lang
		self.patterns = patterns[name]
		path = path_devdocs+"/public/docs/"+lang+"/"
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
			name, descr = match
			descr = re.sub("^(.{30,200}?)(\. |$).*", "\\1\\2", stripTags(descr))
			params.append({"name": stripTags(name), "descr": descr})
		return params


	def updateDoc(self, path):
		index = json.load(open(path+"/index.json"))
		db = {}
		no_match = []
		for entry in index["entries"]:
			# Open doc file
			entry["name"] = entry["name"].replace(" (class)", "").strip("()")
			if "skip" in self.patterns and re.match(self.patterns["skip"], entry["name"]): 
				print("S", end="")
				continue

			path_doc = path+re.sub("#.*$", "", entry["path"])+".html"
			try:
				doc = open(path_doc).read()
			except Exception, err:
				print(err)

			if "doc" in self.patterns: # Prefilter doc
				match = re.match(self.patterns["doc"] % entry, doc, re.DOTALL)
				if match:
					doc = match.group(1)
				else:
					doc = ""

			# Match parameters
			match = re.match(self.patterns["args"], doc, re.DOTALL)

			# Add to db
			if match:
				db[entry["name"]] = {
					"name": entry["name"],
					"path": self.lang+"/"+entry["path"],
					"type": entry["type"],
					"overview": stripTags(match.group(1)),
					"description": self.getDescr(doc),
					"parameters": self.getParams(doc)
				}
				print(".", end="")

				# Create alias like str.replace -> replace
				if "alias" in self.patterns:
					name_alias = re.sub(self.patterns["alias"], "", entry["name"])
					if name_alias != entry["name"]:
						db[name_alias] = db[entry["name"]]
						print("A", end="")
			else:
				print("-", end="")
				no_match.append(entry["name"])
		open(path_db+"/"+self.name+".json", "w").write(json.dumps(db, sort_keys=True, indent=4))
		print("No match:", no_match)
		print("Done!")


for name in docs:
	print(" * Updating", name)
	lang = name.lower()
	Parser(name, lang)
