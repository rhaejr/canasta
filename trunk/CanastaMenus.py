# -*- coding: utf-8 -*-
#Import Modules
import pygame
from pygame.locals import *
import time
import math
 
# import gui stuff
import gui
from gui import *
import defaultStyle
from CanastaObjects import *

screenSize = (1024,768)
lines = []
lineLimit = 20

SPLASH = 0
ONE_PLAYER = 1
NETWORK_SERVER = 2
NETWORK_CLIENT = 3

class SetOptions:

    def __init__(self):
	pygame.init() 
	self.screen = pygame.display.set_mode((1024,768))
	pygame.display.set_caption('Canasty - version '+VERSION[0]+"."+VERSION[1]+"."+VERSION[2])

	self.clock = pygame.time.Clock()
	self.back = pygame.image.load("./cards/titlescreen.gif").convert()
	self.settings = CanastaOptions()

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

    def netclient(self):
	"""
	Get necessary information to launch a client and connect to a remote server.
	"""  
	self.done = False

	def OKOnClick(button):
	    self.done = True
	    self.save = True
	def cancelOnClick(button):
	    self.done = True
	    self.save = False

	defaultStyle.init(gui)
	desktop_main = Desktop()
	desktop = Window(position = (300,220), size = (400,200), parent = desktop_main, text = "Join Network Game", shadeable = False)
	labelStyleCopy = gui.defaultLabelStyle.copy()
	desktop.onClose = cancelOnClick

	label = Label(position = (100,40),size = (200,0), parent = desktop, text = "Enter a name and server location:", style = labelStyleCopy)

	label = Label(position = (100,70),size = (50,0), parent = desktop, text = "Name", style = labelStyleCopy)
	name_txt = TextBox(position = (150,70), size = (100, 0), parent = desktop, text = "noname")
	label = Label(position = (100,95),size = (50,0), parent = desktop, text = "Host", style = labelStyleCopy)
	host_txt = TextBox(position = (150,95), size = (200, 0), parent = desktop, text = "localhost")
	label = Label(position = (100,120),size = (50,0), parent = desktop, text = "Port", style = labelStyleCopy)
	port_txt = TextBox(position = (150,120), size = (50, 0), parent = desktop, text = "7171")

	OK_button = Button(position = (100,170), size = (50,0), parent = desktop, text = "OK")
	cancel_button = Button(position = (200,170), size = (50,0), parent = desktop, text = "Cancel")

	OK_button.onClick = OKOnClick
	cancel_button.onClick = cancelOnClick

	while not self.done:

	    #Handle Input Events
	    for event in gui.setEvents():
		if event.type == QUIT:
		    return
		elif event.type == KEYDOWN and event.key == K_ESCAPE:
		    return
		elif event.type == KEYDOWN and event.key == 9:
		    if desktop_main.focused is name_txt:
			desktop_main.focused=host_txt
		    elif desktop_main.focused is host_txt:
			desktop_main.focused=port_txt
		    else :
			desktop_main.focused=name_txt

		    name_txt.needsRefresh = True
		    host_txt.needsRefresh = True
		    port_txt.needsRefresh = True
		elif event.type == KEYDOWN and event.key == 13:
		    OKOnClick(None)
		else:
		    desktop_main.update()
	    self.Draw(desktop_main)

	if self.save:
	    return [name_txt.text, host_txt.text,int(port_txt.text)]
	else:
	    return

    def netserver(self):
	"""
	Get necessary information to launch a server and wait for remote clients.
	"""  
	self.done = False

	def OKOnClick(button):
	    self.done = True
	    self.save = True
	def cancelOnClick(button):
	    self.done = True
	    self.save = False

	defaultStyle.init(gui)
	defaultStyle.init(gui)
	desktop_main = Desktop()
	desktop = Window(position = (300,220), size = (400,200), parent = desktop_main, text = "Start Network Game", shadeable = False)
	desktop.onClose = cancelOnClick

	labelStyleCopy = gui.defaultLabelStyle.copy()

	Label(position = (100,50),size = (200,0), parent = desktop, text = "Enter a name and server location:", style = labelStyleCopy)

	Label(position = (100,75),size = (50,0), parent = desktop, text = "Name", style = labelStyleCopy)
	name_txt = TextBox(position = (150,75), size = (100, 0), parent = desktop, text = "noname")
	Label(position = (100,100),size = (50,0), parent = desktop, text = "Port", style = labelStyleCopy)
	port_txt = TextBox(position = (150,100), size = (50, 0), parent = desktop, text = "7171")

	OK_button = Button(position = (100,150), size = (50,0), parent = desktop, text = "OK")
	cancel_button = Button(position = (200,150), size = (50,0), parent = desktop, text = "Cancel")

	OK_button.onClick = OKOnClick
	cancel_button.onClick = cancelOnClick

	while not self.done:

	    #Handle Input Events
	    for event in gui.setEvents():
		if event.type == QUIT:
		    return
		elif event.type == KEYDOWN and event.key == K_ESCAPE:
		    return
		elif event.type == KEYDOWN and event.key == 9:
		    print desktop_main.focused is name_txt
		    if desktop_main.focused is name_txt:
			desktop_main.focused=port_txt
		    else :
			desktop_main.focused=name_txt
		    name_txt.needsRefresh = True
		    port_txt.needsRefresh = True
		elif event.type == KEYDOWN and event.key == 13:
		    OKOnClick(None)
		else:
		    desktop_main.update()
	    self.Draw(desktop_main)

	if self.save:
	    return [name_txt.text,port_txt.text]
	else:
	    return

    def Options(self,options):
	"""
	Set gameplay options.
	"""  
	self.done = False

	def OKOnClick(button):
	    self.done = True
	    self.save = True
	def cancelOnClick(button):
	    self.done = True
	    self.save = False
	def onChkValueChanged(chk):
	    meldbonus1_txt.enabled = chk.value
	    meldbonus2_txt.enabled = chk.value
	def animateChkValueChanged(chk):
	    animate_txt.enabled = chk.value

	defaultStyle.init(gui)
	desktop_main = Desktop()
	desktop = Window(position = (250,200), size = (600,400), parent = desktop_main, text = "Options", shadeable = False)
	desktop.onClose = cancelOnClick

	labelStyleCopy = gui.defaultLabelStyle.copy()

	red3penalty_chk = CheckBox(position = (20,225), size = (200,0), parent = desktop, text = "Red 3 Penalty", value = options.red3penalty)
	initfreeze_chk = CheckBox(position = (20,50), size = (200,0), parent = desktop, text = "Allow freeze on opening", value = options.initfreeze)
	counttop_chk = CheckBox(position = (20,75), size = (200,0), parent = desktop, text = "Count pile card points in melds", value = options.counttop)
	allowpass_chk = CheckBox(position = (20,100), size = (200,0), parent = desktop, text = "Allow passing with one card", value = options.allowpass)
	negpoints_chk = CheckBox(position = (20,125), size = (200,0), parent = desktop, text = "No point threshold with negative score", value = options.negpoints)
	concealedfree_chk = CheckBox(position = (20,150), size = (200,0), parent = desktop, text = "No minimum for concealed going out", value = options.concealedfree)
	piletocanasta_chk = CheckBox(position = (20,175), size = (200,0), parent = desktop, text = "Allow melding pile card with existing meld", value = options.piletocanasta)
	pilewithwild_chk = CheckBox(position = (20,200), size = (200,0), parent = desktop, text = "Allow matching unfrozen pile with a wild", value = options.pilewithwild)

	megamelds_chk = CheckBox(position = (350,225), size = (200,0), parent = desktop, text = "Melds of more than 7 cards", value = options.megamelds)
	wildmeld_chk = CheckBox(position = (350,50), size = (200,0), parent = desktop, text = "Wild card melds", value = options.wildmeld)
	wildmeld_chk.onValueChanged = onChkValueChanged
	Label(position = (400,75),size = (50,0), parent = desktop, text = "Wild card canasta value", style = labelStyleCopy)
	meldbonus1_txt = TextBox(position = (350,75), size = (40, 0), parent = desktop, text = "1000")
	Label(position = (400,100),size = (50,0), parent = desktop, text = "If 0 or 4 Jokers", style = labelStyleCopy)
	meldbonus2_txt = TextBox(position = (350,100), size = (40, 0), parent = desktop, text = "1000")

	threewilds_chk = CheckBox(position = (350,125), size = (200,0), parent = desktop, text = "Limit 3 wilds in a meld", value = options.threewilds)
	gonatural_chk = CheckBox(position = (350,150), size = (200,0), parent = desktop, text = "Pile frozen before initial meld", value = options.gonatural)
	freezealways_chk = CheckBox(position = (350,175), size = (200,0), parent = desktop, text = "Pile always frozen", value = options.freezealways)
	runempty_chk = CheckBox(position = (350,200), size = (200,0), parent = desktop, text = "Continued play with no stock", value = options.runempty)

	animate_chk = CheckBox(position = (250,270), size = (100,0), parent = desktop, text = "Animate cards?", value = options.wildmeld)
	animate_chk.onValueChanged = animateChkValueChanged
	Label(position = (250,295),size = (50,0), parent = desktop, text = "Speed:", style = labelStyleCopy)
	animate_txt = TextBox(position = (310,295), size = (40, 0), parent = desktop, text = "30")

	OK_button = Button(position = (200,370), size = (50,0), parent = desktop, text = "OK")
	cancel_button = Button(position = (400,370), size = (50,0), parent = desktop, text = "Cancel")

	OK_button.onClick = OKOnClick
	cancel_button.onClick = cancelOnClick

	while not self.done:

	    #Handle Input Events
	    for event in gui.setEvents():
		if event.type == QUIT:
		    return
		elif event.type == KEYDOWN and event.key == K_ESCAPE:
		    return
		elif event.type == KEYDOWN and event.key == 13:
		    OKOnClick(None)
	    desktop_main.update()
	    self.Draw(desktop_main)

	if not animate_chk.value:
	    animation = 10000
	else:
	    try: animation = int(animate_txt.text)
	    except: animation = 30
	    if animation <1:
		animation = 1

	if self.save:
	    try: meldbonus1 = int(meldbonus1_txt.text)
	    except: meldbonus1 = 1000

	    try: meldbonus2 = int(meldbonus1_txt.text)
	    except: meldbonus2 = 1000

	    return CanastaOptions(red3penalty_chk.value,initfreeze_chk.value,counttop_chk.value,negpoints_chk.value,megamelds_chk.value,threewilds_chk.value,gonatural_chk.value,concealedfree_chk.value,allowpass_chk.value,runempty_chk.value,piletocanasta_chk.value,pilewithwild_chk.value,freezealways_chk.value,wildmeld_chk.value,[int(meldbonus1),int(meldbonus2)],animation)
	else:
	    return options

    def Draw(self, desktop):

	"""
	Generic draw function for the pre-game menu GUIs.
	"""

	self.screen.fill((0,0,255))    
	self.screen.blit(self.back, (0,0))
	self.screen.blit(self.titletext,self.titlepos)
	self.screen.blit(self.titletext2,self.titlepos2)
	self.screen.blit(self.titletext3,self.titlepos3)
	self.screen.blit(self.titletext4,self.titlepos4)

	try:
	    desktop.draw()
	except:
	    pass

	#Flips!
	pygame.display.flip()

    def SplashScreen(self):  

	"""
	Present the opening screen and return the type of game the user wants.

	Also handles setting game options.
	"""

	self.Draw(None)

	while True: 
	    for event in pygame.event.get():
		if event.type == QUIT:
		    return QUIT_GAME
		elif event.type == KEYDOWN and event.key == K_ESCAPE:
		    return QUIT_GAME
		elif (event.type == MOUSEBUTTONUP):
		    if (event.pos[0] < (self.titlepos[0]+self.titlepos[1])) & (event.pos[0] > self.titlepos[0]) & (event.pos[1] < (self.titlepos[1]+self.titlepos[3])) & (event.pos[1] > self.titlepos[1]):
			return ONE_PLAYER
		    if (event.pos[0] < (self.titlepos2[0]+self.titlepos2[1])) & (event.pos[0] > self.titlepos2[0]) & (event.pos[1] < (self.titlepos2[1]+self.titlepos2[3])) & (event.pos[1] > self.titlepos2[1]):
			return NETWORK_SERVER
		    if (event.pos[0] < (self.titlepos3[0]+self.titlepos3[1])) & (event.pos[0] > self.titlepos3[0]) & (event.pos[1] < (self.titlepos3[1]+self.titlepos3[3])) & (event.pos[1] > self.titlepos3[1]):
			return NETWORK_CLIENT
		    if (event.pos[0] < (self.titlepos4[0]+self.titlepos4[1])) & (event.pos[0] > self.titlepos4[0]) & (event.pos[1] < (self.titlepos4[1]+self.titlepos4[3])) & (event.pos[1] > self.titlepos4[1]):
			optset = self.Options(self.settings)
			if optset:
			    self.settings = optset
			return SPLASH