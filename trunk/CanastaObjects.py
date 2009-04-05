#! /usr/bin/python
# -*- coding: utf-8 -*-

from twisted.spread import pb

DEBUGGER = True

QUIT_GAME = -999
GO_OUT = -777
BLOCK_OUT = -770
PASS_TURN = -1

NO_PLAY = 0

DRAW_CARD = 1
DISCARD_CARD = 2
tlist = range(4,16)
TLIST = range(4,16)
CLEAR_STAGE = 20
MELD_CARDS = 100
PICK_PILE = 110
TO_STAGE = 200
RESIZE = 666
CHAT = 777
SELECT_CARD = 999

DEBUG = 7171

PRE_DRAW = 0
POST_DRAW = 1

CARD_KEYS = [52,53,54,55,56,57,116,106,113,107,97,119]

IN_PILE = 1
IS_WILD = 0

class CanastaOptions:
    """
    Command object that is passed to the game object to make a play.
    """
    def __init__(self, red3penalty=False, initfreeze=False, counttop=False):
	self.red3penalty = red3penalty
	self.initfreeze = initfreeze
	self.counttop = counttop

class CanastaCommand:
    """
    Command object that is passed to the game object to make a play.
    """
    def __init__(self,action,arglist,token,retcode=None):
	self.action = action
	self.arglist = arglist
        self.token = token
	self.retcode = retcode

    def hasArguments(self):
	if len(arglist)>0:
	    return True
	else:
	    return False

class CanastaStatus:
    """
    Game status object to be read by computer players.
    """
    def __init__(self,meldPoints,turn,turnState,selected,curLocations,lastMelded,numcards,frozen,roundover,lastCommand,lastReturn,lastArgs,lastToken):
        self.meldPoints = meldPoints
        self.curTurn = turn
        self.turnState = turnState
	self.selected = selected
        self.curLocations = curLocations
	self.lastMelded = lastMelded
        self.numCards = numcards
        self.frozen = frozen
	self.roundOver = roundover
        self.lastCommand = lastCommand
        self.lastReturn = lastReturn
        self.lastArgs = lastArgs
        self.lastToken = lastToken

    def cardsSelected(self):
	if len(self.arglist)>0:
	    return True
	else:
	    return False

class CanastaInitStatus:
    """
    Initial status object, used by the server to synchronize all the client game objects.
    """
    def __init__(self,meldPoints,curLocations,frozen,idx,red3penalty,initfreeze,counttop,active,playernames):
        self.meldPoints = meldPoints
        self.curLocations = curLocations
        self.frozen = frozen
	self.idx = idx
	self.red3penalty = red3penalty
	self.initfreeze = initfreeze
	self.counttop = counttop
	self.playernames = playernames
	self.active = active

class CopyCanastaOptions(CanastaOptions, pb.Copyable):
    pass

class ReceiverCanastaOptions(pb.RemoteCopy, CanastaOptions):
    pass

pb.setUnjellyableForClass(CopyCanastaOptions, ReceiverCanastaOptions)

class CopyCanastaInitStatus(CanastaInitStatus, pb.Copyable):
    pass

class ReceiverCanastaInitStatus(pb.RemoteCopy, CanastaInitStatus):
    pass

pb.setUnjellyableForClass(CopyCanastaInitStatus, ReceiverCanastaInitStatus)

class CopyCanastaCommand(CanastaCommand, pb.Copyable):
    pass

class ReceiverCanastaCommand(pb.RemoteCopy, CanastaCommand):
    pass

pb.setUnjellyableForClass(CopyCanastaCommand, ReceiverCanastaCommand)

class CopyCanastaStatus(CanastaStatus, pb.Copyable):
    pass

class ReceiverCanastaStatus(pb.RemoteCopy, CanastaStatus):
    pass

pb.setUnjellyableForClass(CopyCanastaStatus, ReceiverCanastaStatus)
