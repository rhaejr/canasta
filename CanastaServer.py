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

INFO_STRING = "***"

class CanastaServer(pb.Root):
    def __init__(self,controller_id):
	self.g = CanastaRound(images=False)
	self.playerlist = {}
	self.idlist = []
	self.players = []
	self.game_started = False
	self.players_ready = [False]*4
	self.wait_response = False
	self.executing = False
	self.controller_id = UUID(controller_id)
	self.shut_down = False
	if DEBUGGER: print "server started"

    def remote_debug(self):
	self.g.roundOver=True
	for player in self.playerlist:
	    player[2].callRemote("debug")

    def infoChat(self,message):
	"""
	Send a server informational message to the chat windows of the clients
	"""
	command = CanastaCommand(CHAT,[message],[INFO_STRING])
	self.sendChat(command)

    def remote_joinServer(self, client, name, id, version):
	if version != VERSION:
	    return "Error: incompatible client, this host requires version "+VERSION[0]+"."+VERSION[1]+"."+VERSION[2]
	while name in self.players:
	    name += "_a"
	self.playerlist[id] = [name,False,client]
	if UUID(id) == self.controller_id:
	    self.playerlist[id][1]=True
	self.players.append(name)
	self.idlist.append(id)
	if DEBUGGER: print ["player",name,"joined",id]
	self.infoChat(name+" has arrived.")
	for p in self.idlist:
	    player = self.playerlist[p]
	    player[2].callRemote("updateNames",self.remote_Names())
	return self.playerlist[id][1]

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
	client = self.playerlist[str(id)][2]
	if command.action == GO_OUT:
	    if DEBUGGER: print "got go-out ask"
	    self.tryGoOut(id)
	elif not self.wait_response:
	    if command.action == CHAT:
		self.sendChat(command)
	    elif self.g.turn == self.playerset.index(str(id)):
		self.execCommand(command)

    def sentCommand(self,obj):
	if DEBUGGER: print "successfully sent command",obj
     
    def errCommand(self,obj):
	if DEBUGGER: print "error sending command",obj

    def execCommand(self,command):
	"""
	Excute a game command both locally and on the client players.

	If the round is over, update scores and prepare to wait for the clients.
	"""
	self.executing = True
	cur_turn = self.g.turn
	self.g.execCode(command)
	if DEBUGGER: print ["server executed",self.g.lastCommand,self.g.lastReturn]
	for turn, p in enumerate(self.playerset):
	    player = self.playerlist[str(p)][2]
	    if isinstance(player,ComputerPlayer):
		pass
	    elif self.g.lastReturn:
		player.callRemote("readCommand",command).addCallbacks(self.sentCommand,self.errCommand)
	if self.g.lastReturn:
	    self.updateComputers(cur_turn)
	if self.g.roundOver:
	    if self.g.lastReturn:
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
	self.executing = False

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
	elif self.game_started & (not self.executing):
	    if isinstance(self.playerlist[self.playerset[self.g.turn]][2],ComputerPlayer) & (not self.g.roundOver):
		cur_turn = self.g.turn
		play = self.playerlist[self.playerset[self.g.turn]][2].getPlay(self.g.curState())
		if play.action == CHAT:
		    self.sendChat(play)
		else:
		    self.execCommand(play)
	    elif self.g.roundOver:
		self.nextRound()

    def remote_takeChat(self, id, command):
	"""
	Back channel for sending chat messages, which does not check turn status.
	Blocked if the server is waiting on a request to go out.
	"""
	client = self.playerlist[str(id)][2]
	if (command.action == CHAT) & (not self.wait_response):
	    self.sendChat(command)

    def sendChat(self,command):
	"""
	Sends a chat message to all clients.
	"""
	self.g.execCode(command)
	if DEBUGGER: print [self.g.lastCommand,self.g.lastReturn]
	if self.game_started:
	    players = self.playerset
	else:
	    players = self.idlist
	for p in players:
	    player = self.playerlist[str(p)][2]
	    if not isinstance(player,ComputerPlayer):
		player.callRemote("readCommand",command)

    def notClosed(self,obj):
	if DEBUGGER: print ["Client did not close correctly",obj]
	self.is_closed = True

    def isClosed(self,obj):
	if DEBUGGER: print ["Client closed correctly",obj]
	self.is_closed = True

    def remote_Shutdown(self,id):
	client = self.playerlist[str(id)][2]
	controller = self.playerlist[str(id)][1]
	if self.game_started:
	    players = self.playerset
	else:
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

    def remote_Names(self):
	namelist = []
	for i in self.idlist:
	    namelist.append(self.playerlist[i][0])
	return namelist

    def remote_Start(self,client,poslist,options):
	"""
	Start a game and initialize all the player positions, inserting computers where no human player
	is specified.
	This function only accepts commands from the controlling client, which is the first client to connect to the server. It is intended that this will always be the local player whose application has launched the
	server as its subprocess.
	"""

	if self.playerlist[str(client)][1]:
	    self.playerset = []
	    self.observerset = []
	    names = []
	    positions = [None]*4
	    for index, p in enumerate(poslist):
		try:
		    positions[index] = self.idlist[self.players.index(p)]
		except:
		    pass
	    for p in self.playerlist:
		if p[0] not in self.players:
		    self.observerset.append(p)	    
	    for index, p in enumerate(positions):
		if p==None:
		    cur_p = ComputerPlayer(index)
		    self.playerset.append(str(index))
		    self.playerlist[str(index)] = ["Computer " + str(index),False,cur_p]
		    names.append("Computer " + str(index))
		else:
		    self.playerset.append(p)
		    names.append(poslist[index])
	    self.g.gameStart(names,-1,options)
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

    def nextRound(self):
	"""
	Start the next round. Reset the scores if someone went over 5000 in the last round.
	"""
	if not(False in self.players_ready):
	    if DEBUGGER: print "initializing the next round"
	    if ((self.g.team1score>5000) | (self.g.team2score>5000)) & (self.g.team1score != self.g.team2score):
		self.newGame()
	    self.initRound()
	    self.initClients()

    def newGame(self):
	"""
	Tell the clients that a new game is starting, so they should reset their scores.
	"""
	self.g.newGame()
	for pos, p in enumerate(self.playerset):
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
	for pos, p in enumerate(self.playerset):
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

    def initClients(self):
	"""
	Initialize the round by sending the clients an object describing the deal. After this is called, all game objects held by the server and the clients should be in an identical state.
	"""
	for pos, p in enumerate(self.playerset):
	    player = self.playerlist[p][2]
	    if isinstance(player,ComputerPlayer):
		player.initRound(self.g.initStatus())
	    else:
		if DEBUGGER: print "starting the client round"
		player.callRemote("initRound")
		if DEBUGGER: print "initializing the cards"
		status = self.g.initStatus()
		player.callRemote("readInit",status)
	self.players_ready = [False]*4

if __name__ == '__main__':
    game = CanastaServer(sys.argv[2])
    factory = pb.PBServerFactory(game)
    reactor.listenTCP(int(sys.argv[1]), factory)
    computer_loop = LoopingCall(game.playLocals)
    computer_loop.start(0.05)
    reactor.run()