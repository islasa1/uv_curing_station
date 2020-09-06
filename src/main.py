#!/usr/bin/env python3

import gpiozero as gz
from luma.lcd.device import st7735 as luma_st7735
from luma.core.interface.serial import spi as luma_spi
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite

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
                               bgr=True
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
    self.hwctrl_.buttons_[ "up"    ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "down"  ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "left"  ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "right" ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "key3"  ].when_pressed = self.buttonPress

    self.graph_    = widgets.Graph( x=38, y=44, width=84, height=84 )
    self.graph_.gridPxIncx_ = 8
    self.graph_.gridPxIncy_ = 8

    self.quit_ = False

    self.currentContext_ = "run"
    
    self.contexts_ = {}
    self.contexts_[ "main" ]       = self.main
    self.contexts_[ "settings" ]   = self.settings
    self.contexts_[ "configs" ]    = self.configs
    self.contexts_[ "edit"    ]    = self.edit
    self.contexts_[ "run"     ]    = self.run

  def main( self, canvas ) :
    pass
  def settings( self, canvas ) :
    pass
  def configs( self, canvas ) :
    pass
  def edit( self, canvas ) :
    pass
  def run( self, canvas ) :
    self.graph_.draw( canvas )
    if len( self.model_.configs_ ) > 0 :
      if self.model_.configs_[0].datasets_["zaxis"] :
        data = np.array( ( self.model_.configs_[0].datasets_["zaxis"].time_,
                           self.model_.configs_[0].datasets_["zaxis"].value_ ) )
        self.graph_.drawData( data, 10, 10, "blue", "red" )  
    
  
  def buttonPress( self, button ) :
    pressType = self.hwctrl_.buttonMap_[ button.pin.number ] 
    print( "You pressed " + pressType )

    if pressType == "up" :
      self.graph_.moveUp()
    elif pressType == "down" :
      self.graph_.moveDown()
    elif pressType == "left" :
      self.graph_.moveLeft()    
    elif pressType == "right" :
      self.graph_.moveRight()
    elif pressType == "key3" :
      self.quit_ = True

    self.render()

  def quit( self ) :
    return self.quit_
      
  def render( self ) :
    data = np.array( ( range( 0, 101, 20 ), range( 0, 101, 20 ) ) )

    with self.hwctrl_.frameReg_ :
      with luma_render.canvas( self.hwctrl_.device_, dither=True ) as canvas :
        self.contexts_[ self.currentContext_ ]( canvas )
        

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
  

