# -*- coding: utf-8 -*-
#/usr/bin/python
              
import os, sys, pygame, math, subprocess
sys.path.append(os.path.split(sys.path[0])[0])
from pygame.locals import *
import random
import re
from time import sleep
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from uuid import uuid4

from CardImages import CardImages
from CardGroup import CardGroup
from Card import Card
from CanastaRound import CanastaRound
from ComputerPlayer import ComputerPlayer
from HumanPlayer import HumanPlayer
from CanastaMenus import SetOptions
from CanastaClient import CanastaClient
from CanastaServer import CanastaServer
from CanastaObjects import *

SPLASH = 0
ONE_PLAYER = 1
NETWORK_SERVER = 2
NETWORK_CLIENT = 3

#Ultra simple computer player. Just draws a card and then discards at random.
def dummyPlayer(status):

    args = []

    if status.turnState == PRE_DRAW:
	action = DRAW_CARD
    if (len(status.selected) != 1 & status.turnState == POST_DRAW):
	action = SELECT_CARD
	args = [random.randrange(1,13)]
    if (len(status.selected) == 1 & status.turnState == POST_DRAW):
	action = DISCARD_CARD

    output = CanastaCommand(action,args)

    return output

def main():
    """
    The main game program. This is not a main loop; rather, after setting up the appropriate game settings, 
    this routine launches a server in a subprocess if necessary, and then turns execution over to a client
    running as a Twisted reactor.
    """

    pygame.init() 

    game_type = SPLASH
    options = SetOptions()

    while game_type == SPLASH:
	game_type = options.SplashScreen()

	if game_type == NETWORK_SERVER:

	    args = options.netserver()
	    if not args:
		game_type = SPLASH
	    else:
		name,port = args

	if game_type == NETWORK_CLIENT:	    
	    connected = False
	    while not connected:
		try:
		    client = CanastaClient(args[0],options.settings)
		    reactor.connectTCP(args[1],args[2], client.factory)
		    client.factory.getRootObject().addCallbacks(client.Connect,client.failConnect)
		    if client.cancel:
			game_type = SPLASH
			connected = True
			client.cancel = False
		    else:
			connected = True
		except:
		    args = options.netclient()
		    if not args:
			game_type = SPLASH
			connected = True


    if game_type == QUIT_GAME:
	return

    def isConnected():
	connected = True

    def notConnected():
	sleep(1)

    if game_type == ONE_PLAYER:

	client = CanastaClient("Player",options.settings)
	proc = subprocess.Popen(['python', 'CanastaServer.py','7171', str(client.id)])

    if game_type == NETWORK_SERVER:

	name,port = args

	client = CanastaClient(name,options.settings,server=True)

	proc = subprocess.Popen(['python', 'CanastaServer.py', port, str(client.id)])

	client.port = int(port)
	reactor.connectTCP("localhost", int(port), client.factory)
	client.factory.getRootObject().addCallbacks(client.Connect,client.failConnect)

    if game_type == ONE_PLAYER:
	reactor.connectTCP("localhost",7171, client.factory)
	client.player_positions = ["Player",None,None,None]
	client.factory.getRootObject().addCallbacks(client.Connect,client.failConnect)
	client.factory.getRootObject().addCallbacks(client.startServer,client.failStart)

    player_input = LoopingCall(client.getInput)
    player_input.start(0.01)

    print "running client reactor"

    reactor.run()

    return
              
#this calls the 'main' function when this script is executed
if __name__ == '__main__': main()

pygame.quit()
