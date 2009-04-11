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
	self.windowsize = (1024,768)
	self.menuback = pygame.image.load("./cards/titlescreen.gif").convert()
	self.screen = pygame.display.set_mode(self.windowsize)
	self.g = CanastaRound()
	self.p = HumanPlayer()
	self.factory = ReconnectingPBClientFactory()
	self.port = 7171
	self.server = server
	self.id = UUID(id)

	self.clock = pygame.time.Clock()

	self.rejected = False
	self.connected = False
	self.controller = False
	self.options = options
	self.positions = [None]*4

	self.pause = False
	self.starting = False
	self.start_game = False
	self.start_match = False
	self.cancel = False
	self.started = False
	self.initialized = False
	self.new_players = True	
	self.shut_down = False
	self.shutting_down = False
	self.CommandQueue = []
	self.desktop = Desktop()

    def callDebug(self,obj):
	if DEBUGGER: obj.callRemote("debug")

    def remote_debug(self):
	self.g.roundOver=True

    def Connect(self,obj):
	if DEBUGGER: print "Connection established with server"
	obj.callRemote("joinServer",self,self.name,str(self.id),VERSION).addCallback(self.isController)

    def Disconnect(self,obj):
	if DEBUGGER: print "Hanging up connection"
	obj.callRemote("hangUp",str(self.id)).addCallback(self.isDisconnected)

    def isDisconnected(self,obj):
	if DEBUGGER: print "Closed connection with server:",obj
	self.shut_down = True

    def failConnect(self,obj):
	if self.cancel:
	    return "cancel"
	else:
	    if DEBUGGER: print "Failed to connect, retrying..."
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

    def remote_lookAlive(self):
	return True

    def getNames(self,obj):
	obj.callRemote("Names").addCallback(self.gotNames)

    def remote_updateNames(self,namelist):
	self.names = namelist
	if self.initialized: print "got a new name",namelist
	if self.initialized: self.g.playernames.append(namelist[-1])
	self.new_players = True

    def remote_removeName(self,name):
	if DEBUGGER: print "removing " + name + " from name list"
	if self.initialized: self.g.playernames.remove(name)
	self.names.remove(name)
	try: self.positions.remove(name)
	except: pass
	self.new_players = True

    def gotNames(self,obj):
	self.names = obj

    def startServer(self,obj):
	self.oneRef = obj
	self.oneRef.callRemote("Start",str(self.id),self.player_positions,self.options).addCallbacks(self.didStart,self.failStart)

    def didStart(self,obj):
	if DEBUGGER: print "Game started on the server"
	self.start_match = True
	if not self.server: self.factory.getRootObject().addCallbacks(self.blockClients)

    def failStart(self,obj):
	if DEBUGGER: print "Failed to start game on the server, retrying..."
	sleep(1)
	self.factory.getRootObject().addCallbacks(self.startServer,self.failStart)

    def blockClients(self,obj):
	obj.callRemote("blockConnections")

    def notClosed(self,obj):
	if DEBUGGER: print "Server did not close correctly:",obj
	self.shut_down = True

    def isClosed(self,obj):
	if DEBUGGER: print "Server closed correctly:",obj
	self.shut_down = True

    def stopServer(self,obj):
	self.shutting_down = True
	self.oneRef = obj
	self.oneRef.callRemote("Shutdown",str(self.id)).addCallbacks(self.isClosed,self.notClosed)

    def reportReady(self,obj):
	self.started=False
	self.initialized=False
	self.oneRef = obj
	if self.g.human in [0,1,2,3]: self.oneRef.callRemote("isReady",str(self.id))

    def SendCommand(self,obj):
	self.oneRef = obj
	self.oneRef.callRemote("takeCanastaCommand",str(self.id),self.lastplay)

    def clearCommand(self,obj):
	self.lastplay=CanastaCommand(NO_PLAY,[],[])

    def SendChat(self,obj):
	if DEBUGGER: print "sending chat"
	if len(self.chatwin.chattxt.text)>0:
	    self.lastchat = CanastaCommand(CHAT,[self.chatwin.chattxt.text,self.g.myPos])
	self.chatwin.chattxt.text = ""
	self.oneRef = obj
	self.oneRef.callRemote("takeChat",str(self.id),self.lastchat)

    def remote_initGame(self,players,human,options):
	if DEBUGGER: print "client game initialized"
	if options.animation == None:
	    options.animation = self.options.animation
	self.g.gameStart(players,human,options)
	try: self.chatwin.close()
	except: pass
	self.genChat(self.g.CHATX[0],self.g.CHATX[1])
	self.g.initCanasta(nextround=False)
	self.chatwin.enabled = True
	self.screen = pygame.display.set_mode(self.windowsize,RESIZABLE)

    def remote_resetRound(self):
      
	self.started = False
	self.initialized = False

    def remote_resetGame(self):
	self.starting = False
	self.start_game = False
	self.start_match = False
	self.cancel = False
	self.started = False
	self.initialized = False
	self.new_players = True	
	self.shut_down = False
	self.shutting_down = False
	self.CommandQueue = []

    def remote_newGame(self):
	if DEBUGGER: print "client game reset"
	self.g.newGame()

    def remote_initRound(self):
	try: self.desktop.query.close()
	except: pass
	if DEBUGGER: print "client round initialized"
	self.g.initCanasta()
	try: self.chatwin.close()
	except: pass
	self.genChat(self.g.curchatx,self.g.CHATX[1])
	self.chatwin.enabled = True
	self.started = True

    def remote_readInit(self,status):
	if not self.initialized:
	    if DEBUGGER: print "client got status"
	    self.g.readInit(status)
	    self.initialized = True

    def remote_readCommand(self,command):
	"""
	Read a command from the server. Chats are executed immediately, everything else is queued for execution later.
	"""
	if command.action==CHAT:
	    self.g.execCode(command)
	    return
	else:
	    self.CommandQueue.append(command)
	    retcode = True
	    return [self.g.lastCommand,retcode]

    def execCommand(self,command):
	"""
	Execute a command on the local game object. Uses items that have previously been queued from the server.
	"""
	if self.g.turn==self.g.myPos:
	    invis = False
	else:
	    invis = True
	self.g.execCode(command,invisible=invis)
	retcode = self.g.lastReturn
	if DEBUGGER: print "result was",self.g.lastReturn
	if self.g.lastReturn: 
	    if self.g.roundOver:
		if DEBUGGER: print "ROUND OVER *** client updating score"
		team1round = self.g.cardPoints(1) + self.g.specialPoints(1,params=False) - self.g.handPoints(1)
		team2round = self.g.cardPoints(2) + self.g.specialPoints(2,params=False) - self.g.handPoints(2)

		self.g.team1score += team1round
		self.g.team2score += team2round

		self.genEndRound()

	self.clearCommand(None)
	if DEBUGGER & (not retcode): print "WARNING: command failed"
	return [self.g.lastCommand,retcode]

    def remote_lostPlayer(self,name):

	def ComputerOnClick(button):
	    self.result = True
	    self.desktop.query.close()
	    self.desktop.query.position = (0,0)
	    self.desktop.query.size = (0,0)
	def ResetOnClick(button):
	    self.result = False
	    self.desktop.query.close()
	    self.desktop.query.position = (0,0)
	    self.desktop.query.size = (0,0)

	self.result = None

	try: self.desktop.query.close()
	except: pass

	defaultStyle.init(gui)
	endStyle = {'font-color': (255,255,255), 'font': font.Font(None,20), 'autosize': True, "antialias": True,'border-width': False, 'border-color': (0,0,0), 'wordwrap': False}
	self.desktop.query = Window(position = (250,180), size = (500,200), parent = self.desktop, text = "Lost Player", closeable = False, shadeable = False)

	labelStyleCopy = gui.defaultLabelStyle.copy()
	Label(position = (30,50),size = (100,0), parent = self.desktop.query, text = str(name) + " has disconnected", style = endStyle)
	Label(position = (30,75),size = (100,0), parent = self.desktop.query, text = "Do you want to replace them with a computer player?", style = endStyle)
	Label(position = (30,100),size = (100,0), parent = self.desktop.query, text = "Or end this game and start a new one?", style = endStyle)
	Label(position = (30,125),size = (100,0), parent = self.desktop.query, text = "If you replace them, you can add them back in if they reconnect", style = endStyle)
	    
	Computer_button = Button(position = (30,170), size = (175,0), parent = self.desktop.query, text = "Replace with computer")
	Computer_button.onClick = ComputerOnClick
	Reset_button = Button(position = (270,170), size = (175,0), parent = self.desktop.query, text = "Start over with a new game")
	Reset_button.onClick = ResetOnClick
	
	while self.result == None:
	    self.defaultInput()
	    self.DrawQuery()

	return self.result

    def remote_waitPlayer(self,name):

	defaultStyle.init(gui)
	endStyle = {'font-color': (255,255,255), 'font': font.Font(None,20), 'autosize': True, "antialias": True,'border-width': False, 'border-color': (0,0,0), 'wordwrap': False}
	self.desktop.query = Window(position = (250,180), size = (500,200), parent = self.desktop, text = "Lost Player", closeable = False, shadeable = False)

	labelStyleCopy = gui.defaultLabelStyle.copy()
	Label(position = (30,50),size = (100,0), parent = self.desktop.query, text = str(name) + " has disconnected", style = endStyle)
	Label(position = (30,100),size = (100,0), parent = self.desktop.query, text = "Waiting for the game host to replace them or restart the game", style = endStyle)

	self.pause = True

	return

    def askReset(self):

	def YesOnClick(button):
	    self.pause = False
	    def1 = self.factory.getRootObject()
	    def1.addCallback(self.gameReset)
	    self.desktop.query.close()
	    self.desktop.query.position = (0,0)
	    self.desktop.query.size = (0,0)
	def NoOnClick(button):
	    self.pause = False
	    self.desktop.query.close()
	    self.desktop.query.position = (0,0)
	    self.desktop.query.size = (0,0)

	defaultStyle.init(gui)
	endStyle = {'font-color': (255,255,255), 'font': font.Font(None,24), 'autosize': True, "antialias": True,'border-width': False, 'border-color': (0,0,0), 'wordwrap': False}
	self.desktop.query = Window(position = (350,250), size = (300,200), parent = self.desktop, text = "Reset", closeable = False, shadeable = False)

	labelStyleCopy = gui.defaultLabelStyle.copy()
	Label(position = (100,50),size = (100,0), parent = self.desktop.query, text = "Reset the game", style = endStyle)
	Label(position = (100,100),size = (100,0), parent = self.desktop.query, text = "Are you sure?", style = endStyle)

	Yes_button = Button(position = (50,150), size = (40,0), parent = self.desktop.query, text = "Yes")
	No_button = Button(position = (200,150), size = (40,0), parent = self.desktop.query, text = "No")
	Yes_button.onClick = YesOnClick
	No_button.onClick = NoOnClick

	self.pause = True

	return	

    def gameReset(self,obj):
	obj.callRemote("Reset",str(self.id))

    def remote_unPause(self):
	try:
	    self.desktop.query.close()
	    self.desktop.query.position = (0,0)
	    self.desktop.query.size = (0,0)
	except: pass
	self.pause = False

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

    def overWindow(self):

	result = False

	try:
	    temp = self.desktop.assign
	    assign = True
	    assign_pos = self.desktop.assign.position
	    assign_size = self.desktop.assign.size
	except: 
	    assign = False

	try:
	    temp = self.desktop.query
	    query = True
	    query_pos = self.desktop.query.position
	    query_size = self.desktop.query.size
	except: 
	    query = False

	try:
	    temp = self.chatwin
	    chat = True
	    chat_pos = self.chatwin.position
	    chat_size = self.chatwin.size
	except:
	    chat = False

	if gui.events != None:
	    for event in gui.events:
		if event.type in [MOUSEBUTTONUP,MOUSEBUTTONDOWN,MOUSEMOTION]:
		    if assign:
			if (event.pos[0] > assign_pos[0]) & (event.pos[0]<assign_pos[0]+assign_size[0]) & (event.pos[1] > assign_pos[1]) & (event.pos[1]<assign_pos[1]+assign_size[1]):
			    result = True
		    if query:
			if (event.pos[0] > query_pos[0]) & (event.pos[0]<query_pos[0]+query_size[0]) & (event.pos[1] > query_pos[1]) & (event.pos[1]<query_pos[1]+query_size[1]):
			    result = True
		    if chat:
			if (event.pos[0] > chat_pos[0]) & (event.pos[0]<chat_pos[0]+chat_size[0]) & (event.pos[1] > chat_pos[1]) & (event.pos[1]<chat_pos[1]+chat_size[1]):
			    result = True

	return result

    def defaultInput(self,chat=True):

	if self.chatwin.chattxt.hasFocus:
	    self.g.enterchat = True
	else:
	    self.g.enterchat = False

	play = self.p.getPlay(self.g,gui.events)

	if play.action == QUIT_GAME:
	    def1 = self.factory.getRootObject()
	    if self.controller:
		def1.addCallbacks(self.stopServer)
	    else:
		def1.addCallbacks(self.Disconnect)
	    play = CanastaCommand(NO_PLAY,[],[])
	elif (play.action == CHAT) & chat:
	    self.lastchat = play
	    def1 = self.factory.getRootObject()
	    def1.addCallback(self.SendChat)
	    play = CanastaCommand(NO_PLAY,[],[])
	elif play.action == RESIZE:
	    self.screen = pygame.display.set_mode(play.arglist[0],RESIZABLE)
	    self.windowsize = play.arglist[0]	
	    self.chatwin.close()
	    self.genChat(self.g.curchatx,self.g.CHATX[1])
	    play = CanastaCommand(NO_PLAY,[],[])

	if self.g.animating: 
	    self.g.animate()
	else:
	    try:
		self.execCommand(self.CommandQueue.pop(0))
	    except:
		pass

	return play

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

	self.clock.tick(40)

	if self.overWindow():
	    self.p.over_window = True
	else:
	    self.p.over_window = False

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
	elif self.pause:
	    self.defaultInput()
	    self.DrawQuery()
	elif self.shutting_down:
	    pass
	elif self.started & self.initialized:

	    if self.chatwin.chattxt.hasFocus:
		self.g.enterchat = True
	    else:
		self.g.enterchat = False
	
	    play = self.defaultInput()

	    if (self.g.roundOver) | (self.p.viewhelp==1): 
		if self.p.viewhelp==1:
		    try: 
			if self.desktop.query.wintype != "help":
			    try:
				self.desktop.query.close()
				self.desktop.query.position = (0,0)
				self.desktop.query.size = (0,0)
				self.genHelp()
			    except:
				self.genHelp()
		    except:
			self.genHelp()
		self.DrawQuery()  
	    else:
		self.DrawGame()	
		if play.action == RESET:
		    if self.controller:
			self.askReset()
		elif play.action != NO_PLAY:
		    if self.g.turn==self.g.myPos:
			self.lastplay = play
			def1 = self.factory.getRootObject()
			def1.addCallback(self.SendCommand)    
	    if self.p.viewhelp==0:
		try:
		    if self.desktop.query.wintype == "help":
			self.desktop.query.close()
			self.desktop.query.position = (0,0)
			self.desktop.query.size = (0,0)
		except: pass

	elif (not self.start_match) & self.controller & (not self.server):
	    for event in pygame.event.get():
		if event.type == QUIT:
		    self.cancel = True
		elif event.type == KEYDOWN and event.key == K_ESCAPE:
		    self.cancel = True
	    if self.connected:
		self.DrawWait("Waiting for game to start...")
	    else:
		self.DrawWait("Connecting to the game server...")
	    if not self.starting:
		if DEBUGGER: print "Starting the server"
		self.factory.getRootObject().addCallbacks(self.startServer,self.failStart)
		self.starting = True
	elif (not self.server) | self.start_match:
	    if self.connected:

		if self.chatwin.chattxt.hasFocus:
		    self.g.enterchat = True
		else:
		    self.g.enterchat = False

		self.DrawWait("Waiting for game to start...")
		play = self.p.getPlay(self.g,gui.events)
		if play.action == QUIT_GAME:
		    def1 = self.factory.getRootObject()
		    if self.controller:
			def1.addCallbacks(self.stopServer)
		    else:
			def1.addCallbacks(self.Disconnect)
		elif play.action == CHAT:
		    self.lastchat = play
		    def1 = self.factory.getRootObject()
		    def1.addCallback(self.SendChat)
	    else:
		for event in pygame.event.get():
		    if event.type == QUIT:
			self.shut_down = True
		    elif event.type == KEYDOWN and event.key == K_ESCAPE:
			self.shut_down = True
		self.DrawWait("Connecting to the game server...")
	elif not self.connected:
	    self.DrawWait("Setting up the game server...")
	else:
	    if not self.start_game:

		if self.chatwin.chattxt.hasFocus:
		    self.g.enterchat = True
		else:
		    self.g.enterchat = False

		play = self.p.getPlay(self.g,gui.events)

		#Handle Input Events
		for event in gui.events:
		    if event.type == KEYDOWN and event.key == 13:
			if not self.g.enterchat: self.start_game = True
		    else:
			pass

		if play.action == QUIT_GAME:
		    def1 = self.factory.getRootObject()
		    def1.addCallbacks(self.stopServer)
		elif play.action == CHAT:
		    self.lastchat = play
		    def1 = self.factory.getRootObject()
		    def1.addCallback(self.SendChat)

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
	    self.desktop.assign.close()
	    self.desktop.assign.position = (0,0)
	    self.desktop.assign.size = (0,0)

	def assignPlayer(arg):
	    which = self.glist.index(arg.name)
	    last = self.gr[which]
	    if DEBUGGER: print arg.name,self.glist,which,last
	    if arg.value==None:
		return
	    loc = posnames.index(arg.text)
	    #Assign an observer. Allows starting a game with no human players only if the debugger is on.
	    if (loc == 4) & ((positions != [None]*4) | DEBUGGER):
		try: self.gr[which].value = False
		except: pass
		for i in range(len(positions)):
		    if positions[i]==arg.name:
			positions[i]=None
		self.gr[which] = arg
	    #Reject the assign if it conflicts with another player's assignment or leaves no human players with the debugger off.
	    elif (positions[loc]!=None) | ((loc==4) & (positions==[None]*4) & (not DEBUGGER)):
		print "BZZT!"
		arg.value = False
		self.gr[which].value = True
	    #Otherwise, assign the position
	    else:
		try: self.gr[which].value = False
		except: pass
		for i in range(len(positions)):
		    if positions[i]==arg.name:
			positions[i]=None
		positions[loc] = arg.name
		self.gr[which] = arg
	    if DEBUGGER: print positions
	    self.positions = positions

	playernames=self.names

	if self.new_players:

	    try: 
		self.desktop.assign.close()
		self.desktop.query.position = (0,0)
		self.desktop.query.size = (0,0)
	    except: pass

	    optionsurf = pygame.image.load("./art/optionbox.png").convert_alpha()

	    self.desktop_main = Desktop()
	    self.desktop.assign = Window(position = (100,100), size = (800,600), parent = self.desktop, text = "Assign players", closeable = False, shadeable = False)
	    self.gr = []
	    self.glist = []

	    defaultStyle.init(gui)
	    labelStyleCopy = gui.defaultLabelStyle.copy()
	    labelStyleCopy['wordwrap'] = True

	    if self.positions == [None]*4:
		default = True
	    else:
		default = False
	    positions = self.positions
	    posnames = ["Bottom","Left","Top","Right","Observer"]
	    
	    for index, p in enumerate(self.names):
		if index<4:
		    def_pos = posnames[index]
		else:
		    def_pos = None

		if index==0:
		    label1 = Label(position = (125,125),size = (200,0), parent = self.desktop.assign, text = "Players will appear here when they connect to your game.", style = labelStyleCopy)
		    label2 = Label(position = (125,145),size = (200,0), parent = self.desktop.assign, text = "Assign them to a player position and press the start button when ready.", style = labelStyleCopy)
		    label3 = Label(position = (125,165),size = (200,0), parent = self.desktop.assign, text = "Unfilled positions will be filled with computer players.", style = labelStyleCopy)
		    label3 = Label(position = (125,185),size = (200,0), parent = self.desktop.assign, text = "Observers can watch the game and use the chat window, and may be included in the next round.", style = labelStyleCopy)
		label_name = Label(position = (125,220 + index*25),size = (200,0), parent = self.desktop.assign, text = p, style = labelStyleCopy)

		if (index<4) & default:
		    positions[index] = p
		self.gr.append(None)
		self.glist.append(p)

		for index2, pos in enumerate(posnames):
		    o = CheckBox(position = (200+index2*75,220+index*25), parent = self.desktop.assign, text = pos, style = gui.createOptionBoxStyle(gui.defaultFont, optionsurf, 12, (255,255,255),
                                                     (100,100,100), autosize = True))
		    o.name = p
		    print p
		    o.index = index2
		    try:
			if positions[index2]==p:
			    o.value = True
			    self.gr[index] = o
		    except:
			pass
		    if (index2==4) & (self.gr[index]==None):
			o.value = True
		    o.onValueChanged = assignPlayer


		OK_button = Button(position = (125,400), size = (50,0), parent = self.desktop.assign, text = "Start")
		OK_button.onClick = OKOnClick

	    self.positions = positions
	    self.new_players = False

	self.DrawGame()

    def DrawWait(self,message):

	defaultStyle.init(gui)
	desktop_main = Desktop()
	desktop = Window(position = (300,220), size = (400,200), parent = desktop_main, text = "Waiting", closeable = False, shadeable = False)

	labelStyleCopy = gui.defaultLabelStyle.copy()
	Label(position = (100,75),size = (50,0), parent = desktop, text = message, style = labelStyleCopy)

	if not self.connected:
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

	    self.screen.fill((0,0,255))               

	    #YOUR RENDERING HERE!!!
	    self.screen.blit(self.menuback, (0,0))
	    
	    self.screen.blit(self.titletext,self.titlepos)
	    self.screen.blit(self.titletext2,self.titlepos2)
	    self.screen.blit(self.titletext3,self.titlepos3)
	    self.screen.blit(self.titletext4,self.titlepos4)
	else:
	    self.DrawGame(flip=False)

	#Last thing to draw, desktop
	try:
	    desktop_main.update()
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

	self.chatwin.chatdisplay.text = ""

	if not self.chatwin.shaded:
	    for i in range(-1,-8,-1):
		try:
		    text = self.g.chatlist[i]
		    count = 0
		    rendered = gui.wrapText(text + "\n" + self.chatwin.chatdisplay.text,self.chatwin.chatdisplay.style['font'],self.chatwin.chatdisplay.size[0])
		    for char in rendered: 
			if char=="\n": count += 1
		    if count<9:
			self.chatwin.chatdisplay.text = self.g.chatlist[i] + "\n" +self.chatwin.chatdisplay.text
		except: pass

	gui.setEvents()
	try:
	    self.desktop.update()
	except: pass
	self.desktop.draw()

	if flip: pygame.display.flip()

    def genEndRound(self):

	self.next_round = False
	
	def ContinueOnClick(button):
	    self.desktop.query.close()
	    self.desktop.query.position = (0,0)
	    self.desktop.query.size = (0,0)
	    def1 = self.factory.getRootObject()
	    def1.addCallback(self.reportReady)

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

	if (self.g.team1score>=5000) & (self.g.team1score>self.g.team2score):
	      endtext1.append("Team 1 is the winner!")
	if (self.g.team2score>=5000) & (self.g.team2score>self.g.team1score):
	      endtext2.append("Team 2 is the winner!")
		

	defaultStyle.init(gui)
	endStyle = {'font-color': (255,255,255), 'font': font.Font(None,24), 'autosize': True, "antialias": True,'border-width': False, 'border-color': (0,0,0), 'wordwrap': False}
	self.desktop.query = Window(position = (250,180), size = (500,400), parent = self.desktop, text = "Round Over", closeable = False, shadeable = False)

	labelStyleCopy = gui.defaultLabelStyle.copy()
	Label(position = (200,40),size = (100,0), parent = self.desktop.query, text = "Round " + str(self.g.round) + " over", style = endStyle)

	for pos, t in enumerate(endtext1):
	    Label(position = (50,80+25*pos),size = (200,0), parent = self.desktop.query, text = t, style = endStyle)
	for pos, t in enumerate(endtext2):
	    Label(position = (300,80+25*pos),size = (200,0), parent = self.desktop.query, text = t, style = endStyle)
		    
	Cont_button = Button(position = (200,350), size = (70,0), parent = self.desktop.query, text = "Continue")
	Cont_button.onClick = ContinueOnClick

    def genHelp(self):

	def helpClose(button):
	    self.p.viewhelp = 0
	    self.desktop.query.wintype = None
	    self.desktop.query.position = (0,0)
	    self.desktop.query.size = (0,0)

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
	    "-----------------------",
	    "See manual for alternate keyboard controls"]

	defaultStyle.init(gui)
	helpStyle = {'font-color': (255,255,255), 'font': font.Font(None,24), 'autosize': True, "antialias": True,'border-width': False, 'border-color': (0,0,0), 'wordwrap': False}
	self.desktop.query = Window(position = (300,120), size = (400,500), parent = self.desktop, text = "Help", closeable = True, shadeable = False)
	self.desktop.query.onClose = helpClose
	self.desktop.query.wintype = "help"

	labelStyleCopy = gui.defaultLabelStyle.copy()

	for pos, t in enumerate(text):
	    Label(position = (30,35+25*pos),size = (200,0), parent = self.desktop.query, text = t, style = helpStyle)

    def genChat(self,x,y):

	defaultStyle.init(gui)
	self.chatwin = Window(position = (x,y), size = (280,130), parent = self.desktop, text = "", closeable = False, shadeable = True)

	labelStyleCopy = gui.defaultLabelStyle.copy()
	labelStyleCopy['autosize'] = False
	labelStyleCopy['wordwrap'] = True
	labelStyleCopy['font'] = pygame.font.Font("FreeSans.ttf", 12)

	textboxStyleCopy = gui.defaultTextBoxStyle.copy()
	textboxStyleCopy['border-width'] = 1
	textboxStyleCopy['font'] = pygame.font.Font("FreeSans.ttf", 12)

	self.chatwin.chatdisplay = Label(position = (5,5),size = (270,105), parent = self.chatwin, text = "", style = labelStyleCopy)
	self.chatwin.chattxt = TextBox(position = (5,107), size = (270, 0), parent =self.chatwin, text = "", style = textboxStyleCopy)

	self.chatwin.enabled = True

    def DrawQuery(self):

	self.DrawGame(flip=False)

	#Flips!
	pygame.display.flip()