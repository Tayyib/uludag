CSLValue = None
CSLAPI_NAME = "string"
debug = None

moddir = dir()

def getFuncTable():
	vtbl = {}
	cls = API()
	for i in dir(cls):
		if i[:4] == "csl_":
			vtbl[i[4:]] = getattr(cls, i)
	s = "RX: 128 TX: 1500 MTU 250"
	f = "TX:"
	x = s.find(f)
	rv = ""
	if x != -1:
		x = x + len(f) # skip fieldid
		for i in range(x, len(s)):
			x = i
			if s[i] != " ":
				break
		
		for i in range(x, len(s)):					
			if s[i] in "\n\t ":					
				break
			rv += s[i]
	print "TEST RV:", rv
	return vtbl
	
def safeget(prms, prm, default):
	if prms.has_key(prm):
		return prms[prm].toString()
	return default

class API:
	def csl_getfieldval(self, prms):
		""" getfieldval(string=str, field='');
	getfieldval(string="RX: 128 TX: 1500 MTU 250", field="RX:"); #return 128 """
		
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string") and prms.has_key("field"):
			s = prms["string"].toString()
			f = prms["field"].toString()
			x = s.find(f)
			#print "Get Field:", s, "\n", f, x, 
			rv = ""
			if x != -1:
				x = x + len(f) # skip fieldid
				for i in range(x, len(s)):					
					if s[i] != " ":
						x = i
						break				
				#print "x:", x, "s[x]:", s[x:x+2],
				for i in range(x, len(s)):					
					if s[i] in "\n\t ":					
						break
					rv += s[i]
			#print "RV: '%s'" % rv
			return CSLValue("string", rv)
			
	def csl_arraygrep(self, prms):
		"array_grep(array=arr, pattern='');"
		if prms.has_key("$__obj"):
			prms["array"] = prms["$__obj"]
		if prms.has_key("array") and prms.has_key("pattern"):
			arr = prms["array"].value
			pattern = safeget(prms, "pattern", "")
			ret = {}
			if arr.type == "array":
				for i in arr.keys():
					s = arr[i].toString()
					if s.find(pattern) != -1:
						ret[i] = arr[i]					
			else:
				if arr.toString.find(pattern) != -1:
					ret["%06d" % 0] = arr
			return CSLValue("array", ret)
		return CSLValue("NULL", "")
	def arraytostring(self, arr):
		ret = ""
		arrval = arr.value
		for i in arrval.keys():			
			if arrval[i].type == "array":
				tmp = self.arraytostring(arrval[i].value)
			else:
				tmp = arrval[i].toString()
			ret += tmp
		return CSLValue("string", ret)
	def csl_array2buffer(self, prms):
		if prms.has_key("$__obj"):
			prms["array"] = prms["$__obj"]
		if prms.has_key("array"):
			arr = prms["array"]
			return self.arraytostring(arr)
		return CSLValue("NULL", "")
		
	def csl_replacetokens(self, prms):
		tokenid = "$"
		valid_chars = "0123456789_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
		if prms.has_key("$__obj"):
			prms["buffer"] = prms["$__obj"]
		if prms.has_key("buffer") and prms.has_key("fields"):
			tokenid = safeget(prms, "tokenid", tokenid)
			fields = prms["fields"]
			#print "Fields:", fields, fields.type, fields.value, prms
			buf = prms["buffer"].toString()
			pos = 0
			x = buf.find(tokenid, pos)
			while x != -1:
				buf_last = len(buf) - 1
				if x < buf_last:
					if buf[x+1] == tokenid:
						buf = buf[:x] + buf[x+1:]
						pos = x + 1
					else:
						pos = x + 1
						lpart = buf[:x]
						start = buf[x+1]
						stop = None
						if start == "{":
							sp = x + 2
							x += 1
							stop = "}"
						token = ""
						x += 1
						for i in range(x, buf_last):
							if stop:								
								if buf[i] == stop:
									token = buf[sp:i]									
									pos = i + 1									
									break
							else:								
								if not (buf[i] in valid_chars):
									token = buf[x:i]
									pos = i 
									break
						if token != "":							
							fld = safeget(fields.value, token, "")							
							#print "Replace \"%s\"Token: +%s+ -> +%s+ \"%s\" + \"%s\" %d "% (buf, token, fld, lpart, buf[pos:], pos)
							buf = lpart + fld + buf[pos:]
							pos = len(lpart) + len(fld) + 1
							token = ""
				x = buf.find(tokenid, pos)
				if x == len(buf) - 1:
					x = -1
				#print "new buf:", buf, x
			return CSLValue("string", buf)
		return CSLValue("NULL", "")
		
	def	csl_strupper(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			a = prms["string"].toString()
			return CSLValue("string", a.upper())
			
	def csl_strip(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			a = prms["string"].toString()
			return CSLValue("string", a.strip())
		debug(DEBUG_FATAL, "Invalid Strip:", prms)
		
	def csl_strlower(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			a = prms["string"].toString()
			return CSLValue("string", a.lower())
			
	def csl_startswith(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("prefix") and prms.has_key("string"):
			a = prms["string"].toString()
			return CSLValue("numeric", a.startswith(prms['prefix'].toString()))
	def csl_splitws(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			a = prms["string"].toString()
			fn = ""
			x = 0
			ret = {}
			for i in a:
				if i == " " or i == "\t":
					if fn != "":
						ret[x] = CSLValue("string", fn)								
						x += 1
					fn = ""
				else:
					fn += i
			#print "SPLITWS Return:", ret, a, arr,prms["separator"].toString()
			return CSLValue("array", ret)
		print "Incorrect split:", prms
				
	def csl_split(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("separator") and prms.has_key("string"):
			a = prms["string"].toString()
			s = prms["separator"].toString()
			arr = a.split(s)
			ret = {}
			x = 0
			for i in arr:
				if i != "":
					ret[x] = CSLValue("string", i)
					#print "split:", x, "=", i,
					x += 1
			#print "SPLIT Return:", ret, a, arr,prms["separator"].toString()
			return CSLValue("array", ret)
		print "Incorrect split:", prms
		
	def csl_strlen(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			return CSLValue("numeric", len(prms['string'].toString()))
	
	def csl_strstr(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string") and prms.has_key("pattern"):
			
			st = prms['string'].toString()
			#print "STRSTR:", prms, st, prms['pattern'].toString(),
			if st.find(prms['pattern'].toString()) != -1:
				#print "=", 1
				return CSLValue("numeric", 1)
			else:
				#print "=", 0
				return CSLValue("numeric", 0)
		return CSLValue("numeric", 0)
	def csl_gettabbedsections(self, prms):
		if prms.has_key("$__obj"):
			prms["array"] = prms["$__obj"]
		if prms.has_key("array"):
			arr = prms['array'].value
			ret = {}
			if arr.type == "array":
				keys = arr.keys()
				keys.sort()
				x = 0
				data = {}
				lin = 0
				for i in keys:
					if arr[i][0] in "\t ":						
						data["%04d" % lin] = arr[i]
						lin = lin + 1
					else:
						if len(data):
							ret["%04d" % x] = data
							lin = 0
						data = {}
						data["%04d" % x] = arr[i]						
						x = x + 1				
			return CSLValue("array", ret)
	def csl_substr_left(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			st = prms['string'].toString()						
			if prms.has_key("size"):
				maxs = int(prms['size'].toNumeric());				
			else:
				maxs = len(st)
			if maxs > len(st):
				maxs = len(st)
			
			a = st[:maxs]
			return CSLValue("string", a)
	
	def csl_substr_mid(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			if prms.has_key("first"):
				st = prms['string'].toString()
			if prms.has_key("size"):
				maxs = size;
			else:
				maxs = len(st)
			pos = st.find(prms['first'].toString())
			if pos == -1:
				return CSLValue("string", "")
			a = st[pos+1:]
			a = a[:maxs]
			return CSLValue("string", a)
	
	def csl_getnumleft(self, prms):
		" return number of '12alpha' form.."
		ret = ""
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):
			s = prms["string"].toString()
			skip = 0
			#print "GETNumLeft: '%s'" % (s)
			for i in s:
				if i in "0123456789.":
					ret += i
					skip = 1
				elif i == " ":
					if skip:
						if len(ret):
							try:
								ret = float(ret)
							except:
								ret = 0
						break							
				else:
					if len(ret):
						try:
							ret = float(ret)
						except:
							ret = 0

					break
		if ret == "": 
			ret = "0"
		#print "getnumleft return:", ret
		if int(ret) == ret:
			ret = int(ret)
		return CSLValue("numeric", ret)
	
	def csl_getnumright(self, prms):
		" return number of 'alpha12' form.."
		ret = ""	
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string"):					
			s = prms["string"].toString()
			#print "GETNumRight: '%s'" % (s)
			skip = 0
			for i in range(len(s) - 1, -1, -1):
				c = s[i]
				if c in "0123456789" or (ret != "" and c == ".") :
					ret = c + ret
					skip = 1
				elif i == " ":
					if skip:
						if len(ret):
							try:
								ret = float(ret)
							except:
								ret = 0
						break							
				else:
					break
		#print "getnumright return:", ret
		if ret == "": 
			ret = "0"
		return CSLValue("numeric", ret)
	
	def csl_casestartswith(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("prefix") and prms.has_key("string"):
			a = prms["string"].toString()
			a = a.lower()
			needle = prms['prefix'].toString()
			needle = needle.lower()
			return CSLValue("string", a.startswith(needle))
			
	def csl_caseendswith(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("trailer") and prms.has_key("string"):
			a = prms["trailer"].toString()
			a = a.lower()
			needle = prms['trailer'].toString()
			needle = needle.lower()
			return CSLValue("string", a.startswith(needle))
	
	def csl_casefind(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("pattern") and prms.has_key("string"):
			a = prms["string"].toString()
			a = a.lower()
			needle = prms['pattern'].toString()
			needle = needle.lower()
			ret = CSLValue("string", a.find(needle))
			if ret == -1:
				return CSLValue("numeric", 0)
			else:
				return CSLValue("numeric", ret + 1)
	
	def csl_caserfind(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("pattern") and prms.has_key("string"):
			a = prms["string"].toString()
			a = a.lower()
			needle = prms['pattern'].toString()
			needle = needle.lower()
			ret = CSLValue("string", a.rfind(needle))
			if ret == -1:
				return CSLValue("numeric", 0)
			else:
				return CSLValue("numeric", ret + 1)
		else:
			return CSLValue("numeric", 0)
	
	def csl_rfind(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string") and prms.has_key("pattern"):
			a = prms["string"].toString()
			needle = prms['pattern'].toString()
			ret = CSLValue("string", a.rfind(needle))
			if ret == -1:
				return CSLValue("numeric", 0)
			else:
				return CSLValue("numeric", ret + 1)
		else:
			return CSLValue("numeric", 0)
	
	def csl_insert(self, prms):
		if prms.has_key("$__obj"):
			prms["string"] = prms["$__obj"]
		if prms.has_key("string") and prms.has_key("part"):
			pos = 0
			rep = 0
			if prms.has_key("position"):
				pos = prms["position"].toNumeric() - 1
	
			if pos < 0:
				pos = 0
	
			if prms.has_key("replace"):
				rep = prms["replace"].toNumeric()
			st = prms["string"]
			ll = st[:pos]
			rl = st[pos + 1:]
	
			if rep:
				rl = rl[rep:]
			return CSLValue("string", ll + prms['part'] + rl)
			
	def csl_hex2dec(self, prms):
		if prms.has_key("$__obj"):
			prms["value"] = prms["$__obj"]
		if prms.has_key("value"):
			x = int(prms["value"].toString(), 16)					
			return CSLValue("numeric", x)
		return CSLValue("NULL", 0)
