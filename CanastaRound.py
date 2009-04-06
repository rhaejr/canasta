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
	self.animating = False

    def debugFunc(self):
	if not DEBUGGER:
	    return
        print "Selected locations"
        for c in self.selectionCards:
            print [c.color,c.value,c.location,c.rotated,c.order,[c.x,c.y],[c.rect.x,c.rect.y]]
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

	self.options = options

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
        self.topPile = None
        self.roundOver = False
	self.myPosMelded = False
	self.concealed = False
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
  
	if (self.team1score < 0) & self.options.negpoints:
	    self.minmeld1 = 15
	elif self.team1score <1500:
	    self.minmeld1 = 50
	elif (self.team1score < 3000):
	    self.minmeld1 = 90
	else:
	    self.minmeld1 = 120

	if (self.team2score < 0) & self.options.negpoints:
	    self.minmeld2 = 15
	elif self.team2score <1500:
	    self.minmeld2 = 50
	elif (self.team2score < 3000):
	    self.minmeld2 = 90
	else:
	    self.minmeld2 = 120
          
        gt = self.cardGroup.getCardAt  
                
        cards = 11
        self.idx = 107
             
        for c in self.cardGroup.cards:
            c.location = 0
	    c.nofreeze = False

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
	while self.topPile in [None,0,100]:
	    c = gt(self.idx)
	    c.flip()
	    self.cardGroup.dropCard(c)
	    c.location = 1
	    self.topPile = c.cancolor
	    self.topPileV = c.canvalue
	    if (c.cancolor==0) & (not self.options.initfreeze):
		c.nofreeze = True
	    elif (c.cancolor==0) & self.options.initfreeze:
		self.frozen = True
	    if c.cancolor not in [0,100]:
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

	result = CanastaInitStatus([self.minmeld1,self.minmeld2],locations,self.frozen,self.idx,self.playernames,active)

	return result

    def readInit(self,initStatus):

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
		if (c.cancolor==0) & (not self.options.initfreeze):
		    c.nofreeze = True
		elif (c.cancolor==0) & self.options.initfreeze:
		    self.frozen = True
		    c.nofreeze = False
		else:
		    c.nofreeze = False
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

    def validMeld(self):
	"""
	Determine whether the currently selected cards can be legally melded by the current player, either by themselves or in combination with an existing meld. Does not check for the point threshold.
	"""
	status = [0,0]
	vals = []
	#Determine what naturals and wild cards are selected
	for c in self.selectedCards:
	    #Invalid if a selected card does not belong to the player
	    if c.location != 100*(self.turn + 1):
		return False
	    if c.cancolor != 0:
		status[0] += 1
		if c.cancolor not in vals: vals.append(c.cancolor)
	    else:
		status[1] += 1
	#If more than one different natural is selected, not a valid meld
	if len(vals) > 1:
	    return False
	elif (len(vals) == 0):
	    val = 15
	else:
	    val = vals[0]
	#Check for currently melded or staged cards of the same value
	for c in self.cardGroup.cards:
	    if c.location in [100*self.curTeam() + val,val]:
		if c.cancolor != 0:
		    status[0] += 1
		else:
		    status[1] += 1
	if self.options.threewilds:
	    limit = 3
	else:
	    limit = status[0] - 1
	#If the resulting meld would be at least three cards and doesn't violate the maximum meld size or the wild card limit, it's OK
	if (sum(status)>7) & (not self.options.megamelds):
	    return False
	elif (sum(status)>2) & (status[1]<=limit):
	    return True
	#Allow a wild card meld if it's legal for this game
	elif self.options.wildmeld & (status[0]==0) & (status[1]>2):
	    return True
	else:
	    return False

    def selectedNatural(self):
	"""
	Returns the natural component of selected cards, or None if there are two different naturals present.
	"""
	vals = []
	for c in self.selectedCards:
	    if c.cancolor != 0:
		if c.cancolor not in vals: vals.append(c.cancolor)
	if len(vals) == 1:
	    return vals[0]
	elif len(vals) == 0:
	    return 0
	else:
	    return None

    def canGoOut(self):
	"""
	Reports whether the current player can legally go out.
	"""
	if not self.turnstart:
	    return False
	elif not self.hasCanasta():
	    return False
	elif self.cardsInHand(include_stage=False)>1:
	    return False
	else:
	    return True

    def goConcealed(self):
	"""
	Reports whether the current player can legally go out concealed.
	"""
	if self.cardsInHand(include_stage=False)>1:
	    return False
	elif self.myPosMelded:
	    return False
	else:
	    points = 0
	    vals = [0]*15
	    for c in self.cardGroup.cards:
		if c.location in TLIST:
		    vals[c.location] += 1
		    points += c.canvalue
	    print vals
	    if (points<self.pointsToGoIn()) & (not self.hasMelded()) & (not self.options.concealedfree):
		return False
	    elif max(vals)==7:
		return True
	    elif (max(vals)>7) & self.options.megamelds:
		return True
	    else:
		return False

    def guessWildTarget(self):
	"""
	Picks a meld to add a wild card to. Will select a meld of wilds if it exists, otherwise the largest meld that isn't already maxed out on wild cards. Returns 0 if there is nowhere to meld a wild.
	"""
	if self.numMelded(0,self.curTeam())[1]>0:
	    return 15
	result = 0
	vals = [0]*16
	locs = range(100*self.curTeam()+3,100*self.curTeam()+16)
	for c in self.cardGroup.cards:
	    if c.location in locs:
		vals[c.location % 100] += 1
	for i in range(3,7):
	    try:
		which_meld = vals.index(i)
		cards = self.numMelded(which_meld,self.curTeam())
		if (cards[1] < (cards[0] / 2)) & (result == 0):
		    result = which_meld
	    except:
		pass
	return result

############################
#Layout functions
#############################

    def animate(self):
	rate = self.options.animation
	did_something = False
	for c in self.cardGroup.cards:
	    if c.x != c.rect.x:
		did_something = True
		if abs(c.x-c.rect.x)<rate:
		    c.rect.x = c.x
		elif c.x<c.rect.x:
		    c.rect.x -= rate
		elif c.x>c.rect.x:
		    c.rect.x += rate
	    if c.y != c.rect.y:
		did_something = True
		if abs(c.y-c.rect.y)<rate:
		    c.rect.y = c.y
		elif c.y<c.rect.y:
		    c.rect.y -= rate
		elif c.y>c.rect.y:
		    c.rect.y += rate
	if not did_something:
	    self.animating = False

    def updateRect(self):
	for c in self.cardGroup.cards:
	    c.x = c.rect.x
	    c.y = c.rect.y

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
			c.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0] + row[whichGroup]*offsets2[whichGroup][0]
			c.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1] + row[whichGroup]*offsets2[whichGroup][1]
                    self.selectedCards.append(c)

		    if counts[whichGroup]>15:
			counts[whichGroup]=0
			row[whichGroup]+=1
            self.sortSelection()
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))
        self.selectedCards = []
        self.selectionCards = []
	if self.images:
	    self.animating = True
	    self.animate()

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
		c.x = self.curlocxy[coords][0] + counts[whichGroup]*cur_offset[0]
		c.y = self.curlocxy[coords][1] + counts[whichGroup]*cur_offset[1]
	self.selectionCards = []
        self.selectedCards = []
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))
	if self.images:
	    self.animating = True
	    self.animate()

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
		    c.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0]
		    c.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1]
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))
	if self.images:
	    self.animating = True
	    self.animate()

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
		    c.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0]
		    c.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1]
		if (c.location == 1):
		    pile_count += 1
		    if (c.side==0):
			c.flip()
		    if (c.rotated == 0) & (c.cancolor==0) & (not c.nofreeze):
			c.turn()
		    if c.nofreeze & self.images:
			c.rect.x += 20
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))
	if self.images:
	    self.animating = True
	    self.animate()

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
		    c.x = self.curlocxy[coords][0] + counts[whichGroup]*offsets[whichGroup][0]
		    c.y = self.curlocxy[coords][1] + counts[whichGroup]*offsets[whichGroup][1]
	if self.images & (not self.invisible):
	    self.selectionRect = pygame.Rect((0,0,0,0))
	if self.images:
	    self.animating = True
	    self.animate()

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
        
    def sortSelection(self,pop=True):
        if (len(self.selectedCards) > 0):

	    self.selectedCards.sort(key=lambda obj: obj.value)            
            self.selectedCards.sort(key=lambda obj: obj.color)
	    self.selectedCards.sort(key=lambda obj: obj.canvalue)            
            self.selectedCards.sort(key=lambda obj: obj.cancolor)

            if pop: 
		for c in self.selectedCards:
		    self.cardGroup.popCard(c)                            

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

    def meldWild(self,target,stage=False):
	  if len(self.selectedCards) != 1:
	      return False
	  if (self.numMelded(target,self.curTeam())[0]==7) & (not self.options.megamelds):
	      return False
	  if (self.selectedCards[0].cancolor != 0) or (self.turnstart == False):
	      return False
	  meld_status = self.numMelded(target,self.curTeam())
	  if stage:
	      location = 0
	  else:
	      location = 100*self.curTeam()
	  if meld_status[0]>0:
	      if self.options.threewilds:
		  limit = 3
	      else:
		  limit = meld_status[0]/2
	      if (meld_status[1] < limit) | (meld_status[0]==meld_status[1]):
		  self.lastMelded = []
		  self.selectedCards[0].location = location + target
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
	    
    def meldSelection(self,target=None,stage=False):
	if target:
	    return self.meldWild(target,stage)
        cloc = 100*(self.turn + 1)
	#Check for the point threshold if applicable
	if (not stage) & (not self.hasMelded()):
	    if self.stagedCards():
		test = range(4,16)
		cards = self.cardGroup.cards
	    else:
		cards = self.selectedCards
		test = [cloc]
	    points = 0
	    for c in cards:
		if c.location in test:
		    points += c.canvalue
	else:
	    points = 1000
	#Meld stage cards if applicable
        if (not stage) & self.turnstart & self.stagedCards():
	    if self.goConcealed() | (points >= self.pointsToGoIn()) & (self.cardsInStage() < self.cardsInHand()):
		if self.goConcealed(): self.concealed = True
		self.lastMelded = []
		self.meldStage()
		if self.concealed:
		    self.roundOver=True
                return True
	    else:
		return False
        if (not stage) & (points < self.pointsToGoIn()):
	    return False
	#Block if the play would leave player with too few cards
	if self.options.allowpass | self.hasCanasta():
	    limit = self.cardsInHand() - 1
	else:
	    limit = self.cardsInHand() - 2
	if len(self.selectedCards)>limit:
	    return False
	#If it's OK to stage/meld, set locations
        if (stage | self.turnstart) & (self.validMeld()):
            cval = self.selectedNatural()
	    if cval == 0: cval = 15

	    if stage:
		toMeld = -1*cloc
            elif cloc > 200:
                toMeld = -200
            else:
                toMeld = 0

	    #Allow melding black 3's only if it's the last meld of the hand
            if cval==-1:
                if self.cardsInHand() > (len(self.selectedCards)+1):
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

	    #Otherwise it's a normal meld, stage or meld it.
	    else:
		if not stage: self.lastMelded = []
                for i in range(len(self.selectedCards)):
                    self.selectedCards[i].location += (toMeld + cval)
		    if not stage: self.lastMelded.append(self.selectedCards[i])
		return True

        else:
            return False

############################
#Drawing, discarding and pile-picking
#############################

    def DrawCard(self):
	if self.idx<0:
	    self.roundOver=True
	    return True
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
            if self.idx<0:
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

	if self.options.counttop:
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
	if (self.frozen | self.options.freezealways | (not self.options.pilewithwild) | (self.options.gonatural & (not self.hasMelded()))) & (select_wild>0):
	    result = False
	#If top of pile matches a meld and it's not frozen, OK to pick up
	if ((self.numMelded(self.topPile,self.curTeam())[0]>0) & (not (self.frozen|self.options.freezealways)) & self.options.piletocanasta):
	    result = True
	
	#Disallow if if picking up the pile would leave player with no cards in their hand.
	if (self.cardsInStage() + len(self.selectedCards)) == self.cardsInHand():
	    result = False

	return result

    def PickPile(self):
	"""
	Check if it is legal to pick up the pile. If so, transfer all pile cards to the current player's hadn.
	"""
	if (self.idx<0) & (not self.options.runempty):
	    self.roundOver=True
	    return True
        if (self.topPile not in [-1,0,100]) & self.canPickItUp():
	    #Assign pile cards to current hand, and meld the top card
	    psize = self.pileSize()
	    self.lastMelded = []
            for c in self.cardGroup.cards:
		c.nofreeze = False
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
        super_wc = False

        meldRange = range(100*team + 3,100*team+16)
        for i in meldRange:
	    jokers = 0
            meldlength = 0
            dirty = False
            for c in self.cardGroup.cards:
                if c.location == i:
                    meldlength += 1
                    if c.cancolor==0:
                        dirty = True
			if c.canvalue==50:
			    jokers += 1
            if meldlength >= 7:
                if i % 100 == 15:
                    wc_canasta += 1
		    if jokers in [0,4]:
			super_wc = True
                if dirty:
                    black_canastas += 1
                else:
                    red_canastas += 1

        for c in self.cardGroup.cards:
            if c.location == 1000*team:
                red_threes += 1

        if red_threes == 4:
            red_threes *= 2
	    if (self.cardPoints(team)==0) & (self.options.red3penalty):
		red_threes *= -1

        if ((self.turn % 2) + 1 == team) & (self.idx>0):
            going_out = 1

	
	if super_wc:
	    wc_bonus = self.options.wildcanastabonus[0] - 500
	else:
	    wc_bonus = self.options.wildcanastabonus[1] - 500

	if self.concealed: going_out+=1

        result = 500*red_canastas + 300*black_canastas + 100*red_threes + 100*going_out + wc_bonus*wc_canasta

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

	target = None

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

	    if DEBUGGER: print "command",ccommand.action,ccommand.arglist,ccommand.token

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

	    if (ccode in [TO_STAGE,MELD_CARDS]) & (len(self.selectedCards)==1):
		if (self.selectedCards[0].cancolor==0):
		    if token:
			target = token[0]
		    else:
			target = self.guessWildTarget()
			if target==0: target = None
		    if DEBUGGER: print "Inserting the target",target

	    if ccode == TO_STAGE:
		retcode = self.meldSelection(target=target,stage=True)
		if retcode:
		    self.pushHistory("Stage cards")
		    self.selectedCards = []
		    self.stageLayout()
	    elif ccode == CLEAR_STAGE:
		retcode = self.clearStage()
	    elif ccode == MELD_CARDS:		
		retcode = self.meldSelection(target=target)
		if retcode:
		    self.pushHistory("Meld cards")
		    self.selectedCards = []
		    self.meldLayout()
		    if self.turn == self.myPos:
			self.myPosMelded = True
	    elif ccode in TLIST:
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
	    if (ccode not in TLIST):
		if isinstance(token,list):
		    if retcode & (len(token)==2) & (token[0]==CHAT):
			chatcommand = CanastaCommand(CHAT,[token[1]],[])
			self.addChat(chatcommand)


        self.lastCommand = ccommand.action
        self.lastReturn = retcode
        self.lastArgs = arglist
        self.lastToken = token