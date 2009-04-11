# -*- coding: utf-8 -*-
import os,pygame,math
from pygame.locals import *
from CanastaObjects import *

class HumanPlayer:
    """
    The input device for human players. The client launches an instance of this module, which reads from the
    mouse and keyboard and returns commands that can be executed by the game engine.
    """

    NOTHING = 0
    DRAW_SELECTION = 1
    CARD_SELECTED = 2
    SELECTION_SELECTED = 3
    SELECTION_SPREAD_INIT = 4
    SELECTION_SPREAD = 5

    def __init__(self):
        self.popsingle = 1
        self.viewhelp = 0
        self.lctrlDown = 0
        self.rctrlDown = 0
        self.lshiftDown = 0
        self.rshiftDown = 0
	self.over_window = False
	self.mode = self.NOTHING

    def getPlay(self,g,events=None):
	"""
	Convert keyboard/mouse input into control codes that can be executed by the client process or the game interpreter. Cards that are selected on screen are converted into the argument list form used by the computer players and the command interpreter.
	"""        
        ccode = NO_PLAY
	args = []
	token = []

	if events==None: events = pygame.event.get()

	for event in events:
	    
	    if event.type == QUIT:
		ccode = QUIT_GAME
	    elif event.type == VIDEORESIZE:
		g.locationsUpdate(event.size)
		ccode = RESIZE
		args = [event.size]
	    elif g.enterchat:
		if event.type == KEYDOWN:
		    if event.key == K_RETURN:
			    ccode = CHAT
			    args = ["",g.myPos]
			    g.curchat = None
	    elif event.type == KEYDOWN:   
                                            
		if event.key == K_ESCAPE:
		    if self.viewhelp==1:
			self.viewhelp=0
		    else:
			ccode = QUIT_GAME           
		elif event.key == K_LCTRL:
		    self.lctrlDown = 1        
		elif event.key == K_RCTRL:
		    self.rctrlDown = 1        
		elif event.key == K_LSHIFT:
		    self.lshiftDown = 1        
		elif event.key == K_RSHIFT:
		    self.rshiftDown = 1   
		elif ((self.lctrlDown==1) | (self.rctrlDown==1)) & (event.key==113):
		    ccode = RESET
		elif event.key == 110 and (self.lctrlDown or self.rctrlDown):  
		    ccode = CLEAR_STAGE
		elif event.key == 109:
		    if (self.lctrlDown or self.rctrlDown):
			ccode = TO_STAGE
		    else:
			ccode = MELD_CARDS
		elif event.key in CARD_KEYS:
		    token = [tlist[CARD_KEYS.index(event.key)]]
		    ccode = MELD_CARDS
		elif event.key == 100:
		    ccode = DRAW_CARD
		elif event.key == 120:
		    ccode = DISCARD_CARD
		elif event.key == 32:
		    ccode = PASS_TURN
		elif event.key == 112:
		    ccode = PICK_PILE
		elif event.key == K_F1: 
		    if self.viewhelp == 0:
			print "entering help"
			self.viewhelp = 1
		    else:
			print "leaving help"
			self.viewhelp = 0
		    ccode = NO_PLAY
		elif event.key == K_F10:
		    g.handLayout()
		    g.meldLayout()
		    g.pileLayout()
		    g.redThreeLayout()
		    g.selectionRect = pygame.Rect((0,0,0,0))
		    g.selectionCards = []
		elif event.key == K_F11:
		    if DEBUGGER:
			ccode = DEBUG
		elif event.key == K_F12:
		    if DEBUGGER:
			g.debugFunc()
		elif event.key == K_LEFT:
		    if len(g.selectionCards):
			g.pushHistory("AlignLeft")
			left = g.selectionCards[0].rect.left
			for c in g.selectionCards:
			    if c.rect.left<left:
				left = c.rect.left
			for c in g.selectionCards:
			    c.rect.left = left
			g.updateSelectionRect()
		elif event.key == K_RIGHT:
		    if len(g.selectionCards):
			g.pushHistory("AlignRight")
			right = g.selectionCards[0].rect.right
			for c in g.selectionCards:
			    if c.rect.right>right:
				right = c.rect.right
			for c in g.selectionCards:
			    c.rect.right = right
			g.updateSelectionRect()
		elif event.key == K_UP:
		    if len(g.selectionCards):
			g.pushHistory("AlignUp")
			top = g.selectionCards[0].rect.top
			for c in g.selectionCards:
			    if c.rect.top<top:
				top = c.rect.top
			for c in g.selectionCards:
				c.rect.top = top
			g.updateSelectionRect()
		elif event.key == K_DOWN:
		    if len(g.selectionCards):
			g.pushHistory("AlignDown")
			bottom = g.selectionCards[0].rect.bottom
			for c in g.selectionCards:
			    if c.rect.bottom>bottom:
				bottom = c.rect.bottom
			for c in g.selectionCards:
			    c.rect.bottom = bottom
			g.updateSelectionRect()
	    elif event.type == KEYUP:          
		if event.key == K_LCTRL:
		    self.lctrlDown = 0        
		elif event.key == K_RCTRL:
		    self.rctrlDown = 0        
		elif event.key == K_LSHIFT:
		    self.lshiftDown = 0        
		elif event.key == K_RSHIFT:
		    self.rshiftDown = 0        
		    
	    elif (event.type == MOUSEBUTTONDOWN) and (not self.over_window):
		#if (event.pos[0]>g.curchatx) & (event.pos[1]>g.CHATX[1]) & (event.pos[1]<g.CHATX[1] + 130):
		 #   g.enterchat=True
		#else:
		#    g.enterchat=False
		#   self.mode = self.NOTHING

		area_locs = g.cardGroup.getCardOn(event.pos[0],event.pos[1])
		if ((self.mode == self.DRAW_SELECTION) | (self.mode == self.SELECTION_SELECTED)) & (len(area_locs)):
		    if area_locs[0] == [1] and (not g.turnstart):
			ccode = PICK_PILE
		    elif area_locs[0] == [1] and g.turnstart:
			ccode = PASS_TURN
		    elif area_locs[0] == g.partnerPos:
			ccode = GO_OUT
		elif (self.mode==self.NOTHING) & (event.pos[0] < (g.curstagexy[0]+g.curstagexy[2])) & (event.pos[1] > (g.curstagexy[1])) & (event.button==3):
		    ccode = CLEAR_STAGE  
		elif self.mode == self.NOTHING and (event.button == 1):      
		    #Check if we are inside selection.
		    if g.selectionRect.width > 0 and g.selectionRect.height > 0:
			if g.selectionRect.collidepoint(event.pos[0],event.pos[1]):
			    if self.lshiftDown or self.rshiftDown:
			    
				if len(g.selectionCards) >= 2:
				    g.pushHistory("Collecting/spreading selection")

				    cx = g.selectionCards[0].rect.centerx
				    cy = g.selectionCards[0].rect.centery
				    for c in g.selectionCards:
					c.rect.centerx = cx
					c.rect.centery = cy
				    g.updateSelectionRect()
				
				    pygame.mouse.set_pos((cx,cy))
				    self.mode = self.SELECTION_SPREAD_INIT
			    else:
				g.pushHistory("Pop/flip selection")
				self.mode = self.SELECTION_SELECTED
			elif not area_locs:
				g.selectionRect = pygame.Rect((0,0,0,0))
				g.selectionCards = []

		    if self.mode == self.NOTHING:     
			if (not len(area_locs)) & len(g.selectionCards):
			    g.pushHistory("Drop selection cards")
			    g.cardGroup.popCards(g.selectionCards)                            
			    g.cardGroup.dropCards(g.selectionCards)
			    g.selectionCards = []
			    g.selectionRect.size=(0,0)
			elif len(area_locs)>0:
			    if area_locs[0] == 0:
				ccode = DRAW_CARD
			    elif (area_locs[0] == 1) & (not g.turnstart):
				ccode = PICK_PILE
			    elif (area_locs[0] == 1) & (g.turnstart):
				ccode = PASS_TURN
			    elif area_locs[0] in range(g.curTeam() + 3,g.curTeam()+16):
				ccode = MELD_CARDS
			    elif area_locs[0]==g.partnerPos:
				ccode = GO_OUT
			    else:
				g.pushHistory("Drop selection cards")
				g.cardGroup.popCards(g.selectionCards)                            
				g.cardGroup.dropCards(g.selectionCards)
				g.selectionCards = []
				g.selectionRect.size=(0,0)                   
		    #Check if any card is selected.
		    if self.mode == self.NOTHING:                            
			pop = self.popsingle
			if event.button == 2:
			    self.popsingle = 1
			g.pushHistory("Pop/flip selected card")
			if len(area_locs)>0:
			    if (area_locs[0] not in [0,1]):
				g.selectedCard = g.cardGroup.getCard(event.pos[0],event.pos[1],self.popsingle)
			    else:
				g.selectedCard = None
			else:
			    g.selectedCard = None
			if event.button == 2:
			    self.popsingle = pop
			if g.selectedCard:                                                               
			    self.mode = self.CARD_SELECTED                  
			else:
			    g.history.pop()
		    #Init a new selection rectangle.
		    if self.mode == self.NOTHING:                                 
			g.selectionStart = (event.pos[0],event.pos[1])
			self.mode = self.DRAW_SELECTION
		
		elif self.mode == self.NOTHING and (event.button==3):  
		    if g.curState().turnState == PRE_DRAW:
			if (self.lctrlDown or self.rctrlDown):
			    ccode = PICK_PILE
		    elif g.curState().turnState == POST_DRAW:
			if (self.lctrlDown or self.rctrlDown):
			    ccode = DISCARD_CARD
			else:
			    ccode = MELD_CARDS
			    
	    elif (event.type == MOUSEBUTTONUP) & (not self.over_window):
		    area_locs = g.cardGroup.getCardOn(event.pos[0],event.pos[1])
		    if self.mode == self.SELECTION_SELECTED:

			if len(area_locs)>0:
			    if area_locs[0] == [1] and not g.turnstart:
				ccode = PICK_PILE
			    elif area_locs[0] == [1] and g.turnstart:
				ccode = PASS_TURN
			    elif area_locs[0]==g.partnerPos:
				ccode = GO_OUT
			if (event.pos[0] < (g.curstagexy[0]+g.curstagexy[2])) & (event.pos[1] > (g.curstagexy[1])):
			    if event.button==1:
				ccode = TO_STAGE
			else:
			    for i in range((g.turn+1)*100 + 3,(g.turn + 1)*100 + 16):
				if i in area_locs:
				    if g.selectedCard != None:
					if g.selectedCard.cancolor==0:
					    ccode = MELD_CARDS
					    token = [area_locs[1] % 100]
				    else:
					ccode = MELD_CARDS
			    
			self.mode = self.NOTHING

		    elif self.mode == self.SELECTION_SPREAD:
			self.mode = self.NOTHING

		    elif self.mode == self.SELECTION_SPREAD_INIT:
			self.mode = self.NOTHING
	    
		    #Make plays by dragging and dropping cards
		    elif self.mode == self.CARD_SELECTED:
			if (g.turn+1)*100 in area_locs:
			    #Discard
			    if (1 in area_locs) | ((event.pos[0] in range(g.curlocxy[1][0]-10,g.curlocxy[1][0]+50))  & (event.pos[1] in range(g.curlocxy[1][1],g.curlocxy[1][1]+100))):
				ccode = DISCARD_CARD
			    #meld
			    elif (event.pos[0] < (g.curstagexy[0]+g.curstagexy[2])) & (event.pos[1] > (g.curstagexy[1])):
				if event.button==1:
				    ccode = TO_STAGE
			    for i in range((g.curTeam())*100 + 3,(g.curTeam())*100 + 16):
				if i in area_locs:
				    if g.selectedCard.cancolor==0:
					token = [area_locs[1] % 100]
					ccode = MELD_CARDS
				    else:
					ccode = MELD_CARDS
			    
			elif len(area_locs)>0:
			    if area_locs[0] == 0:
				ccode = DRAW_CARD
			elif len(area_locs)>0:
			    if area_locs[0] == 1:
				if (not g.turnstart):
				    ccode = PICK_PILE
				else:
				    ccode = PASS_TURN

			    elif area_locs[0] == g.partnerPos:
				ccode = GO_OUT

			    g.cardGroup.dropCard(g.selectedCard)
			    g.selectedCard = None 
			self.mode = self.NOTHING
			
		    elif self.mode == self.DRAW_SELECTION:
			#see if we have selected any cards
			if g.selectionRect.width > 0 and g.selectionRect.height > 0:
			    g.pushHistory("Select cards")
			    g.selectionRect,g.selectionCards = g.cardGroup.getCards(g.selectionRect)
			    if not len(g.selectionCards):
				g.history.pop()
			elif (event.pos[0] < (g.curstagexy[0]+g.curstagexy[2])) & (event.pos[1] > (g.curstagexy[1])):
			    ccode = MELD_CARDS
			elif (event.pos[0] > g.curscorex) & (event.pos[0]<(g.curscorex+274)) & (event.pos[1]<40):
			    g.handLayout()
			    g.meldLayout()
			    g.pileLayout()
			    g.redThreeLayout()
			    g.stageLayout()
			else:
			    area_locs = g.cardGroup.getCardOn(event.pos[0],event.pos[1])
			    if len(area_locs)>0:
				if area_locs[0] == 1:
				    if not g.turnstart:
					ccode = PICK_PILE
				    else:
					ccode = PASS_TURN
				elif area_locs[0] == g.partnerPos:
				    ccode = GO_OUT
			self.mode = self.NOTHING
			
	    elif (event.type == MOUSEMOTION):
		area_locs = g.cardGroup.getCardOn(event.pos[0],event.pos[1])
		if event.buttons[0] or event.buttons[1] or event.buttons[2]:
		    if self.mode == self.SELECTION_SELECTED:
			#Handle the drag of a selection rectangle.
			if len(g.selectionCards):
			    g.selectionRect.topleft = (g.selectionRect.x+event.rel[0],g.selectionRect.y+event.rel[1])
			    for c in g.selectionCards:
				c.move(event.rel[0],event.rel[1]);

		    elif (self.mode == self.SELECTION_SPREAD_INIT)  &  (not self.over_window):
			self.mode = self.SELECTION_SPREAD

		    elif self.mode == self.SELECTION_SPREAD:
			#Handle the spread of a selection rectangle.
			l = len(g.selectionCards)
			if l>=2:          
			
			    c = g.selectionCards[l-1]
			    fc = g.selectionCards[0]
			
			    dx = event.pos[0]-fc.rect.centerx
			    dy = event.pos[1]-fc.rect.centery                                                      
			    
			    if abs(dx) > abs(dy):
				cnt = 0                       
				d = float(dx)/float(l-1)
				for mc in g.selectionCards:
				    mc.rect.centery = fc.rect.centery
				    mc.rect.centerx = fc.rect.centerx+int(d*cnt)
				    cnt += 1
				c.rect.centerx = event.pos[0]
				c.rect.centery = fc.rect.centery
			    else:
				cnt = 0 
				d = float(dy)/float(l-1)
				for mc in g.selectionCards:
				    mc.rect.centerx = fc.rect.centerx
				    mc.rect.centery = fc.rect.centery+int(d*cnt)
				    cnt += 1
				c.rect.centery = event.pos[1]
				c.rect.centerx = fc.rect.centerx

			    r = pygame.Rect(c.rect)
			    r.union_ip(g.selectionCards[0].rect)        
			    r.x-=3
			    r.y-=3
			    r.width+=6
			    r.height+=6
			    g.selectionRect = r
	      
		    elif self.mode == self.CARD_SELECTED:
			#Handle the drag of a selected card.
			g.selectedCard.move(event.rel[0],event.rel[1]);
		    
		    elif self.mode == self.DRAW_SELECTION: 
			#Handle the selection rectangle
			#g.selectionRect.size=(event.pos[0]-g.selectionRect.x,event.pos[1]-g.selectionRect.y)

			if event.pos[0] <= g.selectionStart[0]:
			    g.selectionRect.x = g.selectionStart[0]-(g.selectionStart[0]-event.pos[0])
			    g.selectionRect.width = g.selectionStart[0]-event.pos[0]
			else:                            
			    g.selectionRect.x=g.selectionStart[0]
			    g.selectionRect.width=event.pos[0]-g.selectionStart[0]

			if event.pos[1] <= g.selectionStart[1]:
			    g.selectionRect.y = g.selectionStart[1]-(g.selectionStart[1]-event.pos[1])
			    g.selectionRect.height = g.selectionStart[1]-event.pos[1]
			else:                            
			    g.selectionRect.y=g.selectionStart[1]
			    g.selectionRect.height=event.pos[1]-g.selectionStart[1]
			if len(area_locs)>0:
			    if area_locs[0]==1:
				if not g.turnstart:
				    ccode = PICK_PILE
				else:
				    ccode = PASS_TURN
			    if area_locs[0]==g.partnerPos:
				ccode = GO_OUT


	count = 0

	#Pass the currently selected cards in the argument list
	if ccode not in [NO_PLAY,CHAT,RESIZE]:
	    args = []
	    if (len(g.selectionCards)<1) & (ccode in [TO_STAGE,MELD_CARDS,DRAW_CARD,DISCARD_CARD]+tlist) & (g.selectedCard != None):
		g.selectionCards = []
		g.selectionCards.append(g.selectedCard)	

	    hand = []
	    counter = 0
	    for c in g.cardGroup.cards:
		if c.location == (1+g.turn)*100:
		    hand.append(c)	
	    hand.sort(key=lambda obj: obj.value)  
	    hand.sort(key=lambda obj: obj.color)
	    hand.sort(key=lambda obj: obj.canvalue)  
	    hand.sort(key=lambda obj: obj.cancolor)
	    for c in hand:
		counter += 1
		if c in g.selectionCards:
		    args.append(counter)

	if self.viewhelp==1:
	    ccode = NO_PLAY  

        command = CanastaCommand(ccode,args,token)
        return command
