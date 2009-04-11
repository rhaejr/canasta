#! /usr/bin/python
# -*- coding: utf-8 -*-
# This file contains all the data objects that are copied over the network between the server and the clients.

from twisted.spread import pb

DEBUGGER = True

VERSION = ['0','2','5']

QUIT_GAME = -999
RESET = -99
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

class CanastaOptions(pb.Copyable,pb.RemoteCopy):
    """
    Object representing possible rule variations.
    """
    def __init__(self, red3penalty=False, initfreeze=False, counttop=False, negpoints=False, megamelds = True,threewilds=False,gonatural=False,concealedfree=False, allowpass=True, runempty=False, piletocanasta=True,pilewithwild=True,freezealways=False,wildmeld=True,wildcanastabonus=[1000,1000],animation=30):
	#Should red 3s count negative if the turn ends before you meld?
	self.red3penalty = red3penalty
	#If the first card turned over after the deal is a wild, does it freeze the pile?
	self.initfreeze = initfreeze
	#Can you count the point value of the top pile card when making an initial meld?
	self.counttop = counttop

	#Allow player to have only one card left and pass turn?
	self.allowpass = allowpass
	#Should going in require only 15 points if you have a negative score?
	self.negpoints = negpoints
	#Always force players to use two naturals to pick the pile?
	self.freezealways = freezealways
	#Allow taking the discard pile by adding the top card to a completed canasta?
	self.piletocanasta = piletocanasta
	#Allow taking the pile with a wild?
	self.pilewithwild = pilewithwild
	#Allow melds of more than 7 cards?
	self.megamelds = megamelds
	#Allow melds of all wilds? the second variable is a list giving the point value of a wild card canasta, and the value if the canasta is all 2s or has all four jokers.
	self.wildmeld = wildmeld
	self.wildcanastabonus = wildcanastabonus
	#Hard limit of three wild cards in a meld? (Only relevant if megamelds=True)
	self.threewilds = threewilds
	#Is the discard pile frozen against you if you haven't melded? (i.e., can you pick it with a wild or not.)
	self.gonatural = gonatural
	#Allow concealed going out without any point requirement?
	self.concealedfree = concealedfree
	#let play continue with pile-picking and an empty stock?
	self.runempty = runempty
	#Animation speed (set to something huge for no animation)
	self.animation = animation

pb.setUnjellyableForClass(CanastaOptions, CanastaOptions)

class CanastaCommand(pb.Copyable,pb.RemoteCopy):
    """
    Command object that is passed to the game object to make a play.
    """
    def __init__(self,action,arglist=[],token=[],retcode=None):
	self.action = action
	self.arglist = arglist
        self.token = token
	self.retcode = retcode

    def hasArguments(self):
	if len(arglist)>0:
	    return True
	else:
	    return False
pb.setUnjellyableForClass(CanastaCommand, CanastaCommand)

class CanastaStatus(pb.Copyable,pb.RemoteCopy):
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
pb.setUnjellyableForClass(CanastaStatus, CanastaStatus)

class CanastaInitStatus(pb.Copyable,pb.RemoteCopy):
    """
    Initial status object, used by the server to synchronize all the client game objects.
    """
    def __init__(self,meldPoints,curLocations,top_loc,frozen,idx,active,playernames,turn,teamscores,turnstart,myPosMelded,concealed,let_go_out):
        self.meldPoints = meldPoints
        self.curLocations = curLocations
	self.top_loc = top_loc
        self.frozen = frozen
	self.idx = idx
	self.playernames = playernames
	self.active = active
	self.turn = turn
	self.teamscores = teamscores

	self.turnstart = turnstart
	self.myPosMelded = myPosMelded
	self.concealed = concealed
	self.let_go_out = let_go_out


pb.setUnjellyableForClass(CanastaInitStatus, CanastaInitStatus)
