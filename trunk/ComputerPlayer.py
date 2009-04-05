# -*- coding: utf-8 -*-

from random import randrange
from CanastaObjects import *

class ComputerPlayer:

	def __init__(self,myteam):
		self.meldValues = [4,5,6,7,8,9,10,11,12,13,14,15]
		self.cardColors = ['s','c','d','h']
		self.cardValues = ['a','2','3','4','5','6','7','8','9','t','j','q','k','Jo']
		self.cardCodes = [['s','a'],['s','2'],['s','3'],['s','4'],['s','5'],['s','6'],['s','7'],['s','8'],['s','9'],['s','t'],['s','j'],['s','q'],['s','k'],['c','a'],['c','2'],['c','3'],['c','4'],['c','5'],['c','6'],['c','7'],['c','8'],['c','9'],['c','t'],['c','j'],['c','q'],['c','k'],['d','a'],['d','2'],['d','3'],['d','4'],['d','5'],['d','6'],['d','7'],['d','8'],['d','9'],['d','t'],['d','j'],['d','q'],['d','k'],['h','a'],['h','2'],['h','3'],['h','4'],['h','5'],['h','6'],['h','7'],['h','8'],['h','9'],['h','t'],['h','j'],['h','q'],['h','k'],['Jo','Jo']]
		self.cardCodeToCancolor = (14,0,-1,4,5,6,7,8,9,10,11,12,13,14,0,-1,4,5,6,7,8,9,10,11,12,13,14,0,100,4,5,6,7,8,9,10,11,12,13,14,0,100,4,5,6,7,8,9,10,11,12,13,0)
		self.cardLocations = [[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1],[-1,-1,-1,-1]]
		self.firstplay = True
		self.firstturn = True
		self.curPos = None
		self.myPos = 100*(myteam+1)
		self.myTeam = 100 - (self.myPos % 200)
		self.curTop = None
		self.numCards = None
		self.frozen = False

	def isReady(self):
		return True

	def initRound(self,status):
		for locIndex, I in enumerate(self.cardLocations):
			for subIndex, i in enumerate(I):
				self.cardLocations[locIndex][subIndex] = -1
		self.firstplay = True
		self.firstturn = True
		self.curTop = None

	def readChat(self):
		return CanastaCommand(NO_PLAY,[],[])

	def initLocations(self,status):
	
		for c in status.curLocations:
			mem_index = self.cardCodes.index([c.color,c.value])
			if c.isTop:
				self.curTop = [mem_index,self.cardLocations[mem_index].index(-1),c.cancolor]
			self.cardLocations[mem_index][self.cardLocations[mem_index].index(-1)] = c.location
			

		return

	def initHand(self,status):
			
		for c in status.curLocations:
			if c.location == self.curPos:
				mem_index = self.cardCodes.index([c.color,c.value])
				self.cardLocations[mem_index][self.cardLocations[mem_index].index(-1)] = c.location

		return
		
	def findTop(self,status):
		for c in status.curLocations:
			if c.isTop:
				return c
		return 0

	def meldsNow(self,status):
		output = [None, None, None, None, 0,0,0,0,0,0,0,0,0,0,0,0,0]
		for c in status.curLocations:
			if c.location in range(self.curTeam+3,self.curTeam+16):
				output[c.location % 100] += 1
		return output

	def meldsWildNow(self,status):
		output = [None, None, None, None, 0,0,0,0,0,0,0,0,0,0,0,0,0]
		for c in status.curLocations:
			if (c.location in range(self.curTeam+3,self.curTeam+16)) & (c.cancolor==0):
				output[c.location % 100] += 1
		return output

	def meldsWild(self):
		output = [None, None, None, None, 0,0,0,0,0,0,0,0,0,0,0,0,0]
		for locIndex, I in enumerate(self.cardLocations):
			for i in I:
				if (i in range(self.curTeam+3,self.curTeam+16)) & (self.cardCodeToCancolor[locIndex]==0):
					output[i % 100] += 1
		return output


	def meldsPrev(self):
		output = [None, None, None, None, 0,0,0,0,0,0,0,0,0,0,0,0,0]
		for I in self.cardLocations:
			for i in I:
				if i in range(self.curTeam+3,self.curTeam+16):
					output[i % 100] += 1
		return output

	def meldedBoth(self,status,color,value):
		index = 0

		for c in status.curLocations:
			if (c.color == color) & (c.value == value) & (c.location in range(self.curTeam+3,self.curTeam+16)):
				index += 1
		if index>1:
			return True
		else:
			return False

	def updatePile(self,status):
		last_team = self.curPos - 100
		if last_team==0:
			last_team=400
		new_top = self.cardCodes.index([self.findTop(status).color,self.findTop(status).value])
		if last_team in self.cardLocations[new_top]:
			self.curTop = [new_top,self.cardLocations[new_top].index(last_team),self.findTop(status).cancolor]
			self.cardLocations[new_top][self.cardLocations[new_top].index(last_team)] = IN_PILE
		else:
			self.curTop = [new_top,self.cardLocations[new_top].index(-1),self.findTop(status).cancolor]
			self.cardLocations[new_top][self.cardLocations[new_top].index(-1)] = IN_PILE


	def updateMelds(self,status):

		if self.curPos==self.myPos:
		    for locIndex, I in enumerate(self.cardLocations):
			    for subIndex, i in enumerate(I):
				    if i in range(3,16):
					    self.cardLocations[locIndex][subIndex] = self.myPos

		codes_melded = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
		meld_where = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]]
		for c in status.lastMelded:
			codes_melded[self.cardCodes.index([c.color,c.value])] += 1
			meld_where[self.cardCodes.index([c.color,c.value])].append(c.location)

		for mem_index, i in enumerate(codes_melded):
			num_cards = i
			while num_cards>0:
			    num_cards -= 1
			    if self.curPos in self.cardLocations[mem_index]:
				    #print self.cardLocations[mem_index]
				    self.cardLocations[mem_index][self.cardLocations[mem_index].index(self.curPos)] = meld_where[mem_index][num_cards]
			    else:
				    #print self.cardLocations[mem_index]
				    self.cardLocations[mem_index][self.cardLocations[mem_index].index(-1)] = meld_where[mem_index][num_cards]
	   
	def updateHand(self,status):

		loc_list = [self.myPos] + range(3,16)
		for locIndex, I in enumerate(self.cardLocations):
			for subIndex, i in enumerate(I):
				if i in loc_list:
					self.cardLocations[locIndex][subIndex] = -1
		for c in status.curLocations:
			if c.location in loc_list:
				mem_index = self.cardCodes.index([c.color,c.value])
				self.cardLocations[mem_index][self.cardLocations[mem_index].index(-1)] = c.location		
	
	def updatePileToHands(self,status):

		for locIndex, I in enumerate(self.cardLocations):
			for subIndex, i in enumerate(I):
				if i==IN_PILE:
					self.cardLocations[locIndex][subIndex] = self.curPos
		self.curTop = None

	def mayIGoOut(self):
		return True

	#Read data on another player's actions
	def readPlay(self,status):

		if (status.lastCommand == NO_PLAY) or status.roundOver:
			return

		self.curPos = 100*(status.curTurn+1)
		self.curTeam = 200 - (self.curPos % 200)

		#print ["last command",status.lastCommand,status.lastReturn]

		if self.firstplay:
			self.initLocations(status)
			self.firstplay = False
		elif (status.lastCommand in [DRAW_CARD,TO_STAGE,CLEAR_STAGE]) & (self.curPos==self.myPos):
			self.updateHand(status)
		elif (status.lastReturn == True):
			if status.lastCommand in [DRAW_CARD,PASS_TURN]:
				return
			elif status.lastCommand == DISCARD_CARD:
				self.updatePile(status)
			elif status.lastCommand in [MELD_CARDS] + tlist:
				self.updateMelds(status)
				if self.curPos==self.myPos:
					self.updateHand(status)
			elif status.lastCommand == PICK_PILE:
				self.updatePileToHands(status)
				self.updateMelds(status)
				if self.curPos==self.myPos:
					self.updateHand(status)
	
		return

	def pileSize(self):
		output = 0
		for I in self.cardLocations:
			for i in I:
				if i==1:
					output += 1
		return output

	def countValue(self,m):

		count = 0
		for locIndex, I in enumerate(self.cardLocations):
			card_val = self.cardCodeToCancolor[locIndex]
			for i in I:
				if (i == self.myPos) & (card_val == m):
					count += 1
		return count

	def oppcountValue(self,m):

		count = 0
		opp_loc = self.myPos + 100
		if opp_loc == 500:
			opp_loc = 100
		for I in self.cardLocations:
			card_val = self.cardCodeToCancolor[self.cardLocations.index(I)]
			for i in I:
				if (i == opp_loc) & (card_val == m):
					count += 1
		return count

	def allCards(self):

		output = []

		for m in self.meldValues:
			count = self.countValue(m)
			if count>0:
				output.append(m)

		return output

	def wildableCards(self):

		output = []

		for m in range(4,15):
			count = self.countValue(m)
			if count>1:
				output.append(m)

		return output

	def meldAddable(self):
		output = []

		if len(self.meldList())>0:
			for m in self.meldList():
				count = self.countValue(m)
				if count>20:
					output.append(m)

		return output			

	def meldableCards(self):

		output = []

		for m in range(4,15):
			count = self.countValue(m)
			if count>2:
				output.append(m)

		return output

	def oppmeldableCards(self):

		output = []

		for m in range(4,15):
			count = self.oppcountValue(m)
			if count>2:
				output.append(m)

		return output

	def meldList(self):

		output = []

		for m in range(4,16):
			if self.meldsPrev()[m]>0:
				output.append(m)

		return output

	def nearCanastaList(self,threshold):

		output = []

		for m in range(4,16):
			if self.meldsPrev()[m]>=threshold:
				output.append(m)

		return output

	def oppmeldAmounts(self):
		oppmelds = [None, None, None, None, 0,0,0,0,0,0,0,0,0,0,0,0,0]

		for m in range(4,16):
			for I in self.cardLocations:
			      for i in I:
				    if i==(300 - self.curTeam) + m:
					  oppmelds[m] += 1

		return oppmelds

	def oppmeldList(self):

		output = []
		oppmelds = self.oppmeldAmounts()

		for i in range(4,16):
			if oppmelds[i]>0:
			      output.append(i)

		return output
	
	def stageValue(self,status):
		output = 0
		for c in status.curLocations:
			if c.location in range(3,16):
				output += c.canvalue

	def cardsInHand(self):
		count = 0
		for I in self.cardLocations:
			for i in I:
				if (i == self.curPos):
					count += 1
		return count

	def haveCanasta(self):
		output = False
		for m in range(4,16):
			if self.meldsPrev()[m]>6:
				output = True

		return output

	def opphaveCanasta(self):
		output = False
		for m in range(4,16):
			if self.oppmeldAmounts()[m]>6:
				output = True

		return output

	def whereCard(self,cancol,loc):
		result = 0
		for locIndex, I in enumerate(self.cardLocations):
			for subIndex, i in enumerate(I):
			      if (self.cardCodeToCancolor[locIndex]==cancol) & (i==loc):
				    result += 1
		return result	

	def cardAt(self,loc):
		result = 0
		for locIndex, I in enumerate(self.cardLocations):
			for subIndex, i in enumerate(I):
			      if (i==loc):
				    result += 1
		return result

	def  getWild(self,status):
		result = 0
		for c in status.curLocations:
			if (c.cancolor==0) & (result==0) & (c.location == self.curPos):
			    result = c.whereInHand
			elif (c.canvalue==50) & (c.cancolor==0) & (c.location == self.curPos):
			    result = c.whereInHand
		return result

	def genDiscard(self,status):
		next_player = self.myPos + 100
		prev_player = self.myPos - 100
		partner = self.myPos + 200
		if next_player==500:
			next_player = 100
		if prev_player==0:
			prev_player = 400
		if partner > 400:
		    partner -= 400
		output = [0]*(self.cardsInHand()+1)
		output[0] = -999
		opp_wilds = self.whereCard(IS_WILD,next_player)
		value_list = [50,20,10,5]

		for c in status.curLocations:
			opp_has = self.whereCard(c.cancolor,next_player)
			in_pile = self.whereCard(c.cancolor,IN_PILE)
			opp_hasmeld = self.whereCard(c.cancolor,next_player+c.cancolor)
			loc_unknown = self.whereCard(c.cancolor,-1)
			
			if c.location == self.myPos:
			     if (opp_has>1) | ((opp_has>0) & (opp_wilds>0) & (not self.frozen)):
				  output[c.whereInHand] = 0
			     elif (c.cancolor==0) & (not self.frozen) & (len(self.meldList()) < (len(self.oppmeldList())-3)) & (not self.goOut()):
				  output[c.whereInHand] = 7
		             elif (opp_hasmeld>6):
				  output[c.whereInHand] = 7
			     elif (opp_hasmeld>0) & (not status.frozen):
				  output[c.whereInHand] = 7 - opp_hasmeld
			     elif (opp_hasmeld>0) & (status.frozen):
				  output[c.whereInHand] = 7
			     elif (c.canvalue>10):
				  output[c.whereInHand] = 1
			     else:
				  output[c.whereInHand] = 9 - loc_unknown

			     if c.cancolor in self.allCards():
				  output[c.whereInHand] -= 2
			     if c.cancolor in self.meldableCards():
				  output[c.whereInHand] -= 4
			     if c.cancolor in self.wildableCards():
				  output[c.whereInHand] -= 3
			     if c.cancolor in self.meldList():
				  output[c.whereInHand] -= 3
			     if (c.canvalue>=10) & (self.minmeld==120) & (len(self.meldList())==0):
				  output[c.whereInHand] -= 2
			     if (c.canvalue==50) & (self.minmeld>50):
				  output[c.whereInHand] -= 2
			     if (c.cancolor==0) & (len(self.meldList()) + len(self.oppmeldList()) == 0):
				  output[c.whereInHand] -= 2

		return output

	def cardsLeft(self):
		result = sum(self.numCards)
		for i in (range(103,116)+range(203,216) + [1,2000,3000]):
			result += self.cardAt(i)
		result = 108 - result
		return result

	def pickPile(self):
		if (self.pileSize()>4) & (not self.goOut()):
			return True
		else:
			return False

	def goIn(self):
		if len(self.meldList()):
			return True
		elif (self.cardsInHand()>5) | (self.cardsLeft()<15) | (max(self.oppmeldAmounts())>4):
			return True
		else:
			return False

	def meldWildExisting(self):
		output = -99
		if ((self.meldsPrev().count(5)>0) | (self.meldsPrev().count(6)>0)):
			if self.meldsPrev().count(6)>0:
				output = self.meldsPrev().index(6)
			else:
				output = self.meldsPrev().index(5)
		return output

	def meldExisting(self):
		if (len(self.meldAddable())):
			if self.frozen:
			      for i in self.meldAddable():
				    if i in self.nearCanastaList(5):
					  return i
			      return -99
			else:
			      return self.meldAddable()[0]
		else:
			return -99

	def meldNatural(self):
		if (self.cardsInHand()>5) | self.goOut() | ((self.minmeld>50) & (len(self.meldAddable())==0)):
			if len(self.meldableCards()):
				for i in self.meldableCards():
				    if (self.state==POST_DRAW) | (i != self.topcolor):
					return i
				return -99
			else:
				return -99
		else:
			return -99

	def meldDirty(self):
		if self.goOut() | (len(self.meldList())==0):
			if len(self.wildableCards()):
				for i in self.wildableCards():
				    if (self.state==POST_DRAW) | (i != self.topcolor):
					return i
				return -99
			else:
				return -99
		else:
			return -99

	def goOut(self):
		next_player = self.myPos + 100
		prev_player = self.myPos - 100
		partner = self.myPos + 200
		if next_player==500:
			next_player = 100
		if prev_player==0:
			prev_player = 400
		players = [100,200,300,400]
		next_player_cards = self.numCards[players.index(next_player)]
		prev_player_cards = self.numCards[players.index(prev_player)]

		if (self.haveCanasta()) & (len(self.meldList()) < len(self.oppmeldList())+1):
			return True
		elif self.opphaveCanasta() & (prev_player_cards< 3 | next_player_cards<3):
			return True
		else:
			return False

	def matchTop(self,status):
		args = []
		awild = False
		for c in status.curLocations:
			if c.location == self.curPos:
				if c.cancolor == self.findTop(status).cancolor:
					args.append(c.whereInHand)
		if len(args)==1:
			for c in status.curLocations:
				if (not awild) & (not self.frozen) & (c.location == self.curPos):
					if c.cancolor==0:
					    args.append(c.whereInHand)
					    awild = True
		return args
				

	#Take a game status and output a play command
	def getPlay(self,status):

		action = NO_PLAY
		args = []
		token = []

		self.curPos = 100*(status.curTurn+1)
		self.curTeam = 200 - (self.curPos % 200)

		if self.firstplay:
			self.initLocations(status)
			self.firstplay = False
			self.firstturn = False
			self.minmeld = status.meldPoints
		if self.firstturn:
			self.initHand(status)
			self.firstturn = False
			self.minmeld = status.meldPoints
		self.numCards = status.numCards
		self.frozen = status.frozen
		self.state = status.turnState
		if self.findTop(status) != 0:
		    self.topcolor = self.findTop(status).cancolor

		cardlist = []
		vallist = []
		wilds = []
		count = 0
		for c in status.curLocations:
			if c.location == self.myPos:
				count += 1
				c.whereInHand = count
				cardlist.append(c.cancolor)
				vallist.append(c.canvalue)
				if c.cancolor == 0:
					wilds.append(c.whereInHand)

		#print ["Pick",self.pickPile(),"In",self.goIn(),"MeldExist",self.meldExisting(),"MeldNat",self.meldNatural(),"MeldDirt",self.meldDirty(),"MakeCan",self.meldWildExisting(),"Go out",self.goOut()]

		if status.turnState == PRE_DRAW:

			if (not self.pickPile()):
				action = DRAW_CARD
			elif status.lastCommand not in [PICK_PILE,CLEAR_STAGE]:
				if DEBUGGER: print "Pick with nothing"
				action = PICK_PILE
				token = [0]
			elif (status.lastCommand == PICK_PILE) & (status.lastToken==[0]):
				if DEBUGGER: print "Pick with naturals, no stage"
				if self.findTop(status).cancolor in cardlist:
					action = PICK_PILE
					args = self.matchTop(status)
					token = [1]
				else:
					action = DRAW_CARD
			#If picking up with naturals doesn't work, use a wild card
			elif (status.lastCommand == PICK_PILE) & (status.lastToken==[1]):
				if DEBUGGER: print "Pick with wild, no stage"
				if (self.findTop(status).cancolor in self.allCards()) & (len(wilds)>0):
					action = PICK_PILE
					args = self.matchTop(status)
					token = [2]
				else:
					action = DRAW_CARD

			elif (status.lastCommand == PICK_PILE) & (status.lastToken==[2]):
				if DEBUGGER: print "Pick with stage"
				#If you can, stage any three-of-a-kind in your hand
				if len(self.meldableCards())>0:
					for c in status.curLocations:
						if c.location == self.curPos:
							if c.cancolor == self.meldableCards()[0]:
								args.append(c.whereInHand)
					if len(args) < len(self.allCards()):
						action = TO_STAGE
					else:
						action = PICK_PILE
						args = self.matchTop(status)
						token = [3]

				#If you have none, stage any combination of two naturals and a wild
				elif (len(self.wildableCards())>0) & (len(wilds)>0):
					awild = False
					for c in status.curLocations:
						if c.location == self.curPos:
							if c.cancolor== self.wildableCards()[0]:
								args.append(c.whereInHand)
					args.append(self.getWild(status))
					if len(args) < len(self.allCards()):
						action = TO_STAGE
					else:
						action = PICK_PILE
						args = self.matchTop(status)
						token = [3]
				else:
					action = PICK_PILE
					token = [3]
				
			#If you weren't able to pick the pile, draw a card.
			elif (status.lastCommand == PICK_PILE) & (status.lastToken == [3]):
				action = CLEAR_STAGE
			elif (status.lastCommand == CLEAR_STAGE):
				action = DRAW_CARD
			else:
				action = DRAW_CARD


		if status.turnState == POST_DRAW:
			#print ["meld status",self.meldList(),self.meldableCards(),self.wildableCards(),self.meldAddable()]

			if (status.lastCommand == PICK_PILE) & (status.lastReturn):
				action = CHAT
				args = ["Boo-ya! got the pile!"]
			elif (not self.goIn()):
				action = CLEAR_STAGE
			#Add a wild to an existing meld if it's close to a canasta
			elif (self.meldWildExisting() != -99) & (len(wilds)>0) & (not status.lastToken):
				if len(self.allCards()) > 1:
				    action = TO_STAGE
				    token = [self.meldWildExisting()]
				    print ["meld wild to",action]
				    args = [self.getWild(status)]
				else:
				    action = MELD_CARDS

			#If you have something to add to an existing meld, stage it.
			elif self.meldExisting() != -99:
				if DEBUGGER: print "meld to existing"
				for c in status.curLocations:
					if c.location == self.curPos:
						if c.cancolor == self.meldExisting():
							args.append(c.whereInHand)
				if len(args) < len(self.allCards()):
					action = TO_STAGE
				else:
					action = MELD_CARDS
			#If not, stage any three-of-a-kind in your hand
			elif self.meldNatural() != -99:
				if DEBUGGER: print "meld 3 of a kind"
				for c in status.curLocations:
					if (c.location == self.curPos) & (c.cancolor == self.meldNatural()):
							args.append(c.whereInHand)
				if len(args) < len(self.allCards()):
					action = TO_STAGE
				else:
					action = MELD_CARDS
			#If you have none, stage any combination of two naturals and a wild
			elif (self.meldDirty() != -99) & (len(wilds)>0):
				if DEBUGGER: print "meld with a wild"
				for c in status.curLocations:
					if c.location == self.curPos:
						if c.cancolor == self.meldDirty():
							args.append(c.whereInHand)
				args.append(self.getWild(status))
				if len(args) < len(self.allCards()):
					action = TO_STAGE
				else:
					action = MELD_CARDS
			#If there's nothing left to stage, meld the stage, unless you're not at your threshold
			else:         
				action = MELD_CARDS

			#Bug catcher--if melding didn't work, bring everything back to the hand
			if status.lastCommand == MELD_CARDS:
				action = CLEAR_STAGE

			#Select a discard, or pass if you can't discard
			if status.lastCommand == CLEAR_STAGE:
				#Order of priority on discards, taking into account point value,
				#whether the other player has melded it, whether you could meld
				#it, and whether the pile is frozen
				if (self.cardsInHand()>1) | self.haveCanasta():
					action = DISCARD_CARD
					discards = self.genDiscard(status)
					if DEBUGGER: print ["Discard ratings",discards]
					args = [discards.index(max(discards))]
				elif (self.cardsInHand()==1) & self.haveCanasta():
					action = GO_OUT
					args = []
				elif (self.cardsInHand()>1):
					action = DISCARD_CARD
					args = [randrange(1,handsize)]

					if len(args)>1:
						args = args[:1]
				else:
					action = PASS_TURN

		if DEBUGGER: print ["outputting",action,args,token,"from",self.curPos]
		output = CanastaCommand(action,args,token)

		return output             
