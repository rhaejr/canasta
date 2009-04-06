#! /usr/bin/python
# -*- coding: utf-8 -*-
import os, pygame,math
from pygame.locals import *
import random

from CardImages import CardImages
from CardGroup import CardGroup
from Card import Card
from HumanPlayer import HumanPlayer

import subprocess
from twisted.spread import pb, jelly
from twisted.python import log
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from PBUtil import ReconnectingPBClientFactory
from uuid import UUID,uuid4

from time import sleep
import gui
from gui import *
import defaultStyle

from CanastaRound import CanastaRound
from CanastaObjects import *

class CanastaClient(pb.Referenceable):
    """
    Handles all user input and graphical display. Connects to a server to make plays.
    All games, including the one-player game, use the client.
    """

    def __init__(self,name,options,server=False,id=str(uuid4())):
	self.name = name
	self.names = [name]
	pygame.init()
	self.menuback = pygame.image.load("./cards/titlescreen.gif").convert()
	self.screen = pygame.display.set_mode((1024,768))
	self.g = CanastaRound()
	self.p = HumanPlayer()
	self.factory = ReconnectingPBClientFactory()
	self.port = 7171
	self.rejected = False
	self.connected = False
	self.starting = False
	self.start_game = False
	self.start_match = False
	self.cancel = False
	self.started = False
	self.initialized = False
	self.server = server
	self.new_players = True	
	self.controller = False
	self.options = options
	self.shut_down = False
	self.shutting_down = False
	self.controller = False
	self.id = UUID(id)
	self.CommandQueue = []

    def callDebug(self,obj):
	if DEBUGGER: obj.callRemote("debug")

    def remote_debug(self):
	self.g.roundOver=True

    def Connect(self,obj):
	print "connection established"
	obj.callRemote("joinServer",self,self.name,str(self.id),VERSION).addCallback(self.isController)

    def failConnect(self,obj):
	if self.cancel:
	    return "cancel"
	else:
	    print "failed to connect"
	    sleep(1)
	    reactor.connectTCP("localhost",self.port, self.factory)
	    self.factory.getRootObject().addCallbacks(self.Connect,self.failConnect)

    def isController(self,obj):
	if isinstance(obj,str):
	    print obj
	    self.rejected = True
	    reactor.stop()
	else:
	    self.connected = True
	    self.controller = obj

    def getNames(self,obj):
	obj.callRemote("Names").addCallback(self.gotNames)

    def remote_updateNames(self,namelist):
	self.names = namelist
	self.new_players = True

    def gotNames(self,obj):
	self.names = obj

    def startServer(self,obj):
	self.oneRef = obj
	self.oneRef.callRemote("Start",str(self.id),self.player_positions,self.options)
	self.start_match = True

    def failStart(self,obj):
	print "failed to start"
	sleep(1)
	self.factory.getRootObject().addCallbacks(self.startServer,self.failStart)

    def notClosed(self,obj):
	print ["Server did not close correctly",obj]
	self.shut_down = True

    def isClosed(self,obj):
	print ["Server closed correctly",obj]
	self.shut_down = True

    def stopServer(self,obj):
	self.shutting_down = True
	self.oneRef = obj
	self.oneRef.callRemote("Shutdown",str(self.id)).addCallbacks(self.isClosed,self.notClosed)

    def reportReady(self,obj):
	self.oneRef = obj
	self.oneRef.callRemote("isReady",str(self.id))

    def SendCommand(self,obj):
	self.oneRef = obj
	self.oneRef.callRemote("takeCanastaCommand",str(self.id),self.lastplay)

    def clearCommand(self,obj):
	self.lastplay=CanastaCommand(NO_PLAY,[],[])

    def SendChat(self,obj):
	if DEBUGGER: print "sending chat"
	self.oneRef = obj
	self.oneRef.callRemote("takeChat",str(self.id),self.lastchat)

    def remote_initGame(self,players,human,options):
	self.g.gameStart(players,human,options)

    def remote_newGame(self):
	self.g.newGame()

    def remote_initRound(self):
	self.g.initCanasta()
	self.started = True

    def remote_readInit(self,status):
	if not self.initialized:
	    if DEBUGGER: print "client got status"
	    self.g.readInit(status)
	    self.initialized = True
	    self.screen = pygame.display.set_mode((1024,768),RESIZABLE)

    def remote_readCommand(self,command,local=False):
	"""
	Execute a command on the local game object. This function is called externally by the server.
	The client never executes game commands without receiving instruction from the server.
	"""
	if self.g.animating:
	    queued = True
	elif self.CommandQueue:
	    if local:
		queued = False
	    else:
		queued = True
	else:
	    queued = False
	print "got command",command.action
	if command.action==CHAT:
	    self.g.execCode(command)
	    return [self.g.lastCommand,self.g.lastReturn]
	if self.g.turn==self.g.myPos:
	    invis = False
	else:
	    invis = True
	if not queued:
	    print "executing it"
	    self.g.execCode(command,invisible=invis)
	    retcode = self.g.lastReturn
	    print "result was",self.g.lastReturn
	else:
	    print "queueing it"
	    self.CommandQueue.append(command)
	    retcode = True
	if (not queued) & self.g.lastReturn: 
	    if self.g.roundOver:
		team1round = self.g.cardPoints(1) + self.g.specialPoints(1,params=False) - self.g.handPoints(1)
		team2round = self.g.cardPoints(2) + self.g.specialPoints(2,params=False) - self.g.handPoints(2)

		self.g.team1score += team1round
		self.g.team2score += team2round

	self.DrawGame()
	if not queued: self.clearCommand(None)
	return [self.g.lastCommand,retcode]


    def endRound(self):
	"""
	Create the display object showing the final score in the round.
	"""
	team1round = self.g.cardPoints(1) + self.g.specialPoints(1,params=False) - self.g.handPoints(1)
	team2round = self.g.cardPoints(2) + self.g.specialPoints(2,params=False) - self.g.handPoints(2)

	font2 = pygame.font.Font("FreeSans.ttf", 20)

	team1specials = self.g.specialPoints(1,params=True)
	team2specials = self.g.specialPoints(2,params=True)

	if team1specials[2]==8:
	    team1specials[2]=4
	if team2specials[2]==8:
	    team2specials[2]=4

	if team1specials[3]==1:
	    team1out = "Went out first"
	elif team1specials[3]==2:
	    team1out = "Went out concealed"
	else:
	    team1out = ""
	
	if team2specials[3]==1:
	    team2out = "Went out first"
	elif team2specials[3]==2:
	    team2out = "Went out concealed"
	else:
	    team2out = ""

	endtext1 = ["Team 1:",
		    str(team1round)+             " points",
		    str(self.g.cardPoints(1)) +       " face value",
		    "-" + str(self.g.handPoints(1)) + " points in hand",
		    str(team1specials[0])+" red canastas",
		    str(team1specials[1])+" black canastas",
		    str(team1specials[2])+" red threes",
		    str(team1specials[4])+" wild card canastas",
		    team1out]
	endtext2 = ["Team 2:",
		    str(team2round)+             " points",
		    str(self.g.cardPoints(2)) +       " face value",
		    "-" + str(self.g.handPoints(2)) + " points in hand",
		    str(team2specials[0])+" red canastas",
		    str(team2specials[1])+" black canastas",
		    str(team2specials[2])+" red threes",
		    str(team2specials[4])+" wild card canastas",
		    team2out]

	self.g.endroundtext = pygame.Surface((490,400),1).convert()
	self.g.endroundtext.fill((0x0, 0x0, 0x0))
	self.g.endroundtext.set_alpha(200);
	self.g.endroundtextRect = self.g.endroundtext.get_rect()

	sr2 = self.screen.get_rect()
	self.g.endroundtextRect.centerx = sr2.centerx
	self.g.endroundtextRect.centery = sr2.centery

	ty = -175 + self.g.endroundtextRect.top
	rtitle = font2.render("Round "+str(self.g.round)+" complete",1,(0xff,0xff,0))
	r = rtitle.get_rect()
	r.top = ty
	r.left = -123 + self.g.endroundtextRect.left
	self.g.endroundtext.blit(rtitle,r)
	ty +=50
	for t in endtext1:
	    img = font2.render(t, 1, (0xff, 0xff, 0))
	    r = img.get_rect()
	    r.top = ty
	    r.left = -248 + self.g.endroundtextRect.left
	    ty += 25
	    if t=="  ":
		tx-=100
	    self.g.endroundtext.blit(img,r)
	ty = -125 + self.g.endroundtextRect.top
	for t in endtext2:
	    img = font2.render(t, 1, (0xff, 0xff, 0))
	    r = img.get_rect()
	    r.top = ty
	    r.left = 18 + self.g.endroundtextRect.left
	    ty += 25
	    if t=="  ":
		tx-=100
	    self.g.endroundtext.blit(img,r)

	if (self.g.team1score>5000) | (self.g.team2score>5000):
	    if self.g.team1score>self.g.team2score:
		win_string = "Team 1 is the winner!"
	    elif self.g.team1score<self.g.team2score:
		win_string = "Team 2 is the winner!"
	    elif self.g.team1score == self.g.team2score:
		win_string = "It's a tie! Bonus Round!"

	    ty += 25
	    rwin = font2.render(win_string,1,(0xff,0xff,0))
	    r = rwin.get_rect()
	    r.top = ty
	    r.left = -133 + self.g.endroundtextRect.left
	    self.g.endroundtext.blit(rwin,r)
	    pygame.display.flip()

	ty += 40
	rbottom = font2.render("Click or press Space to continue",1,(0xff,0xff,0))
	r = rbottom.get_rect()
	r.top = ty
	r.left = -173 + self.g.endroundtextRect.left
	self.g.endroundtext.blit(rbottom,r)


    def remote_goOut(self):
	"""
	Called remotely by the server when the client's partner has asked to go out.
	Waits for user input.
	"""
	self.done = False

	def OKOnClick(button):
	    self.done = True
	    self.response = True
	def cancelOnClick(button):
	    self.done = True
	    self.response = False

	defaultStyle.init(gui)
	defaultStyle.init(gui)
	desktop_main = Desktop()
	desktop = Window(position = (300,220), size = (400,200), parent = desktop_main, text = "Go Out", closeable = False, shadeable = False)
	desktop.onClose = cancelOnClick

	labelStyleCopy = gui.defaultLabelStyle.copy()

	Label(position = (100,100),size = (200,0), parent = desktop, text = 'Your partner asked: "May I go out?"', style = labelStyleCopy)

	OK_button = Button(position = (100,140), size = (50,0), parent = desktop, text = "Yes")
	cancel_button = Button(position = (200,140), size = (50,0), parent = desktop, text = "No")

	OK_button.onClick = OKOnClick
	cancel_button.onClick = cancelOnClick

	while not self.done:

	    #Handle Input Events
	    for event in gui.setEvents():
		if event.type == QUIT:
		    return
		elif event.type == KEYDOWN and event.key == K_ESCAPE:
		    return

	    self.DrawGame(flip=False)
	    desktop_main.update()
	    desktop_main.draw()
	    pygame.display.flip()

	return self.response

    def remote_endGame(self):
	"""
	Called by the server on all non-controlling clients after the controller sends the kill signal. Should send a confirmation and then kill the reactor in the next input loop.
	"""
	if DEBUGGER: print "quitting client"
	pygame.quit()
	self.shut_down = True

    def getInput(self):
	"""
	The main user input loop. Runs concurrently with Twisted's main reactor, so that the user can enter
	commands whenever they want.
	Game commands are sent to the server for execution. If valid, the server will call back to
	execute them locally.
	Chats are sent to the server through the special back channel that allows them to be distributed
	even if it's someone else's turn.
	Cards can be moved or selected at any time, but commands will not be executed unless it's the client's turn. For efficiency, the client is coded to only submit commands on its turn. For stability, however, the server is programmed to check for the turn before executing any non-chat command it receives.
	"""
	if self.cancel:
	    reactor.stop()
	if self.shut_down:
	    try:
		pygame.quit()
	    except:
		pass
	    try:
		reactor.stop()
	    except:
		pass
	elif self.shutting_down:
	    pass
	elif self.started & self.initialized:
	    #If the client isn't animating, execute any commands waiting in the queue
	    if (not self.g.animating):
		try:
		    self.remote_readCommand(self.CommandQueue.pop(0),local=True)
		except:
		    pass
	    if self.g.roundOver: 
		for event in pygame.event.get():    
		    if event.type == MOUSEBUTTONDOWN:
			self.started=False
			self.initialized=False
			def1 = self.factory.getRootObject()
			def1.addCallback(self.reportReady)
		    elif event.type == KEYDOWN:
			if event.key == 32:
			    self.started=False
			    self.initialized=False
			    def1 = self.factory.getRootObject()
			    def1.addCallback(self.reportReady)
			if event.key == K_ESCAPE:
			    return
		try:
		    self.DrawEndRound()
		except:
		    self.endRound()
	    else:
		play = self.p.getPlay(self.g)
		if play.action == QUIT_GAME:
		    def1 = self.factory.getRootObject()
		    def1.addCallbacks(self.stopServer)
		elif play.action == RESIZE:
		   self.screen = pygame.display.set_mode(play.arglist[0],RESIZABLE)
		elif play.action == CHAT:
		    self.lastchat = play
		    def1 = self.factory.getRootObject()
		    def1.addCallback(self.SendChat)		
		elif play.action != NO_PLAY:
		    if self.g.turn==self.g.myPos:
			self.lastplay = play
			def1 = self.factory.getRootObject()
			def1.addCallback(self.SendCommand)
		if self.g.animating: self.g.animate()
		self.DrawGame()
	elif (not self.start_match) & (not self.controller):
	    for event in pygame.event.get():
		if event.type == QUIT:
		    self.cancel = True
		elif event.type == KEYDOWN and event.key == K_ESCAPE:
		    self.cancel = True
	    if self.connected:
		self.DrawWait("Waiting for game to start...")
	    else:
		self.DrawWait("Connecting to the game server...")
	elif (not self.server) | self.start_match:
	    if self.start_match:
		for event in pygame.event.get():
		    if event.type == QUIT:
			self.shut_down = True
		    elif event.type == KEYDOWN and event.key == K_ESCAPE:
			self.shut_down = True
	    if self.connected:
		self.DrawWait("Waiting for game to start...")
	    else:
		self.DrawWait("Connecting to the game server...")
	else:
	    if not self.start_game:

		#Handle Input Events
		for event in pygame.event.get():
		    if event.type == QUIT:
			def1 = self.factory.getRootObject()
			def1.addCallbacks(self.stopServer)
		    elif event.type == KEYDOWN and event.key == K_ESCAPE:
			def1 = self.factory.getRootObject()
			def1.addCallbacks(self.stopServer)
		    elif event.type == KEYDOWN and event.key == 13:
			self.start_game = True
		    else:
			pass

	    elif not self.starting:
		playernames=[]
		for index, p in enumerate(self.positions):
		    playernames.append(p)

		self.player_positions = playernames
		self.factory.getRootObject().addCallback(self.startServer)
		self.starting = True
	    self.DrawAssign()

    def readyStartGame(self):
	self.start_game = True

#####################################
#Drawing routines
#####################################

    def DrawAssign(self):

	def OKOnClick(button):
	    self.start_game = True
	    self.screen = pygame.display.set_mode((1024,768),RESIZABLE)

	def assignPlayer(arg):
	    print positions
	    g = arg.parent
	    if arg.value==None:
		return
	    loc = posnames.index(arg.text)
	    if loc == 4:
		for i in range(len(positions)):
		    if positions[i]==g.name:
			positions[i]=None
		g.prior = arg
	    elif positions[loc]==None:
		for i in range(len(positions)):
		    if positions[i]==g.name:
			positions[i]=None
		positions[loc] = g.name
		g.prior = arg
	    else:
		arg.value = False
		g.prior.value = True
	    self.positions = positions

	playernames=self.names

	if self.new_players:

	    self.desktops = []

	    defaultStyle.init(gui)
	    labelStyleCopy = gui.defaultLabelStyle.copy()
	    labelStyleCopy['wordwrap'] = True

	    positions = [None]*4
	    posnames = ["Bottom","Left","Top","Right","Not Playing"]

	    for index, p in enumerate(self.names):
		if index<4:
		    def_pos = posnames[index]
		else:
		    def_pos = None

		g = Desktop()
		g.player = index

		if index==0:
		    label1 = Label(position = (125,125),size = (200,0), parent = g, text = "Players will appear here when they connect to your game.", style = labelStyleCopy)
		    label2 = Label(position = (125,145),size = (200,0), parent = g, text = "Assign them to a player position and press the start button when ready.", style = labelStyleCopy)
		    label3 = Label(position = (125,165),size = (200,0), parent = g, text = "Unfilled positions will be filled with computer players.", style = labelStyleCopy)
		label_name = Label(position = (125,200 + index*25),size = (200,0), parent = g, text = p, style = labelStyleCopy)
		g.name = p

		if index<4:
		    positions[index] = p
		g.prior = None

		for index2, pos in enumerate(posnames):
		    o = OptionBox(position = (200+index2*75,200+index*25), parent = g, text = pos)
		    try:
			if positions[index2]==p:
			    o.value = True
			    g.prior = o
		    except:
			pass
		    o.onValueChanged = assignPlayer

		self.desktops.append(g)

	    defaultStyle.init(gui)
	    desktop = Desktop()
	    labelStyleCopy = gui.defaultLabelStyle.copy()

	    OK_button = Button(position = (125,600), size = (50,0), parent = desktop, text = "Start")
	    OK_button.onClick = OKOnClick

	    self.desktops.append(desktop)

	    self.positions = positions
	    self.new_players = False

	self.screen.fill((0, 0, 255))
	pygame.draw.rect(self.screen,(0,100,255),(100,100,824,568))

	for desktop in self.desktops:
	    desktop.update()
	    desktop.draw()

	#Chat window
	#self.DrawChat()

	pygame.display.flip()

    def DrawChat(self):

	font = pygame.font.Font("FreeSans.ttf", 14)

	pygame.draw.rect(self.screen,(0,0,0),(300,400,400,200))
	pygame.draw.rect(self.screen,(255,255,255),(305,405,390,190))
	pygame.draw.rect(self.screen,(0,0,0),(300,600,400,30))
	pygame.draw.rect(self.screen,(255,255,255),(305,605,390,20))

	curchat = self.g.curchat
	if self.g.enterchat:
	    curchat += "|"
	chattext = font.render(curchat,1,(0,0,0))
	chatpos = chattext.get_rect()
	chatpos.left = 10
	chatpos.centery = 575	

	self.screen.blit(chattext,chatpos)

	count = 0
	for i in range(-1,-6,-1):
	    try:
		chattext = font.render(self.g.chatlist[i],1,(0,0,0))

		count += 1

		chatpos = chattext.get_rect()
		chatpos.left = 310
		chatpos.centery = 550 - 15*count	

		self.screen.blit(chattext,chatpos)
	    except:
		pass

    def DrawWait(self,message):

	defaultStyle.init(gui)
	desktop_main = Desktop()
	desktop = Window(position = (300,220), size = (400,200), parent = desktop_main, text = "Waiting", closeable = False, shadeable = False)

	labelStyleCopy = gui.defaultLabelStyle.copy()
	Label(position = (100,75),size = (50,0), parent = desktop, text = message, style = labelStyleCopy)

	font = pygame.font.Font("FreeSans.ttf", 30)
	self.titletext = font.render("Play against the computer",1,(255,255,255))
	self.titletext2 = font.render("Start a network game",1,(255,255,255))
	self.titletext3 = font.render("Join a network game",1,(255,255,255))
	self.titletext4 = font.render("Options",1,(255,255,255))

	self.titlepos = self.titletext.get_rect()
	self.titlepos.centerx = 512
	self.titlepos.centery = 350
	self.titlepos2 = self.titletext2.get_rect()
	self.titlepos2.centerx = 512
	self.titlepos2.centery = 450
	self.titlepos3 = self.titletext3.get_rect()
	self.titlepos3.centerx = 512
	self.titlepos3.centery = 550
	self.titlepos4 = self.titletext4.get_rect()
	self.titlepos4.centerx = 512
	self.titlepos4.centery = 650

	desktop_main.update()

	self.screen.fill((0,0,255))               

	#YOUR RENDERING HERE!!!
	self.screen.blit(self.menuback, (0,0))
	
	self.screen.blit(self.titletext,self.titlepos)
	self.screen.blit(self.titletext2,self.titlepos2)
	self.screen.blit(self.titletext3,self.titlepos3)
	self.screen.blit(self.titletext4,self.titlepos4)

	#Last thing to draw, desktop
	try:
	    desktop_main.draw()
	except:
	    pass

	#Flips!
	pygame.display.flip()

    def DrawGame(self,flip=True):

	screen = self.screen
	g = self.g
	p = self.p
	playernames = self.g.playernames

	# DRAWING           
	screen.fill((0x00, 0xb0, 0x00))
	#Stage area
	pygame.draw.rect(screen,(0,0,0),(g.curstagexy[0]-5,g.curstagexy[1]-5,g.curstagexy[2]+10,g.curstagexy[3]+10))
	pygame.draw.rect(screen,(0,255,0),g.curstagexy)

	sr = screen.get_rect()
	centerx = sr.centerx
	centery = sr.centery

	#Turn arrows
	arrow_length = 30
	headw = 10
	headl = 15
	if g.turn==0:
	    fl = [[(centerx,centery+20),(centerx,centery+20+arrow_length)],
		  [(centerx-headw,centery+20+arrow_length-headl),(centerx,centery+20+arrow_length)],
		  [(centerx+headw,centery+20+arrow_length-headl),(centerx,centery+20+arrow_length)]]
	elif g.turn==1:
	    fl = [[(centerx-90,centery-50),(centerx-90-arrow_length,centery-50)],
		  [(centerx-90-arrow_length+headl,centery-50-headw),(centerx-90-arrow_length,centery-50)],
		  [(centerx-90-arrow_length+headl,centery-50+headw),(centerx-90-arrow_length,centery-50)]]
	elif g.turn==2:
	    fl = [[(centerx,centery-90),(centerx,centery-90-arrow_length)],
		  [(centerx-headw,centery-90-arrow_length+headl),(centerx,centery-90-arrow_length)],
		  [(centerx+headw,centery-90-arrow_length+headl),(centerx,centery-90-arrow_length)]]
	elif g.turn==3:
	    fl = [[(centerx+100,centery-50),(centerx+100+arrow_length,centery-50)],
		  [(centerx+100+arrow_length-headl,centery-headw-50),(centerx+100+arrow_length,centery-50)],
		  [(centerx+100+arrow_length-headl,centery+headw-50),(centerx+100+arrow_length,centery-50)]]
	for points in fl:
	    pygame.draw.aaline(screen,(200,0,0), points[0], points[1])

	if g.roundOver:
	    for c in g.cardGroup.cards:
		if (c.side==0) & c.location in range(3,401):
		    c.flip()

	pygame.draw.rect(screen,(0,0,0),(g.curlocxy[1][0]+2,g.curlocxy[1][1]+2,70,90),2)

	g.cardGroup.draw(screen)

	if g.selectionRect.width > 0 and g.selectionRect.height > 0:
	    pygame.draw.rect(screen,(0xff,0xff,0x00),g.selectionRect,3)

	if p.viewhelp:
	    sr = screen.get_rect()
	    g.helptextRect.centerx = sr.centerx
	    g.helptextRect.centery = sr.centery      
	    screen.blit(g.helptext,g.helptextRect.topleft)

	if g.curState().turnState == PRE_DRAW:
	    state_text = "Draw or pick up"
	else:
	    state_text = "Meld or discard"
	    
	#Score area
	pygame.draw.rect(screen,(0,0,0),(g.curscorex-5,5,280,60))
	pygame.draw.rect(screen,(0,0,255),(g.curscorex,10,270,50))

	font = pygame.font.Font("freesansbold.ttf", 14)
	font2 = pygame.font.Font("FreeSans.ttf", 14)
	roundtext = font.render("%s%s" % ("ROUND ",g.round),1,(255,255,255))
	team1text = font.render("%s%s" % ("Team 1: ",g.team1score),1,(255,255,255))
	team2text = font.render("%s%s" % ("Team 2: ",g.team2score),1,(255,255,255))
	curteamtext = font2.render("%s%s%s" % (playernames[g.turn],": ",state_text),1,(255,255,255))	
	
	roundpos = roundtext.get_rect()
	roundpos.centerx = g.curscorex + 40
	roundpos.centery = 23
	team1pos = roundtext.get_rect()
	team1pos.centerx = g.curscorex + 110
	team1pos.centery = 23
	team2pos = roundtext.get_rect()
	team2pos.centerx = g.curscorex + 210
	team2pos.centery = 23
	curteampos = roundtext.get_rect()
	curteampos.centerx = g.curscorex + 40
	curteampos.centery = 43
	screen.blit(roundtext,roundpos)
	screen.blit(team1text,team1pos)
	screen.blit(team2text,team2pos)
	screen.blit(curteamtext,curteampos)

	#Chat window
	pygame.draw.rect(screen,(0,0,0),(g.curchatx-5,70,280,90))
	pygame.draw.rect(screen,(255,255,255),(g.curchatx,75,270,85))
	pygame.draw.rect(screen,(0,0,0),(g.curchatx-5,160,280,30))
	pygame.draw.rect(screen,(255,255,255),(g.curchatx,165,270,20))

	curchat = g.curchat
	if g.enterchat:
	    curchat += "|"
	chattext = font2.render(curchat,1,(0,0,0))
	chatpos = chattext.get_rect()
	chatpos.left = g.curchatx + 5
	chatpos.centery = 175	

	screen.blit(chattext,chatpos)

	count = 0
	for i in range(-1,-6,-1):
	    try:
		chattext = font2.render(g.chatlist[i],1,(0,0,0))

		count += 1

		chatpos = chattext.get_rect()
		chatpos.left = g.curchatx + 5
		chatpos.centery = 160 - 15*count	

		screen.blit(chattext,chatpos)
	    except:
		pass

	if flip: pygame.display.flip()

    def DrawEndRound(self):

	self.screen.blit(self.g.endroundtext,self.g.endroundtextRect.topleft)
	pygame.display.flip()

    def DrawGoOut(self):

	screen = self.screen
	g = self.g
	p = self.p
	playernames = self.g.playernames

	font2 = pygame.font.Font("FreeSans.ttf", 20)

	text1 = ["Your partner wants to go out",
		 "",
		 "Press Y to let them",
		 "Press N to stop them"]

	sr2 = screen.get_rect()
	g.goouttextRect.centerx = sr2.centerx
	g.goouttextRect.centery = sr2.centery

	screen.blit(g.goouttext,g.goouttextRect.topleft)

	ty = 8 + g.goouttextRect.top
	for t in text1:
	    img = font2.render(t, 1, (0xff, 0xff, 0))
	    r = img.get_rect()
	    r.top = ty
	    r.left = 8 + g.goouttextRect.left
	    ty += 25
	    if t=="  ":
		tx-=100
	    screen.blit(img,r)

	pygame.display.flip()

