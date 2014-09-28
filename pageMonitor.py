import urllib, hashlib, smtplib, os, sys, time, cPickle
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from threading import Thread
from HTMLParser import HTMLParser

#classes
class customURLOpener(urllib.FancyURLopener):
	version = 'Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201'

class Page:
	def __init__(self, fields):
		self.pageID = fields[0] 
		self._pageName = fields[1]
		self._pagePath = fields[2]
		self._frequency = float(fields[3])
		self._pageElement = fields[4]
		if len(fields) > 5:
			self._pageHash = fields[5]
		else:
			self._pageHash = '0'
		self._time = time.clock()
		hashobj = hashlib.md5()
		hashobj.update(fields[0] + fields[1] + fields[2] + fields[3] + fields[4])
		self._entryHash = hashobj.hexdigest()

	def getUpdatedHash(self):
		
		urllib._urlopener = customURLOpener()
		try:
			page = urllib.urlopen(self._pagePath)
		except IOError:
			return self._pageHash
		p = parser(self._pageElement)
		contents = page.read()
		p.feed(contents)
		if p._elementHash == '0':
			return self._pageHash	
		else:
			return p._elementHash
		#hashobj = hashlib.md5()
		#for line in page.readlines():
			#hashobj.update(line)
		#return hashobj.hexdigest()

	def isExpired(self):
		if self._time + self._frequency >= time.clock():
			return 1
		else:
		   	self._time = time.clock()
			return 0

	def sendUpdate(self):
		fromAddr = "pageMonitor@notifications.com"
		# this is the address where the notifcations are to be sent
		toAddr = "emailAddress@domain.com"

		msg = MIMEMultipart()
		msg['From'] = fromAddr
		msg['To'] = fromAddr
		msg['Subject'] = "Page Update -" + self._pageName
		body = """\
		<html>
			<head></head>
				<body>
					<p>Page Monitor has detected a change in <br>
					<a href=""" + self._pagePath + """>""" + self._pageName + """</a> <br>
					</p>
				</body>
			</html>
		"""
		msg.attach(MIMEText(body,'html'))
		# this uses postfix to send emails. 
		server = smtplib.SMTP("localhost")

		text = msg.as_string()
		server.sendmail(fromAddr,toAddr, text)
		#print self._pageName + " - update sent"
		server.close()

	def setNewHash(self,newHash):
		self.hashVal = newHash
		f = open("./pages","r")
		#for line in f.readlines(): #need to iterate through lines but leave the cursor at the beginning of each line so writing
		lines = f.readlines()
		f.close()
		f = open("./pages","w")
		for line in lines:
			feilds = line.split(',')
			p = Page(feilds)
			if p.pageID == self.pageID:
				f.write(self.pageID + "," + self._pageName + "," + self._pagePath + "," + `self._frequency` + "," + self._pageElement + "," + newHash + ',\n')
				self._pageHash = newHash
			else:
				line = f.write(line)
		f.close()

	def printStatus(self):
		print self._pageName + " last checked: " + `self._time` 
				

class parser(HTMLParser):

	def __init__(self, targetElement):
		self._targetElement = targetElement
		self._elementFound = None
		self._elementHash = '0'
		self._tagCount = 0
		self._content = ''
		HTMLParser.__init__(self)

	def handle_starttag(self, tag, attrs):
		if self.getElementID(attrs) == self._targetElement:
			self._elementFound = tag
			self._tagCount = 1
		elif self._elementFound == tag:
			self._tagCount += 1
			
	def handle_endtag(self, tag):
		if self._elementFound == tag:
			self._tagCount -= 1
			if self._tagCount == 0:
				hashobj = hashlib.md5()
				hashobj.update(self._content)
				self._elementHash = hashobj.hexdigest()
				self._elementFound = None

	def handle_data(self, data):
		if self._elementFound != None:
			self._content += data 

	def getElementID(self, attrs):
		for attr in attrs:
			if attr[0] == 'id':
				return attr[1]
		return None


# global Variables
command = sys.argv[1]
msgPipe = "pipe"
service_is_running = 0
monitoredPages = []

# global functions
def handleMsgs():
	global service_is_running
	while service_is_running:
		rp = open(msgPipe,'r')
		msg = rp.read()
		if msg == 'status':
			print "message Recieved"
			for page in monitoredPages:
				page.printStatus()
		elif msg == 'stop':
			print "stopping service"
			service_is_running = 0
		rp.close()



def addNewPages():
	f = open("./pages","r")
	lines = f.readlines()
	#print lines
	for line in lines:
		feilds = line.split(',')
		#print len(feilds)
		p = Page(feilds)
		newPage = 1
		if len(monitoredPages) > 0:
			for page in monitoredPages:
				if page.pageID == p.pageID:
					newPage = 0
			if newPage:
				print p._pageName + ' added to list'
				monitoredPages.append(p)
		else:
			print p._pageName + ' added to list'
			monitoredPages.append(p)
	f.close()
			

def checkPages():
	for page in monitoredPages:
		#print page._pageName
		if page.isExpired():
			#print 'checking ' + page._pageName
			newHash = page.getUpdatedHash()
			#print 'old hash = ' + page._pageHash + '|\r'
			#print 'new hash = ' + newHash + '|\r'
			if page._pageHash != newHash: 
				page.sendUpdate()
				page.setNewHash(newHash)


# Main Routine
if command == 'start':
	pid = os.fork()
	if pid:
		sys.exit()
	else:
		service_is_running = 1
		t = Thread(None, handleMsgs)
		t.start()
		addNewPages()
		#print monitoredPages
		try:
		    os.mkfifo(msgPipe)
		except OSError:
			pass
		while service_is_running:
			checkPages()
			time.sleep(10)
			addNewPages()
			time.sleep(10)
		print "service ended"
elif command == 'status' :
	rp = open(msgPipe,'w')
	rp.write('status')
	rp.close()
elif command == 'stop' :
	rp = open(msgPipe,'w')
	rp.write('stop')
	rp.close()
