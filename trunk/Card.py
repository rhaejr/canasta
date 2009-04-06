# -*- coding: utf-8 -*-
import os, pygame,math
from pygame.locals import *
                             
class Card:

    def __init__(self,frontImage,backImage,col,val,cancol,canval,images,x=0,y=0):
        self.bimg = backImage
        self.fimg = frontImage
        self.img = backImage
        self.side = 0
	if images:
	    self.rect = self.img.get_rect()
	    self.rect.x = x
	    self.rect.y = y
	    self.x = x
	    self.y = y
	else:
	    self.rect = None
	self.curx = x
	self.cury = y
        self.color = col
        self.value = val
        self.cancolor = cancol
        self.canvalue = canval
        self.child = None
        self.parent = None
        self.selected = 0
        self.location = 0
        self.rotated = 0
        self.temp = 0
        self.isTop = False

	self.images = images

    def flip(self):
	if not self.images:
	    return
        if self.side==1:
            self.side = 0
            self.img = self.bimg
        else:
            self.side = 1
            self.img = self.fimg

    def backSide(self):
	if not self.images:
	    return
        self.side = 0
        self.img = self.bimg

    def frontSide(self):
	if not self.images:
	    return
        self.side = 1
        self.img = self.fimg

    def setSide(self,side):
	if not self.images:
	    return
        if side:
            self.img = self.fimg
        else:
            self.img = self.bimg
        self.side = side
       
    def move(self,dx,dy):
	if not self.images:
	    return
        self.rect.x += dx
        self.rect.y += dy
	self.x += dx
	self.y += dy
        if self.child:
            self.child.move(dx,dy)

    def draw(self,surface):
	if not self.images:
	    return
        surface.blit(self.img,self.rect.topleft)

    def turn(self):
	if not self.images:
	    return
	elif self.rotated==1:
	    self.img = pygame.transform.rotate(self.img,90)
	    self.rotated = 0
	else:
	    self.img = pygame.transform.rotate(self.img,-90)
	    self.rotated = 1
