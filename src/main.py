#!/usr/bin/env python3

import gpiozero as gz
from luma.lcd.device import st7735 as luma_st7735
from luma.core.interface.serial import spi as luma_spi
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite
from PIL import ImageFont, ImageColor

import sys
import time
import signal
import widgets
import numpy as np
import atexit
import json
import glob

KEY_UP_PIN     = 6
KEY_DOWN_PIN   = 19
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_PRESS_PIN  = 13
KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16


class Capture:
  def __init__(self):
    self.captured = []
  def __eq__(self, other):
    self.captured.append(other)
    return False


class HardwareController( object ) :
  def __init__( self ) :
    self.spi_    = luma_spi(
                            port=0,
                            device=0,
                            bus_speed_hz=16000000,
                            cs_high=False,
                            transfer_size=4096,
                            gpio_DC=25,
                            gpio_RST=27
                           )
      
    self.device_ = luma_st7735(
                               #gpio_LIGHT=24,  #this is failing, idk why
                               #pwm_frequency=200,
                               serial_interface=self.spi_,
                               width=128,
                               height=128,
                               bgr=True,
                               h_offset=1,
                               v_offset=2
                              )
    #self.device_ = luma_device.get_device( config )
    self.buttons_ = {}
    self.buttons_[ "up"    ] = gz.Button(  6, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "down"  ] = gz.Button( 19, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "left"  ] = gz.Button(  5, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "right" ] = gz.Button( 26, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "press" ] = gz.Button( 13, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "key1"  ] = gz.Button( 21, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "key2"  ] = gz.Button( 20, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "key3"  ] = gz.Button( 16, bounce_time=0.05, hold_time=1, hold_repeat=True )
    
    self.buttonMap_ = {}
    self.buttonMap_[  6 ] = "up"
    self.buttonMap_[ 19 ] = "down"
    self.buttonMap_[  5 ] = "left"
    self.buttonMap_[ 26 ] = "right"
    self.buttonMap_[ 13 ] = "press"
    self.buttonMap_[ 21 ] = "key1"
    self.buttonMap_[ 20 ] = "key2"
    self.buttonMap_[ 16 ] = "key3"

    self.frameReg_ = luma_sprite.framerate_regulator( fps=30 )

class Renderer( object ) :
  def __init__( self, ctrl, model ) :
    self.hwctrl_ = ctrl
    self.model_  = model
    self.font_   = ImageFont.truetype( "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size=8 )
    
    self.hwctrl_.buttons_[ "up"    ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "down"  ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "left"  ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "right" ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "key3"  ].when_pressed = self.buttonPress

    # Widgets
    self.mainWidgets_ = {}
    self.mainWidgets_[ "PreviewGraph" ] = widgets.Graph( x=38, y=44, width=84, height=84 )
    self.mainWidgets_[ "PreviewGraph" ].gridPxIncx_ = 8
    self.mainWidgets_[ "PreviewGraph" ].gridPxIncy_ = 8
    self.mainWidgets_[ "Settings"     ] = widgets.TextBox( "Settings", "darkgreen", 1, 5,  0,  0, 43, 16, self.font_, 1 )
    self.mainWidgets_[ "Configs"      ] = widgets.TextBox( "Edit",     "darkgreen", 4, 5, 44,  0, 27, 16, self.font_, 1 )
    self.mainWidgets_[ "Manual"       ] = widgets.TextBox( "Devs",     "darkgreen", 4, 5, 72,  0, 27, 16, self.font_, 1 )
    self.mainWidgets_[ "Help"         ] = widgets.TextBox( "Help",     "darkgreen", 4, 5, 100, 0, 27, 16, self.font_, 1 )

    for name, widget in self.mainWidgets_.items() :
      widget.name_ = name
      widget.fg_ = "green"
      widget.bg_ = ImageColor.getrgb( "#1f0f0f" )
      widget.activeFg_       = "white"
      widget.activeBg_       = "black"
      
    self.mainWidgets_["PreviewGraph"].link( "left",  self.mainWidgets_["Settings"] )
    
    self.mainWidgets_["Settings"    ].link( "right", self.mainWidgets_["PreviewGraph"] )
    self.mainWidgets_["Configs"     ].link( "right", self.mainWidgets_["PreviewGraph"] )
    self.mainWidgets_["Manual"      ].link( "right", self.mainWidgets_["PreviewGraph"] )
    self.mainWidgets_["Help"        ].link( "right", self.mainWidgets_["PreviewGraph"] )

    self.mainWidgets_["Settings"    ].link( "down",  self.mainWidgets_["Configs"] )
    self.mainWidgets_["Configs"     ].link( "up",    self.mainWidgets_["Settings"] )

    self.mainWidgets_["Configs"     ].link( "down",  self.mainWidgets_["Manual"] )
    self.mainWidgets_["Manual"      ].link( "up",    self.mainWidgets_["Configs"] )

    self.mainWidgets_["Manual"      ].link( "down",  self.mainWidgets_["Help"] )
    self.mainWidgets_["Help"        ].link( "up",    self.mainWidgets_["Manual"] )

    self.mainWidgets_["Help"        ].link( "down",  self.mainWidgets_["Settings"] )
    self.mainWidgets_["Settings"    ].link( "up",    self.mainWidgets_["Help"] )
    
    self.quit_ = False

    self.currentContext_ = "main"
    
    self.contexts_ = {}
    # Contexts as : func(), current widget, default widget
    self.contexts_[ "main" ]       = [ self.main, None, self.mainWidgets_["Settings"] ]
    self.contexts_[ "settings" ]   = [ self.settings, None, None ]
    self.contexts_[ "configs" ]    = [ self.configs, None, None ]
    self.contexts_[ "edit"    ]    = [ self.edit, None, None ]
    self.contexts_[ "run"     ]    = [ self.run, None, None ]

  def main( self, canvas ) :
    
    for name, widgets in self.mainWidgets_.items() :
      widgets.draw( canvas )
      
    if len( self.model_.configs_ ) > 0 :
      if self.model_.configs_[0].datasets_["zaxis"] :
        data = np.array( ( self.model_.configs_[0].datasets_["zaxis"].time_,
                           self.model_.configs_[0].datasets_["zaxis"].value_ ) )
        self.mainWidgets_[ "PreviewGraph" ].drawData( data, 10, 10, "blue", "red" )
        
  def settings( self, canvas ) :
    pass
  def configs( self, canvas ) :
    pass
  def edit( self, canvas ) :
    pass
  def run( self, canvas ) :
    pass
    
  
  def buttonPress( self, button ) :
    pressType = self.hwctrl_.buttonMap_[ button.pin.number ] 
    print( "You pressed " + pressType )

    if self.contexts_[ self.currentContext_ ][1] is None :
      # Assign default
      self.contexts_[ self.currentContext_ ][1] = self.contexts_[ self.currentContext_ ][2]
      self.contexts_[ self.currentContext_ ][1].select()

    #  We have an active widget
    else: #self.contexts_[ self.currentContext_ ][1] is not None :
      if not self.contexts_[ self.currentContext_ ][1].hasFocus() :
        newCurrentWidget = self.contexts_[ self.currentContext_ ][1].getLink( pressType )
        if newCurrentWidget is not None :
          self.contexts_[ self.currentContext_ ][1] = newCurrentWidget
      else :
        # Widget has focus from main control method, go to its handler
        self.contexts_[ self.currentContext_ ][1].onInput( pressType )

    self.render()

  def quit( self ) :
    return self.quit_
      
  def render( self ) :

    with self.hwctrl_.frameReg_ :
      with luma_render.canvas( self.hwctrl_.device_, dither=True ) as canvas :
        self.contexts_[ self.currentContext_ ][0]( canvas )
        if self.contexts_[ self.currentContext_ ][1] is not None :
          print( "Active Widget is : " + self.contexts_[ self.currentContext_ ][1].name_ ) 
          
        

class DataSet( object ) :
  def __init__( self, name ) :
    self.name_  = name
    self.time_  = np.zeros( (0) )
    self.value_ = np.zeros( (0) )
    
        
class Configuration( object ) :
  def __init__( self, name ) :
    self.name_ = name
    self.filename_ = None
    self.datasets_ = {}
    
  def loadFile( self, filename ) :
    print( "Loading " + filename + "..." )
    raw = json.load( open( filename ) )
    self.name_ = raw["name"]

    for data in raw["datasets" ] :
      dataset = DataSet( data["name"] )
      dataset.time_  = np.array( data["time"] )
      dataset.value_ = np.array( data["value"] )
      self.datasets_[dataset.name_] = dataset
     
  
    self.filename_ = filename
    
class DataModel( object ) :
  def __init__( self ) :
    # Config data
    self.configs_ = []
    
    # Time graph resolution in seconds
    self.timeResolution_ = 30

    # Current config selected
    self.currentConfigIdx_ = None

    # where to load from
    self.dataFolder_ = "configs/"

  def loadFolder( self, folder=None ) :
    if folder is not None :
      self.dataFolder_ = folder

    files = glob.glob( self.dataFolder_ + "/*.cfg" )
    
    for cfg in files :
      cfgData = Configuration( "temp" )
      cfgData.loadFile( cfg )
      self.configs_.append( cfgData )

    if self.currentConfigIdx_ is None and len( self.configs_ ) > 0 :
      self.currentConfigIdx_ = 0
  
if __name__ == '__main__':
  
  try:
    hwctrl   = HardwareController( )
    print( "HW Controller Set Up" )

    dataModel = DataModel( )
    dataModel.loadFolder( "config" )
    print( "Data Model Set Up" )
    
    renderer = Renderer( hwctrl, dataModel )
    print( "Renderer Set Up" )

    # Disable luma's stupid fucking cleanup since we can't configure it
    c = Capture()
    atexit.unregister(c)
    print( c.captured )
    atexit.unregister( c.captured[0] )

    renderer.render()
    while not renderer.quit() :
      time.sleep( 1 )
  except :
    print( "Failed to start program." )
    raise
  

