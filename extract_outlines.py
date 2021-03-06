# coding: utf-8
from __future__ import division


from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.layout import LAParams, LTTextBoxHorizontal
from pdfminer.converter import PDFPageAggregator


import sys, re, json, glob



class LCC(object):

	def  __init__(self, filename = ''):
			
		# Open a PDF file.
		fp = open(filename, 'rb')
		# Create a PDF parser object associated with the file object.
		parser = PDFParser(fp)
		laparams = LAParams()


		# Create a PDF document object that stores the document structure.
		# Supply the password for initialization.
		document = PDFDocument(parser, '')
		# Check if the document allows text extraction. If not, abort.
		if not document.is_extractable:
			raise PDFTextExtractionNotAllowed
		# Create a PDF resource manager object that stores shared resources.
		rsrcmgr = PDFResourceManager()
		# Create a PDF device object.
		device = PDFPageAggregator(rsrcmgr, laparams=laparams)
		# Create a PDF interpreter object.
		interpreter = PDFPageInterpreter(rsrcmgr, device)

		self.all_classifications = {}
		self.problematicClassmarks = []

		# Process each page contained in the document.
		for page in PDFPage.create_pages(document):
			interpreter.process_page(page)
			layout = device.get_result()
			self.process_page(layout)

			self.process_classifications()




		self.remove_debug()

		self.seperate()
		
		self.results = self.all_classifications
		self.problems = self.problematicClassmarks

	def seperate(self):

		results = {}



		for c in self.all_classifications:

			if self.all_classifications[c]['prefix'] not in results:
				results[self.all_classifications[c]['prefix']] = []

			self.all_classifications[c]['id'] = c
			results[self.all_classifications[c]['prefix']].append(self.all_classifications[c])

		self.all_classifications = results


	def remove_debug(self):

		for c in self.all_classifications:

			del self.all_classifications[c]['parentsStart']
			del self.all_classifications[c]['parentsIndex']




	def process_classifications(self):


		for c in self.all_classifications:

			#print self.all_classifications[c]

			#look for all parents
			for c_search in self.all_classifications:

				#being very verbose here
				if c != c_search:

					if self.all_classifications[c]['prefix'] == self.all_classifications[c_search]['prefix']:

						if self.all_classifications[c]['start'] >= self.all_classifications[c_search]['start']:

							if self.all_classifications[c]['stop'] <= self.all_classifications[c_search]['stop']:

								#print "IS PARENT:"
								#print self.all_classifications[c_search]
								if self.all_classifications[c_search]['start'] not in self.all_classifications[c]['parentsStart']:
									
									self.all_classifications[c]['parentsStart'].append(self.all_classifications[c_search]['start'])

									self.all_classifications[c]['parentsIndex'][self.all_classifications[c_search]['start']] = c_search

									self.all_classifications[c]['parentsStart'].sort()

									self.all_classifications[c]['parents'] = []

									for n in self.all_classifications[c]['parentsStart']:

										self.all_classifications[c]['parents'].append(self.all_classifications[c]['parentsIndex'][n])










	def process_page(self,layout):


		codes = []
		descriptions = []

		basic_code_pattern = re.compile("^[A-Z]+[0-9]")
		subdivided_pattern = re.compile("^[A-Z]+[0-9]+\.[A-Z]+")
		subdivided_pattern2 = re.compile("^[A-Z]+[0-9]+\-[0-9]\.[A-Z]+")


		hyphen_aplha_pattern = re.compile("^([A-Z]+[0-9]+\.[0-9]+)\.[A-Z]+\-[A-Z]+")

		heading_pattern = re.compile("^[A-Z]+\-[A-Z]+")
		heading_pattern2 = re.compile("^[A-Z]+[0-9]+\-[A-Z]+[0-9]+")

		only_three_prefix = re.compile("^[A-Z]{3}")
		only_two_prefix = re.compile("^[A-Z]{2}")


		for lt_obj in layout:

			

			if isinstance(lt_obj, LTTextBoxHorizontal):


				for line in lt_obj:

					#on the left hand side of the page
					if line.bbox[0] < 200:
						codes.append(line)
					else:
						descriptions.append(line)

				#print lt_obj.bbox[0]
				#print lt_obj.get_text()

				#print "-----"


		for code in codes:

			text = code.get_text().strip().replace('(','').replace(')','')

			text = text.replace('PN1992.93-19 92.95','PN1992.93-1992.95')

			if text == 'D545.9':
				text = 'DT545.9'
			if text == 'D274.5-6':
				text = 'D274.5-274.6'
			if text == 'QC 1-75':
				text = 'QC1-75'







			if ((heading_pattern.match(text) or heading_pattern2.match(text))  and text != 'KFA-KFW' and text != 'KEA-KEN'):

				self.problematicClassmarks.append("Skipping " + text)
				continue

				#TODO fix the KL-KWX1 from KL-KWX schedule here



			if len(text) > 0:


				this_code = text
				this_desc = None

				#now look through all the descriptions

				for description in descriptions:
					if  code.bbox[1] == description.bbox[1]:
						if description.get_text().strip() != '':
							this_desc = description.get_text().strip()

				#did we get it?
				if this_desc == None:
					this_desc = "ERROR, could not find"



				if (basic_code_pattern.match(text)):

					#print this_code, this_desc

					#TODO, do this better
					if (subdivided_pattern.match(this_code)):

						#DA990.U45-U46
						this_code = this_code.split('.')[0]
						#DA990
						self.problematicClassmarks.append(text + ' -> ' + this_code)
					elif (subdivided_pattern2.match(this_code)):

						#M1-1.A15
						this_code = this_code.split('-')[0]
						#M1
						self.problematicClassmarks.append(text + ' -> ' + this_code)
						


					elif (hyphen_aplha_pattern.match(this_code)):

						m = re.search(hyphen_aplha_pattern, this_code)

						#KBM524.4.A-Z				
						this_code = m.group(1)
						#KBM524.4
						self.problematicClassmarks.append(text + ' -> ' + this_code)


					



					#parse the code out
					m = re.search('(^[A-Z]+)', this_code)

					prefix = m.group(0)

					numbers = this_code.replace(prefix,'').replace('(','').replace(')','')

					number_one = None
					number_two = None

					#split the numbers if it is there
					if numbers.find('-') > -1:						
						number_one = float(numbers.split('-')[0])
						number_two = float(numbers.split('-')[1])
					else:
						number_one = float(numbers)
						number_two = number_one


					#print prefix, numbers, number_one, number_two

					self.all_classifications[this_code] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : prefix, "start" : number_one, "stop" : number_two, "subject" : this_desc }

				else:

					#there are some edge cases here

					if only_three_prefix.match(text) and len(text) == 3:

						if text[0] == 'K':

							if (this_desc.find('law of') == -1 and this_desc.find('Laws of') == -1):
								this_desc = "Law of " + this_desc


						self.all_classifications[this_code] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : text, "start" : 0, "stop" : 10000, "subject" : this_desc }



					elif only_two_prefix.match(text) and len(text) == 2:


						self.all_classifications[this_code] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : text, "start" : 0, "stop" : 10000, "subject" : this_desc }

					elif text == 'KES, KEY':

						self.all_classifications['KES'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : "KES", "start" : 0, "stop" : 10000, "subject" : "Law of Saskatchewan" }
						self.all_classifications['KEY'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : "KEY", "start" : 0, "stop" : 10000, "subject" : "Law of Yukon" }


					
					elif text == 'KEA-KEN':


						self.all_classifications['KEA'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEA', "start" : 0, "stop" : 10000, "subject" : 'Law of Alberta' }
						self.all_classifications['KEB'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEB', "start" : 0, "stop" : 10000, "subject" : 'Law of British Columbia' }
						self.all_classifications['KEM'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEM', "start" : 0, "stop" : 10000, "subject" : 'Law of Manitoba' }
						self.all_classifications['KEN1-599'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEN', "start" : 1, "stop" : 599, "subject" : 'Law of New Brunswick' }
						self.all_classifications['KEN1201-1799'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEN', "start" : 1201, "stop" : 1799, "subject" : 'Law of Newfoundland and Labrador' }
						self.all_classifications['KEN5401-5999'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEN', "start" : 5401, "stop" : 5999, "subject" : 'Law of Northwest Territories' }
						self.all_classifications['KEN7401-7999'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEN', "start" : 7401, "stop" : 7999, "subject" : 'Law of Nova Scotia' }
						self.all_classifications['KEN8001-8599'] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : 'KEN', "start" : 8001, "stop" : 8599, "subject" : 'Law of Nunavut' }

							

					elif text == 'KFA-KFW':


						#uggh....
						states = {
							"KFA" : "Law of Alabama",
							"KFC" : "Law of California",
							"KFD" : "Law of Delaware",
							"KFF" : "Law of Florida",
							"KFG" : "Law of Georgia",
							"KFH" : "Law of Hawaii",
							"KFI" : "Law of Idaho",
							"KFK" : "Law of Kansas",
							"KFL" : "Law of Louisiana",
							"KFM" : "Law of Maine",
							"KFN" : "Law of Nebraska",
							"KFO" : "Law of Ohio",
							"KFP" : "Law of Pennsylvania",
							"KFR" : "Law of Rhode Island",
							"KFS" : "Law of South Carolina",
							"KFT" : "Law of Tennessee",
							"KFU" : "Law of Utah",
							"KFV" : "Law of Vermont",
							"KFW" : "Law of Washington"
						}

						for s in states:

							self.all_classifications[s] = { "parents" : [], "parentsStart" : [], "parentsIndex" : {}, "prefix" : s, "start" : 0, "stop" : 10000, "subject" : states[s] }



					
					else:


						self.problematicClassmarks.append(text + ' -> ' + 'Does not look like a LCC?')




if __name__ == "__main__":
	

	
	try:
		mode = sys.argv[2]
	except:
		mode = "single"
	
	if (sys.argv[1] == 'all'):
		mode = 'all'

	if mode == "single":
		aLCC = LCC(sys.argv[1])
		print json.dumps(aLCC.results,sort_keys=True)

	if mode == "all":

		all_results = {}
		all_problems = []

		for x in glob.glob("source/*.pdf"):

			print x

			aLCC = LCC(x)


			for prefix in aLCC.results:


				if prefix not in all_results:
					all_results[prefix] = aLCC.results[prefix]
				else:
					print x,"wants to overwrite",prefix,"Not doing it."


			all_problems = all_problems + aLCC.problems




		with open('results.json', 'w') as outfile:
			json.dump(all_results,outfile,sort_keys=True)

		with open('problems.json', 'w') as outfile:
			json.dump(all_problems,outfile,sort_keys=True)


	