import slackbot
import time
import random
import math
import pickle
import json
import re
import subprocess


class MarkovBot(slackbot.Slackbot):
        

	talkBackFreq = 0.01
	isLearning = True
	censorWords = True

	commandSought = ""

	invSize = 6

	ignore = [ 'talkback', 'saveDict', 'intercourse', 'fuck', 'responding probability', 'dictionary saved successfully', 'remember that about', 'malformed' ]

	repeatWords = []

	STOPWORD = 'BOGON'
        
	#		key	       come-befores       come-afters
	dictionary = { STOPWORD : ( [ (STOPWORD, 1) ], [ (STOPWORD, 1) ] ) }

	def __init__(self, token, client, id):

		slackbot.Slackbot.__init__(self, token, client, id)
		
		try:
			self.facts = {}
			self.inventory = []
			self.commands = {}
			self.loadDictionary()
			print ('DICTIONARY LOADED SUCCESSFULLY')
		except IOError:
			print ('DICTIONARY COULD NOT BE LOADED')



	def onMessageReceived(self, target, sender, message):	

		callargs = {'token': self.TOKEN, 'user': sender}
		info = self.CLIENT.api_call('users.info', callargs)
		userinfo = json.loads(info)['user']
		sentByAdmin = json.loads(info)['user']['is_admin']


		# command handling
		#if sentByAdmin and ('!saveDict' in message):


#	#	# all other messages handled here
		if sender != 'USLACKBOT':
			
			message = message.lower()

			if self.commandSought != "":
				self.commands[self.commandSought].append(message)
				print "Saved '" + message + "' under '" + self.commandSought + "'"
				self.commandSought = ""

			response = ''
			#if (target not in self.channelids) or (self.users[self.bot.ID] in text):
			#if (target not in self.channelids) or (message.startswith('manatee')):
			# TODO make it handle private groups properly
			if (message.startswith('manatee')):
				print "That's a PM"
				response = self.onPrivateMessageReceived(target, sender, message)

			else:

				if self.isLearning:

					sentences = message.split('. ')
					for sentence in sentences:
						if sentence.endswith('.'):	# get rid of last .
							sentence = sentence[:-1]
						self.interpretMessage(sentence)
						

						if random.random() < self.talkBackFreq:
								response = self.generateChain(message)

			if response != '' and response is not None:
				response = fixGrammar(response)
				self.sendMessage(target, response)
                
        
	def onPrivateMessageReceived (self, channel, sender, message):

		# PMs don't teach the bot anything, but will always get a response (if the bot can provide one)

		message = message.lower()
		#if re.match(r'^<@.*>[:,]? ', message):
		if re.match(r'manatee([,:])? ', message) or re.match(r'<@.*>:,? ', message):
			message = re.sub(r'.*manatee([,:])? +', '', message)
			message = re.sub(r'<@manatee>([,:])? +', '', message)
			response = self.processCommand(message, sender, channel)
		else:
			response = self.generateChain(message)

		if response != '':
			self.sendMessage(channel, response)

	def processCommand(self, command, sender, channel):

		print "command::" + command
		response = ''
		# get info about user
		callargs = {'token': self.TOKEN, 'user': sender}
		userinfo = json.loads(self.CLIENT.api_call('users.info', callargs))['user']

		if re.match(r'^(take|hold) ', command):
			item = re.sub(r'^(take|hold) +', '', command)
			item = re.sub(r'\bmy\b', "%s's" % userinfo['name'], item)
			item = re.sub(r'\bme\b', "%s" % userinfo['name'], item)
			item = re.sub(r'\byour\b', 'my', item)
			item = re.sub(r'\bthis ([aeiou])', r'an \1', item, 1)
			item = re.sub(r'\bthis\b', 'a', item, 1)
			response = "now holding %s" % item
			self.inventory.append(item)
			if (len(self.inventory) > self.invSize):
				response += ", but had to drop %s" % self.inventory.pop(0)

		elif re.match(r'drop ', command):
			item = re.sub(r'drop +', '', command)
			print "item: ", item
			#item = re.sub(r'\b(that|the) ([aeiou])', r'an \1', item, 1)
			#item = re.sub(r'\b(that|the)\b', r'a', item, 1)
			# the error_item gets printed when it can't find one
			error_item = re.sub(r'\bmy\b', '%temp%', item)
			error_item = re.sub(r'\bme\b', '%temp2%', item)
			error_item = re.sub(r'\byour\b', 'my', error_item)
			error_item = re.sub(r'%temp%', 'your', error_item)
			error_item = re.sub(r'%temp2%', 'you', error_item)
			# the item is the actual string it looks for
			item = re.sub(r'my', "%s's" % userinfo['name'], item)
			item = re.sub(r'me', "%s" % userinfo['name'], item)
			item = re.sub(r'\byour\b', 'my', item)
			response = "not holding %s" % error_item
			if item in self.inventory:
				response = "dropped %s" % item
			self.inventory = [x for x in self.inventory if x != item]

		elif re.match(r'(show|list) ?(inventory|items)?', command):
			response = "holding "
			if len(self.inventory) == 0:
				response += "nothing"
			elif len(self.inventory) == 1:
				response += self.inventory[0]
			elif len(self.inventory) == 2:
				response += "%s and %s" % (self.inventory[0], self.inventory[1])
			else:
				for item in self.inventory[:-1]:
					response += item + ", "
				response += "and %s" % self.inventory[-1]

		elif re.match(r'remember ', command):
			m = re.match(r'remember (that )?(.+) (is .+|are .+|have .+|has .+)', command)
			if m:
				if m and m.group(2) != "i":
					response = "will remember that about " + m.group(2)
					if m.group(2) in self.facts:
						self.facts[m.group(2)].append(m.group(3))
					else:
						self.facts[m.group(2)] = [m.group(3)]
				else:
					m2 = re.match(r'remember (that )?i (am .+|have .+)', command)
					if m2:
						response = "will remember that about you"
						fact = m2.group(2)
						fact = re.sub(r'\bam\b', 'is', fact)
						fact = re.sub(r'\bhave\b', 'has', fact)
						fact = re.sub(r'\blike\b', 'likes', fact)
						if userinfo['name'] in self.facts:
							self.facts[userinfo['name']].append(fact)
						else:
							self.facts[userinfo['name']] = [fact]
					else:
						response = "MALFORMED USER COMMAND"
			else:
				if userinfo['name'] in self.facts:
					self.facts[userinfo['name']].append('said "' + command + '"')
				else:
					self.facts[userinfo['name']] = ['said "' + command + '"']
				response = "will remember you said that"

		elif re.match(r'forget ', command):
			m = re.match(r'forget (that )?(.+) (is .+|are .+|have .+|has .+)', command)
			if m and m.group(2) != "i":
				response = "will forget that about " + m.group(2)
				if m.group(2) in self.facts:
					origNum = len(self.facts[m.group(2)])
					self.facts[m.group(2)] = [x for x in self.facts[m.group(2)] if x != m.group(3)];
					newNum = len(self.facts[m.group(2)])
					if origNum - newNum == 0:
						response = "didn't know that about %s" % m.group(2)
					else:
						if origNum - newNum > 1:
							response = "forgot %d things" % (origNum - newNum)
						else:
							response = "forgot that %s %s" % (m.group(2), m.group(3))
					if newNum == 0:
						del self.facts[m.group(2)]
				else:
					response = "never knew anything about %s" % m.group(2)
			else:
				m2 = re.match(r'forget (that )?i (am .+|have .+|like .+)', command)
				if m2:
					response = "will forget that about you"
					fact = m2.group(2)
					fact = re.sub(r'\bam\b', 'is', fact)
					fact = re.sub(r'\bhave\b', 'has', fact)
					if userinfo['name'] in self.facts:
						origNum = len(self.facts[userinfo['name']])
						self.facts[userinfo['name']] = [x for x in self.facts[userinfo['name']] if x != fact];
						newNum = len(self.facts[userinfo['name']])
						if origNum - newNum == 0:
							response = "didn't know that about you"
						else:
							if origNum - newNum > 1:
								response = "forgot %d things" % (origNum - newNum)
							else:
								response = "forgot that %s %s" % (userinfo['name'], fact)
						if newNum == 0:
							del self.facts[userinfo['name']]
					else:
						response = "never knew anything about you to begin with"
				else:
					response = "MALFORMED USER COMMAND"

		elif re.match(r'tell me about ', command):
			m = re.match(r'tell me about +(.+)', command)
			if m.group(1) in self.facts:
				response = "%s %s" % (m.group(1), random.choice(self.facts[m.group(1)]))
			elif m.group(1) == 'myself':
				if userinfo['name'] in self.facts:
					response = "%s %s" % (userinfo['name'], random.choice(self.facts[userinfo['name']]))
				else:
					response = "don't know anything about you"
			else:
				response = "don't know anything about " + m.group(1)

		elif re.match(r'tell me something', command):
			fact = random.choice(self.facts.keys())
			response = "%s %s" % (fact, random.choice(self.facts[fact]))

		elif re.match(r'tell me what you know', command):
			for thing in self.facts.keys():
				for fact in self.facts[thing]:
					response += "%s %s\n" % (thing, fact)

		elif re.match(r'commlist', command):
			for thing in self.commands.keys():
				for comm in self.commands[thing]:
					response += "%s: %s\n" % (thing, comm)

		elif re.match(r'do math', command):
			num1 = random.randint(1, 10)
			num2 = random.randint(1, 10)
			op = random.choice(['plus', 'minus', 'times', 'over', 'sqrt', 'pwr'])
			if op == 'plus':
				response = "%d plus %d is %d" % (num1, num2, num1 + num2)
			elif op == 'minus':
				response = "%d minus %d is %d" % (num1, num2, num1 - num2)
			elif op == 'times':
				response = "%d times %d is %d" % (num1, num2, num1 * num2)
			elif op == 'over':
				response = "%d over %d is %f" % (num1, num2, float(num1) / float(num2))
			elif op == 'sqrt':
				response = "the square root of %d is %f" % (num1, math.sqrt(num1))
			elif op == 'pwr':
				response = "%d to the power of %d is %d" % (num1, num2, num1 ** num2)

		elif re.match(r'set inv(entory)? size to \d+', command):
			if userinfo['name'] == 'broomweed':
				m = re.match(r'set inv size to (\d+)', command)
				self.invSize = int(m.group(1))
				response = "inventory size is now %d" % int(m.group(1))
			else:
				response = "only broomweed can do this, %s" % userinfo['name']

		elif re.match(r'say .+', command):
			m = re.match('say +(.+)', command)
			response = m.group(1)

		elif ('save dict' in command):
			if userinfo['name'] != 'broomweed':
				response = "only broomweed can do this for me, %s." % userinfo['name']
				return response
				
			try:
				self.saveDictionary()
				response = 'DICTIONARY SAVED SUCCESSFULLY'
			except IOError:
				response = 'DICTIONARY COULD NOT BE SAVED'

		elif ('load dict' in command):
			if userinfo['name'] != 'broomweed':
				response = "only broomweed can do this for me, %s." % userinfo['name']
				return response
			
			try:
				self.loadDictionary()
				response = 'DICTIONARY LOADED SUCCESSFULLY'
			except IOError:
				response = 'DICTIONARY COULD NOT BE LOADED'

		elif ('erase dict' in command):
			if userinfo['name'] != 'broomweed':
				response = "only broomweed can do this for me, %s." % userinfo['name']
				return response

			response = '!!! not sure you really want to do this !!!'

			#self.dictionary = { self.STOPWORD : ([self.STOPWORD], [self.STOPWORD]) }
			#response = 'DICTIONARY ERASED (NOT SAVED YET)'
		
		elif ('learn' in command):
			if userinfo['name'] != 'broomweed':
				response = "only broomweed can do this for me, %s." % userinfo['name']
				return response

			self.toggleLearn()
			response = 'I AM ' + ('NOW' if self.isLearning else 'NO LONGER') + ' LEARNING'

		#elif sentByAdmin and ('!talkback' in command):
		elif ('talkback' in command):
			if userinfo['name'] != 'broomweed':
				response = "only broomweed can do this for me. current talkback = %f" % self.talkBackFreq
				return response

			try:
				self.talkBackFreq = float(command.split()[1])
				response = ('RESPONDING PROBABILITY SET TO %3f' % self.talkBackFreq)
			except IndexError:
				response = 'MALFORMED COMMAND'
			except ValueError:
				response = "%s isn't a number!" % command.split()[1]

		elif 'joke' in command:
			joke = ''
			while 'Q:' not in joke:
				joke = subprocess.check_output(['fortune'])
			response = joke

		elif command.startswith('leave'):
			print self.CLIENT, channel
			print "&", self.CLIENT.api_call('channels.leave', {'channel': channel})

		elif command.startswith('repeat '):
			m = re.match(r'repeat +([^ ]+)', command)
			self.repeatWords.append(m.group(1))
			response = '"%s" now in repeat-mode' % m.group(1)

		elif command.startswith('norepeat '):
			m = re.match(r'norepeat +([^ ]+)', command)
			self.repeatWords = [r for r in self.repeatWords if r != m.group(1)]
			response = '"%s" no longer in repeat-mode' % m.group(1)

		elif 'good night' in command or 'goodnight' in command:
			if userinfo['name'] == 'broomweed':
				try:
					self.saveDictionary()
					self.sendMessage(channel, 'goodnight!')
					self.quit()
				except IOError:
					self.sendMessage(channel, "couldn't save dictionary. please disable manually")
			else:
				response = "nice try but no"

		else:
			# MALFORMED USER COMMAND
			#m = re.match(r"(\W)+\b", command)
			m = re.match(r'([^ ]+)', command)
			if not m:
				response = "MALFORMED USER COMMAND"
			else:
				commandPhrase = m.group(1)
				if commandPhrase in self.repeatWords:
					if commandPhrase in self.commands:
						if len(self.commands[commandPhrase]) >= 3:
							response = commandPhrase + "; " + random.choice(self.commands[commandPhrase]).replace("manatee", userinfo['name'])
						else:
							self.commandSought = commandPhrase
							response = self.generateChain(command)
					else:
						response = self.generateChain(command)
						self.commands[commandPhrase] = []
						self.commandSought = commandPhrase
				else:
					response = self.generateChain(command)

			#response = "MALFORMED USER COMMAND"

		if response is not None and response != '':
			response = fixGrammar(response)

		return response


	def onQuit(self):

		# try:
		# 	self.saveDictionary()
		# 	print ('DICTIONARY SAVED SUCCESSFULLY')
		# except IOError:
		# 	print ('DICTIONARY COULD NOT BE SAVED')
		pass

	def interpretMessage(self, message):

		print "Interpreting message."
		for i in self.ignore:
			if i in message:
				print "== Going to ignore that message. =="
				return

		words = message.split()
		words.append(self.STOPWORD)
		words.insert(0, self.STOPWORD)
            
		index = 0
		word = words[index]

            	while (True):
			
			try:
                    		next = words[index + 1]

			except IndexError:
		      		# this means we got to the end of the sentence
		      		break
                
			# add 'next' as a word that comes after 'word'
                	if self.dictionary.has_key(word):

				temp = self.dictionary.get(word)[1]
				wordindex = self.wordIndexInList(next, temp)
				
				if (wordindex == -1):
					temp.append( (next, 1) )
				else:
					prevcount = temp[wordindex][1]
					temp[wordindex] = (next, prevcount + 1)
					
                	else:
                    		self.dictionary[word] = ( [], [(next, 1)] )
                    
			# add 'word' as a word that comes before 'next'
			if self.dictionary.has_key(next):
				
				othertemp = self.dictionary.get(next)[0]
				wordindex = self.wordIndexInList(word, othertemp)

				if (wordindex == -1):
					othertemp.append( (word, 1) )
				else:
					prevcount = othertemp[wordindex][1]
					othertemp[wordindex] = (word, prevcount + 1)

                	else:
                    		self.dictionary[next] = ( [(word, 1)], [] )

			
                	index  = index + 1
			word = words[index]
		
			# print self.dictionary
        

	def generateChain(self, message):
        	
		words = message.split()
		
		# remove words we don't know
		for checkword in words:

			if not (self.dictionary.has_key(checkword)):
				words.remove(checkword)

		if len(words) == 0:
			return ''

		seed = random.choice(words)

		chain = ''	
		

		# forwards
		word = seed
            	while (word != self.STOPWORD) and (self.dictionary.has_key(word)):
			
			space = ('' if chain == '' else ' ')
               		chain = chain + space + word
               		word = self.chooseWordFromList( self.dictionary.get(word)[1] )
          

		# backwards
		if self.dictionary.has_key(word):
			word = self.chooseWordFromList( self.dictionary.get(seed)[0] )
			# so we don't have the seed twice


		while (word != self.STOPWORD) and (self.dictionary.has_key(word)):
               		chain = word + ' ' + chain
               		word = self.chooseWordFromList( self.dictionary.get(word)[0] )

		return chain
            
        

	def saveDictionary(self):
        
				output = open('Markov_Dict.pkl', 'w')
				pickle.dump(self.dictionary, output)
				output.close()

				output = open('Facts.pkl', 'w')
				pickle.dump({ 'facts': self.facts, 'inventory': self.inventory, 'commands': self.commands, 'repeat': self.repeatWords }, output)
				output.close()

	def loadDictionary(self):
        
		input = open('Markov_Dict.pkl', 'r')
		self.dictionary = pickle.load(input)
		input.close()

		input = open('Facts.pkl', 'r')
		state = pickle.load(input)
		if 'facts' in state:
			self.facts = state['facts']
		if 'inventory' in state:
			self.inventory = state['inventory']
		if 'commands' in state:
			self.commands = state['commands']
		if 'repeat' in state:
			self.repeatWords = state['repeat']
		input.close()



	def toggleLearn(self):

		self.isLearning = not self.isLearning


	def wordIndexInList(self, findword, list):

		word = ''
		for index in range( len(list) ):
			if (list[index][0] == findword):
				return index
		return -1



	def chooseWordFromList(self, list):

		sum = 0
		stops = [0]

		for pair in list:

			sum = sum + pair[1]
			stops.append(sum)

		rand = random.randint(1, sum)

		for index in range( len(stops) ):
			
			if (rand <= stops[index]):
				return list[index - 1][0]
			
		return list[0][0]




def fixGrammar(response):
	openquotes = len(re.findall('(^| )"', response))
	closequotes = len(re.findall(r'"[.!? ]', response))
	openparens = response.count('(')
	closeparens = response.count(')')
	openticks = len(re.findall('(^| )`', response))
	closeticks = len(re.findall(r'`[.!? ]', response))
	if not re.match(r'.*[.?!]$', response):
		response = response + '.'
	
	response = response.replace('```', '')

	while openquotes > closequotes:
		response += '"'
		openquotes -= 1
	while closequotes > openquotes:
		response = '"' + response
		closequotes -= 1
	while openparens > closeparens:
		response += ')'
		openparens -= 1
	while closeparens > openparens:
		response = '(' + response
		closeparens -= 1
	while openticks > closeticks:
		response += '`'
		openticks -= 1
	while closeticks > openticks:
		response = '`' + response
		closeticks -= 1

	for i, c in enumerate(response):
		if c.isalpha() or c.isdigit():
			# Don't try to capitalize parentheses or whatever.
			break

	if not response.startswith("Q:"):
		# Don't try to fix capitalization on jokes.
		response = response[:i] + response[i:].capitalize()
		response = re.sub(r'([!?.][)"\]`]?) *([a-z])', lambda match: r'%s %s' % (match.group(1), match.group(2).upper()), response)

	response = re.sub(r'\bi\b', 'I', response)
	return response
