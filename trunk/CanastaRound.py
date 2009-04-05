# -*- coding: utf-8 -*-
import os, pygame,math
from pygame.locals import *
import random

from CardImages import CardImages
from CardGroup import CardGroup
from Card import Card

from twisted.spread import pb, jelly
from twisted.python import log

from CanastaObjects import *

class CanastaRound():

    """
    The main game object, which contains all the logic for playing Canasta.

    The default locations will be rescaled when the window size changes.
    """

    LOCATIONSXY = ((435,300),(530,300)) + ((300,650),(20,180),(300,10),(920,180)) + ((500,500),(290,115),(365,115),(440,115),(515,115),(590,115),(665,115),(290,475),(365,475),(440,475),(515,475),(590,475),(665,475)) + ((500,500),(125,200),(125,250),(125,300),(125,350),(125,400),(125,450),(795,200),(795,250),(795,300),(795,350),(795,400),(795,450)) + ((10,10),(850,665)) + ((20,600),(60,600),(100,600),(140,600),(20,670),(30,670),(40,670),(50,670),(60,670),(70,670),(80,670),(90,670),(100,670),(110,670))
    STAGEXY = (10,600,200,133)
    SCOREX = (750,0)
    CHATX = (750,50)
    XSCALE = 1
    YSCALE = 1

    MAX_HISTORY = 30
    history = []

    LOCATIONNAMES = ['pile','discard'] + ['bottom','left','top','right'] + ['3_1','4_1','5_1','6_1','7_1','8_1','9_1','t_1','j_1','q_1','k_1','a_1','wild_1'] + ['3_2','4_2','5_2','6_2','7_2','8_2','9_2','t_2','j_2','q_2','k_2','a_2','wild_2'] + ['red3_1','red3_2'] +  ['3_0','4_0','5_0','6_0','7_0','8_0','9_0','t_0','j_0','q_0','k_0','a_0','wild_0']
    LOCATIONS = [0,1] + [100,200,300,400] + range(103,116) + range(203,216) + [1000,2000] + range(3,16)

    positions = ["Bottom","Left","Top","Right"]

    def __init__(self,images=True):
	"""
	Initialize the game object. The server calls this with images=False to avoid using the pygame overhead, while clients call it with images=True in order to use the card image data.
	"""
	self.images = images
	self.chatlist = []
	self.curchat = ""
	self.enterchat = False

    def debugFunc(self):
	if not DEBUGGER:
	    return
        print "Selected locations"
        for c in self.selectionCards:
            print [c.color,c.value,c.location,c.rotated,c.order]
	print "Has Melded?"
	print self.hasMelded()
	print "To go in:"
	print [self.minmeld1,self.minmeld2]
	print "Has Canasta?"
	print self.hasCanasta()
        print "Scores"
	print [self.handPoints(1),self.cardPoints(1),self.specialPoints(1,True)]
	print [self.handPoints(2),self.cardPoints(2),self.specialPoints(2,True)]
 
############################
#Initialize the game and round
#############################

    def gameStart(self,playernames,human,options=CanastaOptions()):  

	"""
	Sets up the game object for the start of a game.
	"""

        text = [
            "Canasty v0.1",
            "-----------------------",
            "F1 - Display this help text.",
            "ESC - Quit.",
	    "Click the scoreboard to re-sort your cards",
            "Click the pile to draw a card",
	    "Click the discard pile to pick it up",
	    "(first stage or select cards",
	    "that you need to meld)",
	    "Drag a card to the pile to discard it",
	    "Select cards and right-click to meld",
	    "(or drag them onto an existing meld)",
	    "Drag melds to the stage area to stage them",
	    "Left-click the stage to meld it",
	    "(right-click to clear it)",
	    "See manual for alternate keyboard controls",
	    
            "-----------------------",
            "press any key to continue"]
    
        self.selectedCard = None
    
        self.selectionRect = pygame.Rect((0,0,0,0))
        self.selectionCards = []  
	self.selectedCards = []
               
        ci = CardImages(self.images)
        cards = []
        for i in range(0,54):
            cards.append(Card(ci.getCardNbr(i),ci.getBack(),ci.getColors(i),ci.getValues(i),ci.getCanColors(i),ci.getCanValues(i),ci.images))

	#second deck
        for i in range(0,54):
            cards.append(Card(ci.getCardNbr(i),ci.getBack(),ci.getColors(i),ci.getValues(i),ci.getCanColors(i),ci.getCanValues(i),ci.images))
                   
        self.cardGroup = CardGroup(ci.images,cards)
        self.cardGroup.shuffle()               

	if self.images:
	    self.helptext = pygame.Surface((400,475),1).convert()
	    self.helptext.fill((0x0, 0x0, 0x0))
	    self.helptext.set_alpha(200)
	    self.helptextRect = self.helptext.get_rect()
		
	    font = pygame.font.Font("FreeSans.ttf", 18)
	    ty = 8
	    for t in text:
	      img = font.render(t, 1, (0xff, 0xff, 0))
	      r = img.get_rect()
	      r.top = ty
	      r.centerx = self.helptextRect.centerx
	      ty += 25
	      self.helptext.blit(img,r.topleft)

	self.playernames = playernames
	self.human = human
	self.myPos = human
	self.partnerPos = 100*(self.myPos+1) + 200
	if self.partnerPos>400:
	    self.partnerPos -= 400

	self.red3penalty = options.red3penalty
	self.initfreeze = options.initfreeze
	self.counttop = options.counttop

	self.chatlist = []
	self.curchat = ""
	self.enterchat = False

	self.team1score = 0
	self.team2score = 0
	self.round = 0

        self.pushHistory("Setup Canasta")

    def newGame(self):
	self.team1score = 0
	self.team2score = 0
	self.round = 0
    
    def initCanasta(self):    

	"""
	Initialize a round. If the game object belongs to a client, the card locations will be overwritten by the server.
	"""
        self.selectionRect = pygame.Rect((0,0,0,0))
        self.selectionCards = [] 
	self.selectedCards = []
	self.lastMelded = []
        self.turnstart = False
        self.frozen = False
        self.topPile = -1
        self.roundOver = False
	self.invisible = False
	self.let_go_out = True

	self.round += 1
	self.turn = (self.round - 1) % 4

	self.endroundtext = None

        self.curlocxy = []
        self.curstagexy = []
        for i in range(len(self.LOCATIONSXY)):
            self.curlocxy.append(list(self.LOCATIONSXY[i]))
        for i in range(len(self.STAGEXY)):
            self.curstagexy.append(self.STAGEXY[i])
        self.curscorex = self.SCOREX[0]
        self.curscale = [self.XSCALE,self.YSCALE]
        self.locationsUpdate((1024,768))

        self.lastCommand = 0
        self.lastReturn = False
        self.lastArgs = []
        self.lastToken = []

        self.cardGroup.collectAll(435,335)
        self.cardGroup.shuffle()

	for index, c in enumerate(self.cardGroup.cards):
	    c.order = index
  
	if self.team1score <1500:
	    self.minmeld1 = 50
	if (self.team1score >= 1500) & (self.team1score < 3000):
	    self.minmeld1 = 90
	if (self.team1score >= 3000):
	    self.minmeld1 = 120

	if self.team2score <1500:
	    self.minmeld2 = 50
	if (self.team2score >= 1500) & (self.team2score < 3000):
	    self.minmeld2 = 90
	if (self.team2score >= 3000):
	    self.minmeld2 = 120
          
        gt = self.cardGroup.getCardAt  
                
        cards = 11
        self.idx = 107
             
        for c in self.cardGroup.cards:
            c.location = 0

        for cols in range(4):
            for hc in range(cards):
                c = gt(self.idx)
                while c.cancolor==100:
                    c.flip()
                    self.cardGroup.dropCard(c)
                    if cols % 2 == 0:
                        c.location = 1000
                    if cols % 2 == 1:
                        c.location = 2000
                    self.idx-=1
                    c = gt(self.idx)
                if cols==self.human:
                    c.flip()
                self.cardGroup.dropCard(c)
                c.location = 100*(cols+1)
                self.idx-=1
        c = gt(self.idx)
        c.flip()
        self.cardGroup.dropCard(c)
        c.location = 1
        self.topPile = c.cancolor
	self.topPileV = c.canvalue
	if (c.cancolor==0) & (not self.initfreeze):
	    self.turnedWild = True
	elif (c.cancolor==0) & self.initfreeze:
	    self.frozen = True
	else:
	    self.turnedWild = False
	c.isTop = True
        self.idx-=1

        self.handLayout()
        self.pileLayout()
        self.redThreeLayout()

############################
#package the current game state for export to a player module
#############################

    def curState(self,active=True):

	cardselect = []

	if self.turnstart:
	    turnstatus = POST_DRAW
	else:
	    turnstatus = PRE_DRAW

        if (len(self.selectionCards)>0) & active:
            for c in self.selectionCards:
                if c.location == 100*(self.turn+1):
                    cardselect.append(c)

        if self.curTeam()==1:
            meldPoints = self.minmeld1
        else:
            meldPoints = self.minmeld2

        numcards = []
        for i in [100,200,300,400]:
            num = 0
            for c in self.cardGroup.cards:
                    if c.location == i:
                            num+=1
            numcards.append(num)
        
        curLocations = []

        return_locations = [1000,2000] + range(103,116) + range(203,216)
        if active:
            return_locations.append(100*(self.turn+1))
            return_locations = return_locations + range(3,16)
            
        for c in self.cardGroup.cards:
            if (c.location in return_locations) | (c.isTop):
                curLocations.append(c)

	lastMelded = self.lastMelded

	result = CanastaStatus(meldPoints,self.turn,turnstatus,cardselect,curLocations,lastMelded,numcards,self.frozen,self.roundOver,self.lastCommand,self.lastReturn,self.lastArgs,self.lastToken)
	return result      

    def initStatus(self,active=False,fornet=False):

	locations = []

	for i in range(0,108):
	    c = self.cardGroup.cards[i]
	    locations.append([c.color,c.value,c.location,c.order])

	if fornet:
	    result = CopyCanastaInitStatus([self.minmeld1,self.minmeld2],locations,self.frozen,self.idx,self.red3penalty,self.initfreeze,self.counttop,self.playernames,active)
	else:
	    result = CanastaInitStatus([self.minmeld1,self.minmeld2],locations,self.frozen,self.idx,self.red3penalty,self.initfreeze,self.counttop,self.playernames,active)

	return result

    def readInit(self,initStatus):

	self.red3penalty = initStatus.red3penalty
	self.initfreeze = initStatus.initfreeze
	self.counttop = initStatus.counttop

	self.frozen = initStatus.frozen
	self.minmeld1, self.minmeld2 = initStatus.meldPoints

	for c in self.cardGroup.cards:
	    c.location = -1
	    c.isTop = False

	for I in initStatus.curLocations:
	    found = False
	    for c in self.cardGroup.cards:
		if (c.color==I[0]) & (c.value==I[1]) & (c.location == -1) & (not found):
		    found = True
		    c.location = I[2]
		    c.order = I[3]
		    self.cardGroup.popCard(c)
		    if c.location in [1,(self.myPos+1)*100,1000,2000]:
			if c.side==0:
			    c.flip()
		    elif c.side==1:
			c.flip()

	for c in self.cardGroup.cards:
	    if c.location == 1:
		self.topPile = c.cancolor
		self.topPileV = c.canvalue
		if (c.cancolor==0) & (not self.initfreeze):
		    self.turnedWild = True
		elif (c.cancolor==0) & self.initfreeze:
		    self.frozen = True
		else:
		    self.turnedWild = False
		c.isTop = True
	
	self.idx = initStatus.idx

	self.pileLayout()
	self.handLayout()
	self.redThreeLayout()

############################
#Internal condition functions
#############################

    def cardsInSet(self):
        clist = []
        for i in range(len(self.selectedCards)):
            if self.selectedCards[i].cancolor not in clist:
                clist.append(self.selectedCards[i].cancolor)
        return clist    

    def curTeam(self):
	result = (self.turn % 2) + 1
	return result

    def cardsInHand(self,include_stage=True):
        result = 0
	matchlist = [(self.turn+1)*100] 
	if include_stage:
	    matchlist += range(4,16)    
        for c in self.cardGroup.cards:
            if c.location in matchlist:
                result += 1
        return result          

    def numMelded(self,cancol,team):
	result = [0,0]
        if cancol==0:
            cancol = 15
	for c in self.cardGroup.cards:
	    if c.location == 100*team + cancol:
		result[0] += 1
		if c.cancolor == 0:
		    result[1] += 1
	return result

    def hasCanasta(self):
	result = False
	for i in range(4,16):
	    if self.numMelded(i,self.curTeam())[0]>=7:
		result = True
	return result

    def hasMelded(self):
	result = False
	meldLocations = range(100*self.curTeam()+4,100*self.curTeam() + 16)
	for c in self.cardGroup.cards:
	    if c.location in meldLocations:
		result = True
	return result
	  
    def pointsToGoIn(self):
	if self.curTeam() == 1:
	    return self.minmeld1
	if self.curTeam() == 2:
	    return self.minmeld2

    def cardsOnTable(self):
        team = (self.turn % 2)
        result = []
        if team == 0:
            meldLocations = range(103,116)
        if team == 1:
            meldLocations = range(203,216)
        for c in self.cardGroup.cards:
            if (c.location in meldLocations) & (c.cancolor not in result):
                result.append(c.cancolor)
        return result

    def pileSize(self):
	result = 0
	for c in self.cardGroup.cards:
	    if c.location == 1:
		result += 1
	return result

    def cardLocations(self):
        clist = []
        for i in range(len(self.selectedCards)):
            if self.selectedCards[i].location not in clist:
                clist.append(self.selectedCards[i].location)
        return clist
    
    def cardDirtyMeldOK(self):
        num_naturals = 0
        naturals = []
        for i in range(len(self.selectedCards)):
            if self.selectedCards[i].cancolor in range(4,15):
                num_naturals += 1
                if self.selectedCards[i].cancolor not in naturals:
                    naturals.append(self.selectedCards[i].cancolor) 
            if self.selectedCards[i].cancolor == -1:
                naturals = [99]
        if len(naturals)>1:
            naturals = [99]
        if num_naturals < (len(self.selectedCards) / 2) + 1:
            naturals = [99]
        return naturals[0]       

    def canGoOut(self):
	if not self.turnstart:
	    return False
	elif not self.hasCanasta():
	    return False
	elif self.cardsInHand(include_stage=False)>1:
	    return False
	else:
	    return True

############################
#Layout functions
#############################

    def handLayout(self):

        toSort = [100,200,300,400]
        offsets = [[20,0],[0,20],[20,0],[0,20]]
	offsets2 = [[0,20],[20,0],[0,20],[20,0]]
        counts = [0,0,0,0]
	row = [0,0,0,0]

        for t in toSort:
            self.selectedCards = []
            for c in self.cardGroup.cards:
                if c.location == t:
                    whichGroup = toSort.index(c.location)
                    counts[whichGroup] += 1
                    coords = self.LOCATIONS.index(c.location)
		    if self.images:
			c.rect.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0] + row[whichGroup]*offsets2[whichGroup][0]
			c.rect.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1] + row[whichGroup]*offsets2[whichGroup][1]
                    self.selectedCards.append(c)

		    if counts[whichGroup]>15:
			counts[whichGroup]=0
			row[whichGroup]+=1
            self.sortSelection()
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))
        self.selectedCards = []
        self.selectionCards = []

    def meldLayout(self):

        toSort =  range(103,116) + range(203,216)
        offsets = [[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0],[10,0]]
        counts = [0]*len(toSort)
	self.selectedCards = []
        for c in self.cardGroup.cards:
            if c.location in toSort:
		self.selectedCards.append(c)
	self.sortSelection()
	for c in self.selectedCards:
	    whichGroup = toSort.index(c.location)
	    counts[whichGroup] += 1
	    coords = self.LOCATIONS.index(c.location)
	    this_meld = self.numMelded(c.location % 100,team=c.location / 100)

	    if c.side==0:
		c.flip()

	    if this_meld[0]<7:
                cur_offset = offsets[whichGroup]
            else:
                cur_offset = [0,0]
		if (this_meld[1]==0) & (c.color in ['d','h']):
		    self.cardGroup.popCard(c)
		if (this_meld[1]>0) & (c.color in ['s','c']):
		    self.cardGroup.popCard(c)
                if c.rotated==0:
		    if DEBUGGER: print "rotating",c.color,c.value
		    c.turn()

	    if self.images:
		c.rect.x = self.curlocxy[coords][0] + counts[whichGroup]*cur_offset[0]
		c.rect.y = self.curlocxy[coords][1] + counts[whichGroup]*cur_offset[1]
		
	self.selectionCards = []
        self.selectedCards = []
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))

    def stageLayout(self):

	if self.invisible:
	    return

        toSort =  range(3,16)
        offsets = [[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10],[0,10]]
        counts = [0]*len(toSort)
        for c in self.cardGroup.cards:

            if c.location in toSort:
                whichGroup = toSort.index(c.location)
                counts[whichGroup] += 1
                coords = self.LOCATIONS.index(c.location)
		if self.images:
		    c.rect.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0]
		    c.rect.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1]
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))

    def pileLayout(self):

        toSort = [0,1]
        offsets = [[0,0],[0,0]]
        counts = [0]*len(toSort)
	pile_count = 0
        for c in self.cardGroup.cards:
            if c.location in toSort: 
                whichGroup = toSort.index(c.location)
                counts[whichGroup] += 1
                coords = self.LOCATIONS.index(c.location)
		if self.images:
		    c.rect.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0]
		    c.rect.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1]
		if (c.location == 1):
		    pile_count += 1
		    if (c.side==0):
			c.flip()
		    if (c.rotated == 0) & (c.cancolor==0):
			if (pile_count>1) | (self.turnedWild==False):
			    if DEBUGGER: print "rotating",c.color,c.value
			    c.turn()
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))

    def redThreeLayout(self):

        toSort = [1000,2000]
        offsets = [[10,0],[10,0]]
        counts = [0]*len(toSort)
        for c in self.cardGroup.cards:
            if c.location in toSort:
                whichGroup = toSort.index(c.location)
                counts[whichGroup] += 1
                coords = self.LOCATIONS.index(c.location)
		if self.images:
		    c.rect.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0]
		    c.rect.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1]
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))

    def locationsUpdate(self,res):
	"""
	Change the coordinates of game objects based on the current window size. Called at the start of the round and whenever the window is resized.
	"""
	if self.images:
	    temp = []
	    for i in range(len(self.LOCATIONSXY)):
		temp.append([self.LOCATIONSXY[i][0],self.LOCATIONSXY[i][1]])

	    resx = float(res[0])
	    resy = float(res[1])
	    scalex = float(1024)
	    scaley = float(768)
	    for i in range(len(self.curlocxy)):
		defaultx = float(temp[i][0])
		defaulty = float(temp[i][1])
		self.curlocxy[i][0] = int(defaultx*(resx/scalex))
		self.curlocxy[i][1] = int(defaulty*(resy/scaley))
	    temp = []
	    for i in range(len(self.STAGEXY)):
		temp.append(self.STAGEXY[i])
	    for i in range(len(self.curstagexy)):
		self.curstagexy[0] = int(float(temp[0])*(resx/scalex))
		self.curstagexy[1] = int(float(temp[1])*(resy/scaley))
		self.curstagexy[2] = int(float(temp[2])*(resx/scalex))
		self.curstagexy[3] = int(float(temp[3])*(resy/scaley))
	    temp = self.SCOREX[0]
	    self.curscorex = int(float(temp)*(resx/scalex))
	    temp = self.CHATX[0]
	    self.curchatx = int(float(temp)*(resx/scalex))
        self.handLayout()
        self.meldLayout()
        self.pileLayout()
        self.redThreeLayout()
        self.stageLayout()
 
############################
#History and selection
#############################
       
    def clearHistory(self):
        self.history = []

    def pushHistory(self,desc):
        #print "Pushing: %s" % desc
        while len(self.history) > self.MAX_HISTORY:
            self.history.pop(0)
        
        # store get the z-order
        cards = self.cardGroup.cards[:]

        # store card info
        cardinfo = []
        for c in cards:
            info = []
            info.append(c.side)
            info.append(c.child)
            info.append(c.parent)
            info.append(c.selected)
            info.append(c.value)
            info.append(c.color)
            cardinfo.append(info)
       
        self.history.append([cards,cardinfo,desc])
 
    def popHistory(self):
        if not len(self.history):
            return
 
        #print "Popping: %s" % hi[4]
        
        cards = hi[0]

        i = 0
        for ci in hi[1]:
            cards[i].setSide(ci[0])
            cards[i].rect.topleft = ci[1]
            cards[i].child = ci[2]
            cards[i].parent = ci[3]
            cards[i].selected = ci[4]  
            cards[i].color = ci[5]
            cards[i].value = ci[6]
            i+=1
            
        self.cardGroup.cards = cards   
        self.selectionRect = hi[2]   
        self.selectionCards = hi[3]        
                   
    def updateSelectionRect(self):
        r = None
        for c in self.selectionCards:
            if not r:
                r = pygame.Rect(c.rect)
            else:
                r.union_ip(c.rect)        
        r.x-=3
        r.y-=3
        r.width+=6
        r.height+=6
                
        self.selectionRect = r                          
        
    def sortSelection(self):
        if (len(self.selectedCards) > 0):
	    if self.images:
		rectbuf = []
		for c in self.selectedCards:
		    rectbuf.append(pygame.Rect(c.rect))

	    self.selectedCards.sort(key=lambda obj: obj.value)            
            self.selectedCards.sort(key=lambda obj: obj.color)
	    self.selectedCards.sort(key=lambda obj: obj.canvalue)            
            self.selectedCards.sort(key=lambda obj: obj.cancolor)

	    if self.images:
		for i in range(len(rectbuf)):
		    self.selectedCards[i].rect = rectbuf[i]
      
            self.cardGroup.popCards(self.selectedCards)                            

############################
#Staging and melding
#############################

    def cardsInStage(self):
	"""
	Return the number of staged cards.
	"""
	result = 0
	for c in self.cardGroup.cards:
	    if c.location in range(3,16):
		result += 1
	return result
 
    def stagedCards(self):
	"""
	Return whether there are staged cards.
	"""
        result = False
        for c in self.cardGroup.cards:
	    if c.location in range(3,16):
	       result = True
	return result
        
    def clearStage(self):
	for c in self.cardGroup.cards:
	    if c.location in range(4,16):
	        c.location = 100*(self.turn+1)
	self.handLayout()
	return True

    def stageSelection(self):
        numcards = len(self.selectedCards)
        if (numcards==(self.cardsInHand()-self.cardsInStage())):
            return False
        cvals = self.cardsInSet()
        clocs = self.cardLocations()
        tvals = self.cardsOnTable()
        if (numcards>0) & (clocs==[(self.turn+1)*100]):
            cval = self.selectedCards[0].cancolor
            cloc = self.selectedCards[0].location
            team = self.selectedCards[0].location % 200
            if len(cvals)>1:
                sameval = False
            else:
                sameval = True

            if cval == 0:
                cval = 15
	    #black 3's can't be staged--you have to meld them directly at the end of the round.
            if -1 in cvals:
                return False
       
            #New meld, all natural
            elif sameval & (cval not in tvals) & (numcards>2):
                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location = cval
                self.pushHistory("Staged cards")
                self.selectedCards = []
            #Add to existing meld, all natural
            elif sameval & (cval in tvals):
                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location = cval     
                self.pushHistory("Staged cards")
                self.selectedCards = []
            #New Meld, mix of wilds and naturals
            elif ((not sameval) & (self.cardDirtyMeldOK() != 99) & (self.cardDirtyMeldOK() not in tvals) & (numcards > 2)):

                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location = self.cardDirtyMeldOK()
                self.pushHistory("Staged cards")
                self.selectedCards = []
            #Add to existing meld, mix of wilds and naturals
            elif ((not sameval) & (self.cardDirtyMeldOK() in tvals)):
                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location = self.cardDirtyMeldOK()
                self.pushHistory("Staged cards")
                self.selectedCards = []        
	    if not self.invisible:
		self.stageLayout()
            return True
        else:
            return False

    def meldWild(self,target):
	  if len(self.selectedCards) != 1:
	      return False
	  if (self.selectedCards[0].cancolor != 0) or (self.turnstart == False):
	      return False
	  meld_status = self.numMelded(target,self.curTeam())
	  if meld_status[0]>0:
	      if (meld_status[1] < (meld_status[0]/2)) | (meld_status[0]==meld_status[1]):
		  self.lastMelded = []
		  self.selectedCards[0].location = 100*self.curTeam() + target
		  self.lastMelded.append(self.selectedCards[0])
                  self.selectedCards = []	  
                  self.meldLayout()
                  return True
              else:
                  self.handLayout()
                  return False
          else:
              self.handLayout()
              return False

    def meldStage(self):
	 for c in self.cardGroup.cards:
	    if c.location in range(3,16):
		team = self.turn
		c.location += 100*(1 + (self.turn % 2))
		self.lastMelded.append(c)
	 self.meldLayout()
	    
    def meldSelection(self):
        if self.turnstart & self.stagedCards():
	    if not self.hasMelded():
		points = 0
		for c in self.cardGroup.cards:
		    if c.location in range(4,16):
			points += c.canvalue
	    else:
		points = 1000
	    if (points >= self.pointsToGoIn()) & (self.cardsInStage() < self.cardsInHand()):
		self.lastMelded = []
		self.meldStage()
                return True
        numcards = len(self.selectedCards)
	if self.cardsInHand() == len(self.selectedCards):
	    return False
        cvals = self.cardsInSet()
        clocs = self.cardLocations()
        tvals = self.cardsOnTable()
	if not self.hasMelded():
	    points = 0
	    for c in self.selectedCards:
		points += c.canvalue
	else:
	    points = 1000
        if self.turnstart & (numcards>0) & (points >= self.pointsToGoIn()):
            cval = self.selectedCards[0].cancolor
            cloc = self.selectedCards[0].location
            team = self.selectedCards[0].location % 200
            if len(cvals)>1:
                sameval = False
            else:
                sameval = True
            if clocs != [(self.turn+1)*100]:
                sameteam = False
            else:
                sameteam = True

            if clocs[0] > 200:
                toMeld = -200
            else:
                toMeld = 0

	    #Allow melding black 3's only if it's the last meld of the hand
            if -1 in cvals:
                if len(cvals)>1:
                    return False
                elif self.cardsInHand() > (len(self.selectedCards)+1):
                    return False
                elif not self.hasCanasta():
                    return False
                else:
                    for c in self.cardGroup.cards:
                        if c.location == (self.turn+1)*100:
                            if c.cancolor == -1:
                                c.location = self.curTeam()*100 + 3
                            else:
                                c.location = 1
                    self.roundOver = True
		    return True

            #New meld, all natural/all wild
            elif sameval & sameteam & (cval not in tvals) & (numcards>2):
		self.lastMelded = []
		if cval == 0:
		  cval = 15
                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location += (toMeld + cval)
		    self.lastMelded.append(self.selectedCards[i])
                self.pushHistory("Meld cards")
                self.selectedCards = []
		self.meldLayout()
		return True
            #Add to existing meld, all natural
            elif sameval & sameteam & (cval in tvals):
		self.lastMelded = []
                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location += (toMeld + cval)     
		    self.lastMelded.append(self.selectedCards[i])
                self.pushHistory("Meld cards")
                self.selectedCards = []
		self.meldLayout()
		return True
            #New Meld, mix of wilds and naturals
            elif ((not sameval) & sameteam & (self.cardDirtyMeldOK() != 99) & (self.cardDirtyMeldOK() not in tvals) & (numcards > 2)):
		self.lastMelded = []

                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location += (toMeld + self.cardDirtyMeldOK())
		    self.lastMelded.append(self.selectedCards[i])
                self.pushHistory("Meld cards")
                self.selectedCards = []
		self.meldLayout()
		return True
            #Add to existing meld, mix of wilds and naturals
            elif ((not sameval) & sameteam & (self.cardDirtyMeldOK() in tvals)):
		self.lastMelded = []
                loc = self.cardDirtyMeldOK()
                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location += (toMeld + loc)  
		    self.lastMelded.append(self.selectedCards[i])
                self.pushHistory("Meld cards")
                self.selectedCards = []
		self.meldLayout()
		return True
	    else:
		return False
        else:
            return False

############################
#Drawing, discarding and pile-picking
#############################

    def DrawCard(self):
        if not self.turnstart:
	    done = False
	    while not done:
		c = None
		for c_iter in self.cardGroup.cards:
		    if (c_iter.order == self.idx) & (c==None):
			c = c_iter
		if c.cancolor==100:
		    c.flip()
		    c.location = 1000*self.curTeam()
		    self.redThreeLayout()
		if c.cancolor != 100:
		    if not self.invisible:
			c.flip()
		    c.location = 100*(self.turn+1)
		    self.turnstart = True
		    done = True
		self.pushHistory("Draw a card")
		self.idx-=1
            self.handLayout()
            return True
        else:
            return False

    def DiscardCard(self):
       if (self.cardsInHand()==1) & ((not self.hasCanasta()) | (not self.let_go_out)) :
           return False
       if self.turnstart & (len(self.selectedCards) == 1):
           if self.selectedCards[0].location == 100*(self.turn+1):
               self.selectedCards[0].location = 1
	       if self.selectedCards[0].cancolor==0:
		   self.frozen = True
	       self.topPile = self.selectedCards[0].cancolor
	       self.topPileV = self.selectedCards[0].canvalue
	       self.newTop()
               if self.cardsInHand()==0:
                   self.roundOver = True
               else:
                   self.nextTurn()
               self.pushHistory("Discard a card")
	       self.pileLayout()
               if self.idx<0:
                   self.roundOver=True
               return True
           else:
               return False
       else:
           return False

    def passTurn(self):
	"""
	Pass without discarding. Legal only if player has exactly one card.
	"""
        if self.cardsInHand() == 1:
            self.nextTurn()
            self.pushHistory("Pass turn")    
            if self.idx==0:
                self.roundOver=True
            return True
        else:
            return False

    def newTop(self):
	"""
	Marks the selected card as the top of the discard pile
	"""
	self.selectedCards[0].temp = 1
	for c in self.cardGroup.cards:
	    c.isTop = False
	for c in self.cardGroup.cards:
	    if c.temp == 1:
		c.isTop = True
	for c in self.cardGroup.cards:
	    c.temp = 0
	
   def canPickItUp(self):
	"""
	Can the current player pick up the pile given the current selected/staged cards and the state of the round? Returns True or False.
	"""
        result = False
	stage_cols = []
	select_cols = []
	stage_points = 0
	select_points = 0
 	select_topmatch = 0
	select_wild = 0
	select_other = 0

	#Get value of staged cards
        if self.stagedCards():
	    for c in self.cardGroup.cards:
		if c.location in range(4,16):
		    stage_cols.append(c.cancolor)
		    stage_points += c.canvalue

	#Get value of selected cards

	if len(self.selectedCards)>0:
	    for i in range(len(self.selectedCards)):
		select_cols.append(self.selectedCards[i].cancolor)
		select_points += self.selectedCards[i].canvalue
		if self.selectedCards[i].cancolor == self.topPile:
		    select_topmatch += 1
		elif self.selectedCards[i].cancolor == 0:
		    select_wild += 1
		else:
		    select_other += 1

	if self.counttop:
	    top_points = self.topPileV
	else:
	    top_points = 0

	#If the top of the pile matches something in the stage but nothing in
	#selection, OK to pick up (check for points if this is the first meld)
	if (self.topPile in stage_cols) & (self.topPile not in select_cols):
	    if (self.hasMelded() or (top_points + stage_points >= self.pointsToGoIn())):
		result = True	

	#If nothing in the stage matches but there are matches in the selection, OK to pick up
	if (self.topPile not in stage_cols) & (select_topmatch >= 1) & (select_wild <= select_topmatch) & (select_other==0) & (len(select_cols)>=2):
	    if (self.hasMelded() or ((top_points + stage_points + select_points) >= self.pointsToGoIn())):
		result = True	

	#Disallow wild cards if the pile is frozen
	if self.frozen & (select_wild>0):
	    result = False
	#If top of pile matches a meld and it's not frozen, OK to pick up
	if ((self.numMelded(self.topPile,self.curTeam())[0]>0) & (not self.frozen)):
	    result = True
	
	#Disallow if if picking up the pile would leave player with no cards in their hand.
	if (self.cardsInStage() + len(self.selectedCards)) == self.cardsInHand():
	    result = False

	return result

    def PickPile(self):
	"""
	Check if it is legal to pick up the pile. If so, transfer all pile cards to the current player's hadn.
	"""
        if (self.topPile not in [-1,0,100]) & self.canPickItUp():
	    self.turnedWild = False
	    #Assign pile cards to current hand, and meld the top card
	    psize = self.pileSize()
	    self.lastMelded = []
            for c in self.cardGroup.cards:
                if c.rotated==1:
		    if DEBUGGER: print "de-rotating",c.value,c.color
                    c.turn()
                if c.location == 1:
		    if c.cancolor==100:
			c.location = 1000*self.curTeam()
		    else:
			c.location = 100*(self.turn+1)
			if self.invisible:
			    c.flip()
		if c.isTop:
		    c.location = 100*(self.curTeam()) + c.cancolor
		    c.isTop = False
		    self.lastMelded.append(c)
	    #Meld any selected cards, then meld the stage
	    for c in self.selectedCards:
		c.location = 100*(self.curTeam()) + self.topPile
		self.lastMelded.append(c)
	    self.meldStage()
            self.pushHistory("Pick up pile")
            self.turnstart = True
	    self.frozen = False
	    self.topPile = -1
	    self.meldLayout()
            self.handLayout()
	    self.redThreeLayout()
            return True
        else:
            return False
 
    def nextTurn(self):
	"""
	Pass play to the next position.
	"""
	self.clearStage()
        oldturn = self.turn
        self.turn += 1
        if self.turn == 4:
            self.turn = 0
        self.turnstart = False
	self.selectedCards = []
	self.lastMelded = []
	self.let_go_out = True
 
############################
#Scoring
#############################
    
    def cardPoints(self,team):
	"""
	Face value of all melded cards.
	"""
	result = 0
	for c in self.cardGroup.cards:
	    if (c.location > 100*team) & (c.location < 100*(team+1)):
		result += c.canvalue
	return result

    def handPoints(self,team):
	"""
	Face value of all cards in hand, evaluated at the end of the round.
	"""
	result = 0
	for c in self.cardGroup.cards:
	    if (c.location == 100*team) | (c.location == 100*(team+2)):
		result += c.canvalue
	return result

    def specialPoints(self,team,params):
	"""
	Points from canastas, red threes, and going out.
	"""
        red_canastas = 0
        black_canastas = 0
        red_threes = 0
        going_out = 0
        wc_canasta = 0
        
        meldRange = range(100*team + 3,100*team+16)
        for i in meldRange:
            meldlength = 0
            dirty = False
            for c in self.cardGroup.cards:
                if c.location == i:
                    meldlength += 1
                    if c.cancolor==0:
                        dirty = True
            if meldlength >= 7:
                if i % 100 == 15:
                    wc_canasta += 1
                if dirty:
                    black_canastas += 1
                else:
                    red_canastas += 1

        for c in self.cardGroup.cards:
            if c.location == 1000*team:
                red_threes += 1

        if red_threes == 4:
            red_threes *= 2
	    if (self.cardPoints(team)==0) & (self.red3penalty):
		red_threes *= -1

        if ((self.turn % 2) + 1 == team) & (self.idx>0):
            going_out = 1

        result = 500*red_canastas + 300*black_canastas + 100*red_threes + 100*going_out + 500*wc_canasta

        if params:
            return [red_canastas,black_canastas,red_threes,going_out,wc_canasta]
        else:
            return result
   
############################
#Command Interpreter
#############################

    def addChat(self,command):
	"""
	Chats are submitted through the interpreter like any game command, but they are passed to this method for processing.
	"""
	ccode = command.action
	arglist = command.arglist
	token = command.token

	if (len(arglist)>1):
	    who = arglist[1]
	elif token:
	    who = ""
	else:
	    who = self.turn

	if token:
	    chatline = token[0] + arglist[0] + token[0]
	else:
	    chatline = "[" + self.playernames[who] + "] " + arglist[0]

	#DEBUGGING: use the hash-bang to print variable states in the chat window.
	#This is a huge security hole, so it should be disabled for distribution.
	if (arglist[0][0:2] == "#!") & DEBUGGER:
	    try:
		chatlines = [str(eval(arglist[0][2:len(arglist[0])]))]
	    except:
		chatlines = ["no such variable!"]
	elif len(chatline)>35:
	    chatlines = [chatline[0:33]] + [chatline[33:len(chatline)]]
	else:
	    chatlines = [chatline]
	for c in chatlines:
	    try:self.chatlist.append(c)
	    except:retcode = False
	if len(self.chatlist)>10:
	    self.chatlist = self.chatlist[1:]
	return True

    def execCode(self,ccommand,invisible=True):
	"""
	All changes to the game state are made by executing command codes through this method. Codes are generated by either the human input module or the computer player, and the server determines which codes will be passed to the game engine for execution. The interpreter saves the last command and argument list that was submitted, as well as a return code indicating whether the action was successful. These are all retrieved by the status commands.
	"""
	ccode = ccommand.action
	arglist = ccommand.arglist
	token = ccommand.token

	if ccode == DEBUG:
	    self.roundOver = True
	    self.team1score = 10000
	    retcode = True

	if invisible:
	    self.invisible = True
	else:
	    self.invisible = False

	if ccode == NO_PLAY:
	    retcode = False
	elif ccode == CHAT:		
	    retcode = self.addChat(ccommand)
	elif ccode == BLOCK_OUT:
	    self.let_go_out = False
	    retcode = True
	else:
	    popsingle = 1
      
	    viewhelp = 0
	    lctrlDown = 0
	    rctrlDown = 0
	    lshiftDown = 0
	    rshiftDown = 0

	    if (len(arglist)>0):
		hand = []
		counter = 0
		for c in self.cardGroup.cards:
		    if c.location == (1+self.turn)*100:
			hand.append(c)	
		hand.sort(key=lambda obj: obj.value)  
		hand.sort(key=lambda obj: obj.color)
		hand.sort(key=lambda obj: obj.canvalue)  
		hand.sort(key=lambda obj: obj.cancolor)

		self.selectedCards = []
		counter = 0
		for c in hand:
		    counter += 1
		    if counter in arglist:
			if DEBUGGER: print ["in argument list:",c.color,c.value]
			self.selectedCards.append(c) 

	    if ccode == TO_STAGE:
		retcode = self.stageSelection()
	    elif ccode == CLEAR_STAGE:
		retcode = self.clearStage()
	    elif ccode == MELD_CARDS:
		retcode = self.meldSelection()
	    elif ccode in tlist:
		retcode = self.meldWild(ccode)
	    elif ccode == DRAW_CARD:
		retcode = self.DrawCard()
	    elif ccode == PASS_TURN:
		retcode = self.passTurn()
	    elif ccode == PICK_PILE:
		retcode = self.PickPile()
	    elif ccode == DISCARD_CARD:
		retcode = self.DiscardCard()

	if token:
	    if isinstance(token,list):
		if retcode & (len(token)==2) & (token[0]==CHAT):
		    chatcommand = CanastaCommand(CHAT,[token[1]],[])
		    self.addChat(chatcommand)


        self.lastCommand = ccode
        self.lastReturn = retcode
        self.lastArgs = arglist
        self.lastToken = token