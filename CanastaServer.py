# -*- coding: utf-8 -*-
"""PB copy receiver example.

This is a Twisted Application Configuration (tac) file.  Run with e.g.
   twistd -ny copy_receiver.tac
See the twistd(1) man page or
http://twistedmatrix.com/documents/current/howto/application for details.
"""

import sys

import os, pygame,math
from pygame.locals import *
import random
from time import sleep

from CardImages import CardImages
from CardGroup import CardGroup
from Card import Card

from ComputerPlayer import ComputerPlayer

from twisted.application import service, internet
from twisted.internet import reactor
from twisted.spread import pb
from twisted.python import log
from twisted.internet.task import LoopingCall
#log.startLogging(sys.stdout)
from uuid import UUID

from CanastaRound import CanastaRound
from CanastaObjects import *

#The info string will surround status messages from the server. The loop rate specifies how often the server attempts to get plays from computer players. The timeout is the number of seconds the server will go without getting any input from a player, before it checks to make sure no-one has disconnected.
INFO_STRING = "***"
LOOP_RATE = 0.05
TIMEOUT = 60

class CanastaServer(pb.Root):
    def __init__(self,controller_id):
	self.g = CanastaRound(images=False)
	self.playerlist = {}
	self.idlist = []
	self.players = []
	self.accept_clients = True
	self.game_started = False
	self.players_ready = [False]*4
	self.wait_response = False
	self.pause = False
	self.executing = False
	self.computing = False
	self.controller_id = UUID(controller_id)
	self.shut_down = False
	self.last_command_time = 0
	if DEBUGGER: print "server started"

    def remote_debug(self):
	self.g.roundOver=True
	for player in self.playerlist:
	    player[2].callRemote("debug")

    def remote_Reset(self,id):
	if self.playerlist[str(id)][1]:
	    self.gameReset()


    def infoChat(self,message):
	"""
	Send a server informational message to the chat windows of the clients
	"""
	command = CanastaCommand(CHAT,[message],[INFO_STRING])
	self.sendChat(command)

    def tryGoOut(self,id):
	"""
	Query the current player's partner to ask whether the player can go out.
	To prevent table talk, chatting (and all other command execution) is blocked until the partner
	responds.
	"""

	if self.g.canGoOut():
	    message = self.playerlist[str(id)][0] + " asked to go out"
	    self.infoChat(message)
	    opp_pos = self.playerset.index(str(id)) + 2
	    if opp_pos > 3:
		opp_pos -= 4
	    opp_player = self.playerlist[self.playerset[opp_pos]]
	    self.wait_response = True
	    if isinstance(opp_player[2],ComputerPlayer):
		result = opp_player[2].mayIGoOut()
		self.goOutNow(result)
	    else:
		opp_player[2].callRemote("goOut").addCallbacks(self.goOutNow,self.goOutError)
	else:
	    return

    def goOutError(self,obj):
	if DEBUGGER: print ["error going out",obj]

    def goOutNow(self,obj):
	"""
	Executed after querying a partner about going out. If response is yes, meld any staged cards and
	discard to end the round. If response is no, send a special command that prevents the player from
	going out this turn.
	"""
	if obj:
	    self.infoChat("Partner said yes")
	    code1 = CanastaCommand(MELD_CARDS,[],[])
	    code2 = CanastaCommand(DISCARD_CARD,[1],[])
	    self.execCommand(code1)
	    self.execCommand(code2)
	else:
	    self.infoChat("Partner said no")
	    code = CanastaCommand(BLOCK_OUT,[],[])
	    self.execCommand(code)
	self.wait_response = False

    def replacePlayer(self,which,name):
	self.need_replace = which
	self.pause = True
	for id in self.idlist:
	    player = self.playerlist[str(id)][2]
	    print id,player
	    if self.playerlist[str(id)][1]:
		player.callRemote("lostPlayer",name).addCallback(self.gotReplacement)
	    else:
		player.callRemote("waitPlayer",name)

    def gotReplacement(self,obj):
	if obj:
	    p = ComputerPlayer(self.need_replace)
	    self.playerset[self.need_replace] = str(self.need_replace)
	    self.playerlist[str(self.need_replace)] = ["Computer " + str(self.need_replace),False,p]
	    print "replacing", self.need_replace,self.g.playernames
	    self.g.playernames[self.need_replace] = "Computer " + str(self.need_replace)
	    for p in self.idlist:
		player = self.playerlist[p]
		player[2].callRemote("updateNames",self.remote_Names())
	else:
	    self.playerset.remove(self.playerset[self.need_replace])
	    self.gameReset()
	for id in self.idlist:
	    self.playerlist[id][2].callRemote("unPause")
	self.pause = False

    def removeDeadClient(self,player,p):
	"""
	Removes disconnected clients from the server's records. If the dead client was an observer, continue on with the game. If they were a player, end the game and kick the other clients back to the player-assignment stage.
	"""
	pname = self.playerlist[str(p)][0]
	self.idlist.remove(p)
	self.players.remove(self.playerlist[str(p)][0])
	del self.playerlist[str(p)]
	if self.game_started:
	    if p in self.playerset:
		which = self.playerset.index(p)
		if DEBUGGER: print "Player dropped off, querying"
		self.replacePlayer(which,pname)
	    else:
		self.observerset.remove(p)
		if DEBUGGER: print "Observer dropped off, removing them"
	for p in self.idlist:
	    player = self.playerlist[p]
	    player[2].callRemote("removeName",pname)
	try: self.g.playernames[which] = None
	except: pass
	self.infoChat(pname + " has disconnected")

    def doneExecuting(self,obj=None):
	self.executing = False

    def execCommand(self,command):
	"""
	Excute a game command both locally and on the client players.

	If the round is over, update scores and prepare to wait for the clients.
	"""
	self.executing = True
	cur_turn = self.g.turn
	self.g.execCode(command)
	if DEBUGGER: print ["server executed",self.g.lastCommand,self.g.lastReturn]
	for turn, p in enumerate(self.playerset+self.observerset):
	    player = self.playerlist[str(p)][2]
	    if isinstance(player,ComputerPlayer):
		pass
	    elif self.g.lastReturn:
		try:
		    player.callRemote("readCommand",command).addCallbacks(self.sentCommand,self.errCommand)
		except:
		    self.removeDeadClient(player,p)
	if self.g.lastReturn:
	    self.updateComputers(cur_turn)
	if self.g.roundOver:
	    if self.g.lastReturn:
		if DEBUGGER: print "ROUND OVER *** server updating score"
		team1round = self.g.cardPoints(1) + self.g.specialPoints(1,params=False) - self.g.handPoints(1)
		team2round = self.g.cardPoints(2) + self.g.specialPoints(2,params=False) - self.g.handPoints(2)

		self.g.team1score += team1round
		self.g.team2score += team2round
		for turn, p in enumerate(self.playerset):
		    player = self.playerlist[str(p)][2]
		    if isinstance(player,ComputerPlayer):
			self.players_ready[turn] = player.isReady()
		    else:
			self.players_ready[turn] = False
	self.doneExecuting()

    def sendChat(self,command):
	"""
	Sends a chat message to all clients.
	"""
	self.g.execCode(command)
	if DEBUGGER: print [self.g.lastCommand,self.g.lastReturn]
	for p in self.idlist:
	    player = self.playerlist[str(p)][2]
	    if not isinstance(player,ComputerPlayer):
		player.callRemote("readCommand",command)

    def notClosed(self,obj):
	if DEBUGGER: print "Client did not close correctly:",obj
	self.is_closed = True

    def isClosed(self,obj):
	if DEBUGGER: print "Client closed correctly:",obj
	self.is_closed = True

    def gameReset(self):
	self.executing = True
	to_remove = []
	for id in self.playerset:
	    player = self.playerlist[str(id)][2]
	    if isinstance(player,ComputerPlayer):
		print self.playerlist,id,self.g.playernames
		self.g.playernames.remove(self.playerlist[str(id)][0])
		del self.playerlist[str(id)]
		to_remove.append(id)
	for id in to_remove: self.playerset.remove(id)
	for turn, p in enumerate(self.playerset+self.observerset):
	    player = self.playerlist[str(p)][2]   
	    player.callRemote("updateNames",self.remote_Names())
	    player.callRemote("resetGame")
	self.playerset = []
	self.observerset = []
	self.game_started = False
	self.executing = False

    def nextRound(self):
	"""
	Start the next round. Reset the scores if someone went over 5000 in the last round.
	"""
	if not(False in self.players_ready):
	    if DEBUGGER: print "initializing the next round"
	    if ((self.g.team1score>5000) | (self.g.team2score>5000)) & (self.g.team1score != self.g.team2score):
		self.gameReset()
	    else:
		self.initRound()
		self.initClients()

    def newGame(self):
	"""
	Tell the clients that a new game is starting, so they should reset their scores.
	"""
	self.g.newGame()
	for pos, p in enumerate(self.playerset+self.observerset):
	    player = self.playerlist[p][2]
	    if isinstance(player,ComputerPlayer):
		pass
	    else:
		if DEBUGGER: print "resetting the game"
		player.callRemote("newGame")

    def initGame(self,options):
	"""
	Send the clients the global game settings: the gameplay options, the client's position on the board, and the names of the players.
	"""
	for pos, p in enumerate(self.playerset+self.observerset):
	    player = self.playerlist[str(p)][2]
	    if isinstance(player,ComputerPlayer):
		pass
	    else:
		if DEBUGGER: print "initializing the client"
		player.callRemote("initGame",self.g.playernames,pos,options)

    def initRound(self):
	"""
	Initialize the local game object for the current round. This object will be kept in sync with the parallel objects that are held by the clients.
	"""
	self.g.initCanasta()
	self.g.dealRound()

    def initClients(self):
	"""
	Initialize the round by sending the clients an object describing the deal. After this is called, all game objects held by the server and the clients should be in an identical state.
	"""
	for pos, p in enumerate(self.playerset+self.observerset):
	    player = self.playerlist[p][2]
	    if p in self.observerset:
		player.callRemote("resetRound")
	    if isinstance(player,ComputerPlayer):
		player.initRound(self.g.initStatus())
	    else:
		if DEBUGGER: print "starting the client round"
		player.callRemote("initRound")
		if DEBUGGER: print "initializing the cards"
		status = self.g.initStatus()
		player.callRemote("readInit",status)
	self.players_ready = [False]*4



    def remote_joinServer(self, client, name, id, version):
	if not self.accept_clients:
	    return "This server is not accepting connections -- it is probably in one-player mode."
	elif version != VERSION:
	    return "Error: incompatible client, this host requires version "+VERSION[0]+"."+VERSION[1]+"."+VERSION[2]
	count = 1
	newname = name
	while newname in self.players:
	    newname = name + str(count)
	    count += 1
	name = newname
	if DEBUGGER: print ["player",name,"joined",id]
	if self.game_started:
	    while self.executing | self.computing:
		pass
	    self.executing = True
	    sleep(LOOP_RATE*2)
	    if DEBUGGER: print "Adding player as observer in position",len(self.observerset)+4
	    client.callRemote("initGame",self.g.playernames+[name],len(self.observerset)+4,self.g.options)
	    client.callRemote("initRound")
	    if DEBUGGER: print "initializing the cards"
	    status = self.g.initStatus()
	    self.observerset.append(id)
	    self.g.playernames.append(name)
	    client.callRemote("readInit",status)
	else:
	    self.g.playernames = [None]*4 + self.players + [name]
	self.playerlist[id] = [name,False,client]
	if UUID(id) == self.controller_id:
	    self.playerlist[id][1]=True
	self.players.append(name)
	self.idlist.append(id)
	for index, p in enumerate(self.idlist):
	    player = self.playerlist[p]
	    player[2].callRemote("updateNames",self.remote_Names())
	    if not self.game_started: player[2].callRemote("initGame",self.g.playernames,4+index,CanastaOptions())
	    else: pass
	self.infoChat(name+" has arrived.")
	client.callRemote("lookAlive").addCallback(self.doneExecuting)
	return self.playerlist[id][1]
    
    def remote_blockConnections(self):
	self.accept_clients = False

    def remote_hangUp(self,id):
	player = self.playerlist[id][2]
	self.removeDeadClient(player,id)

    def remote_takeCanastaCommand(self, id, command):
	"""
	The main command invoked by clients that want to execute commands.

	Chats should go through the back channel, but they will be redirected if they show up here.
	Game commands are allowed through only on the player's turn. (For efficiency, the client
	is programmed to only send commands on its turn). 

	GO_OUT is a special command, which cannot be executed by the game engine (it will give an error
	if it is passed.) It is trapped by the server, which then tests whether the client can go out, and
	if so it queries the partner. All commands and chats are blocked if the server is waiting on a 
	request to go out.
	"""
	if self.pause:
	    return
	self.last_command_time = 0
	client = self.playerlist[str(id)][2]
	if command.action == GO_OUT:
	    if DEBUGGER: print "got go-out ask"
	    self.tryGoOut(id)
	elif (not self.wait_response):
	    if command.action == CHAT:
		self.sendChat(command)
	    elif self.g.turn == self.playerset.index(str(id)):
		self.execCommand(command)

    def sentCommand(self,obj):
	if DEBUGGER: print "successfully sent command",obj

    def errCommand(self,obj):
	if DEBUGGER: print "error sending command",obj

    def remote_takeChat(self, id, command):
	self.last_command_time = 0
	"""
	Back channel for sending chat messages, which does not check turn status.
	Blocked if the server is waiting on a request to go out.
	"""
	client = self.playerlist[str(id)][2]
	if (command.action == CHAT) & (not self.wait_response):
	    self.sendChat(command)

    def remote_Names(self):
	namelist = []
	if self.game_started:
	    ids = self.playerset + self.observerset
	else:
	    ids = self.idlist
	for i in ids:
	    namelist.append(self.playerlist[i][0])
	return namelist

    def remote_assignPlayers(self,id,poslist):
	self.all_computers = True
	if self.playerlist[str(id)][1]:
	    self.playerset = []
	    self.observerset = []
	    names = []
	    positions = [None]*4
	    for index, p in enumerate(poslist):
		try:
		    positions[index] = self.idlist[self.players.index(p)]
		except:
		    pass
	    for index, p in enumerate(positions):
		if p==None:
		    cur_p = ComputerPlayer(index)
		    self.playerset.append(str(index))
		    self.playerlist[str(index)] = ["Computer " + str(index),False,cur_p]
		    names.append("Computer " + str(index))
		else:
		    self.all_computers = False
		    self.playerset.append(p)
		    names.append(poslist[index])
	    for i in self.idlist:
		if i not in positions: 
		    self.observerset.append(i)
		    names.append(self.playerlist[str(i)][0])
	return names

    def remote_Start(self,id,poslist,options):
	"""
	Start a game and initialize all the player positions, inserting computers where no human player
	is specified.
	This function only accepts commands from the controlling client, which is the first client to connect to the server. It is intended that this will always be the local player whose application has launched the
	server as its subprocess.
	"""

	if self.playerlist[str(id)][1]:
	    names = self.remote_assignPlayers(id,poslist)
	    if self.all_computers: 
		options.animation=2000
	    else:
		options.animation=None
	    self.g.gameStart(names,-1,options)
	    print "NAMELIST:",self.g.playernames
	    self.initGame(options)
	    self.initRound()
	    self.initClients()
	    self.game_started = True
	    self.infoChat("Game on!")

    def remote_isReady(self,id):
	"""
	Called by clients between rounds, to indicate that they are ready to start the next round. The server won't initialize the round until every client gives the 'ready' signal.
	"""
	if DEBUGGER: print "got ready",id
	client = self.playerlist[str(id)][2]
	self.players_ready[self.playerset.index(str(id))] = True
	if DEBUGGER: print self.players_ready	

    def remote_Shutdown(self,id):
	client = self.playerlist[str(id)][2]
	controller = self.playerlist[str(id)][1]
	players = self.idlist
	if controller:
	    self.executing = True
	    for p in players:
		player = self.playerlist[str(p)][2]
		controller = self.playerlist[str(p)][1]
		name = self.playerlist[str(p)][0]
		if not isinstance(player,ComputerPlayer):
		    if not controller:
			self.is_closed = False
			if DEBUGGER: print ["killing player",name]
			try:
			    player.callRemote("endGame").addCallbacks(self.isClosed,self.notClosed)
			except:
			    self.notClosed("Dead Client")
			while not self.is_closed:
			    reactor.iterate()
	    self.shut_down = True


    def updateComputers(self,cur_turn):
	"""
	Update the computer players on the results of the last play.

	If this is called more than once between commands, it will result in memory errors in the computer
	players.
	"""
	for turn, p in enumerate(self.playerset):
	    player = self.playerlist[str(p)][2]
	    if isinstance(player,ComputerPlayer):
		if DEBUGGER: print ["updating computer",turn]
		if cur_turn==turn:
		    state = self.g.curState(active=True)
		else:
		    state = self.g.curState(active=False)
		player.readPlay(state)

    def playLocals(self):
	"""
	The server's main computation loop, which runs concurrently with the Twisted reactor loop.

	It continually checks whether it's a computer player's turn, and if so it solicits a command.
	"""

	if self.shut_down:
	    reactor.stop()
	elif self.game_started & (not self.executing) & (not self.g.roundOver) & (not self.pause):
	    self.computing = True
	    if isinstance(self.playerlist[self.playerset[self.g.turn]][2],ComputerPlayer) & (not self.g.roundOver):
		cur_turn = self.g.turn
		play = self.playerlist[self.playerset[self.g.turn]][2].getPlay(self.g.curState())
		if play.action == CHAT:
		    self.sendChat(play)
		else:
		    self.execCommand(play)
	    else:
		self.last_command_time += 1
		if self.last_command_time > TIMEOUT/LOOP_RATE:
		    self.last_command_time = 0
		    for turn, p in enumerate(self.playerset+self.observerset):
			player = self.playerlist[str(p)][2]   	
			if not isinstance(player,ComputerPlayer):
			    try:
				player.callRemote("lookAlive")
			    except:
				self.removeDeadClient(player,p)
	    self.computing = False
	elif self.g.roundOver:
	    self.nextRound()




if __name__ == '__main__':
    game = CanastaServer(sys.argv[2])
    factory = pb.PBServerFactory(game)
    reactor.listenTCP(int(sys.argv[1]), factory)
    computer_loop = LoopingCall(game.playLocals)
    computer_loop.start(LOOP_RATE)
    reactor.run()