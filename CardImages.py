# -*- coding: utf-8 -*-

import os, pygame,math
from pygame.locals import *
                             
class CardImages:

    S = 0
    C = 1
    D = 2
    H = 3
    
    cardImages = []
    cardColors = []
    cardValues = []
    backImage = None

    def __init__(self,images=True):
    
        colors = ['s','c','d','h']
        values = ['a','2','3','4','5','6','7','8','9','t','j','q','k']
        canastacol = [14,0,-1,4,5,6,7,8,9,10,11,12,13,14,0,-1,4,5,6,7,8,9,10,11,12,13,14,0,100,4,5,6,7,8,9,10,11,12,13,14,0,100,4,5,6,7,8,9,10,11,12,13,0,0,0,0]
        canastavals = [20,20,5,5,5,5,5,10,10,10,10,10,10,20,20,5,5,5,5,5,10,10,10,10,10,10,20,20,100,5,5,5,5,10,10,10,10,10,10,20,20,100,5,5,5,5,10,10,10,10,10,10,50,50,50,50]
	self.images=images

        for c in colors:
            for v in values:
		if images:
		    self.cardImages.append(pygame.image.load("./cards/%s%s.gif" % (v,c)).convert())
		else:
		    self.cardImages.append([c,v])
		self.cardColors.append(c)
		self.cardValues.append(v)
	
	if images:
	    self.cardImages.append(pygame.image.load("./cards/j.gif"))
	    self.cardImages.append(pygame.image.load("./cards/j.gif"))
	    self.cardImages.append(pygame.image.load("./cards/j.gif"))
	    self.cardImages.append(pygame.image.load("./cards/j.gif"))
	else:
	    self.cardImages.append(["Jo","Jo"])
	    self.cardImages.append(["Jo","Jo"])
	    self.cardImages.append(["Jo","Jo"])
	    self.cardImages.append(["Jo","Jo"])
        self.cardColors.append("Jo")
	self.cardColors.append("Jo")
	self.cardValues.append("Jo")
        self.cardValues.append("Jo")
        self.cardColors.append("Jo")
	self.cardColors.append("Jo")
	self.cardValues.append("Jo")
        self.cardValues.append("Jo")

	if images:
	    self.backImage = pygame.image.load("./cards/b.gif")
	else:
	    self.backImage = None

	self.cardCanColors = canastacol
	self.cardCanValues = canastavals

        #colors = ['spade','club','diamond','heart']
        #values = ['1','2','3','4','5','6','7','8','9','10','jack','queen','king']

        #for c in colors:
        #    for v in values:
        #        self.cardImages.append(pygame.image.load("./CardPng/%s_%s.png" % (v,c)))

        #self.backImage = pygame.image.load("./CardPng/back.png")


    def getCard(self,color,value):
        return self.cardImages[(color*13)+(value-1)]

    def getCardNbr(self,nbr):
        return self.cardImages[nbr]

    def getBack(self):
        return self.backImage
    
    def getColors(self,nbr):
	return self.cardColors[nbr]

    def getValues(self,nbr):
	return self.cardValues[nbr]

    def getCanColors(self,nbr):
	return self.cardCanColors[nbr]

    def getCanValues(self,nbr):
	return self.cardCanValues[nbr]
