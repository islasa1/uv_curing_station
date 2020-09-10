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

# Shield
#KEY_UP_PIN     = 6
#KEY_DOWN_PIN   = 19
#KEY_LEFT_PIN   = 5
#KEY_RIGHT_PIN  = 26
#KEY_PRESS_PIN  = 13
#KEY1_PIN       = 21
#KEY2_PIN       = 20
#KEY3_PIN       = 16

KEY_UP_PIN     = 5
KEY_DOWN_PIN   = 26
KEY_LEFT_PIN   = 6
KEY_RIGHT_PIN  = 19
KEY_PRESS_PIN  = 13

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
                            gpio_DC=23, # 25 
                            gpio_RST=24 # 27
                           )
      
    self.device_ = luma_st7735(
                               #gpio_LIGHT=24,  #this is failing, idk why
                               #pwm_frequency=200,
                               serial_interface=self.spi_,
                               width=160,
                               height=128,
                               bgr=False,
                               h_offset=0,
                               v_offset=0,
                               rotate=2
                              )
    #self.device_ = luma_device.get_device( config )
    self.buttons_ = {}
    self.buttons_[ "up"    ] = gz.Button( KEY_UP_PIN,    bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "down"  ] = gz.Button( KEY_DOWN_PIN,  bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "left"  ] = gz.Button( KEY_LEFT_PIN,  bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "right" ] = gz.Button( KEY_RIGHT_PIN, bounce_time=0.05, hold_time=1, hold_repeat=True )
    self.buttons_[ "press" ] = gz.Button( KEY_PRESS_PIN, bounce_time=0.05, hold_time=1, hold_repeat=True )

    self.buttonMap_ = {}
    for key, value in self.buttons_.items() :
      self.buttonMap_[ value.pin.number ] = key

    self.frameReg_ = luma_sprite.framerate_regulator( fps=30 )

class Renderer( object ) :
  def __init__( self, ctrl, model ) :
    self.hwctrl_ = ctrl
    self.model_  = model
    self.font_   = ImageFont.truetype( "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size=8 )
    self.smallfont_   = ImageFont.truetype( "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size=7 )

    for key, value in self.hwctrl_.buttons_.items() :
      value.when_pressed = self.buttonPress

    self.valueSubdivisions_ = 10
    
    # Widgets
    self.mainWidgets_ = WidgetManager( )
    self.mainWidgets_.addWidget( "PreviewGraph", widgets.Graph( x=44, y=44, width=84, height=84 ) )
    self.mainWidgets_.widgets_[ "PreviewGraph" ].gridPxIncx_ = 8
    self.mainWidgets_.widgets_[ "PreviewGraph" ].gridPxIncy_ = 8

    self.mainWidgets_.addWidget( "Settings",         widgets.TextBox( "Settings", "darkgreen", 1, 5,  0,  0, 43, 16, self.font_, 1 ) )
    self.mainWidgets_.addWidget( "Hardware",         widgets.TextBox( "Hardware", "darkgreen", 1, 5, 44,  0, 43, 16, self.font_, 1 ) )
    self.mainWidgets_.addWidget( "Help",             widgets.TextBox( "Help",     "darkgreen", 4, 5, 89,  0, 28, 16, self.font_, 1 ) )
    self.mainWidgets_.addWidget( "ConfigsBar",       widgets.TextBox( "No\nConfigs\nLoaded", "darkgreen", 2, 5, 0, 17, 43, 110, self.font_, 1 ) )
    self.mainWidgets_.addWidget( "Resolution",       widgets.TextBox( "Timescale\n" + str( self.model_.timeResolution_ ) + " sec", "darkgreen", 2, 2, 44, 17, 48, 20, self.font_, 1, spacing=2 ) )
    self.mainWidgets_.addWidget( "ResolutionAdjust", widgets.TextBox( "Adjust\nTime", "darkgreen", 2, 2, 93, 17, 35, 20, self.font_, 1, spacing=2 ) )
    self.mainWidgets_.addWidget( "ResolutionTime",   widgets.TextBox( "For detailed info ->", "blue", 2, -1, 44, 38, 84, 6, self.smallfont_, 0 ) )
    
    self.configWidgets_ = WidgetManager()
    self.configWidgets_.adjustCentroid_ = False
    self.configWidgets_.centerX_ = mainWidgets_.widgets_[ "ConfigsBar" ].centerX_
    self.configWidgets_.centerY_ = mainWidgets_.widgets_[ "ConfigsBar" ].centerY_

    for cfg in self.model_.configs_ :
      self.addConfig( cfg )
    
    for name, widget in self.mainWidgets_.widgets_.items() :
      widget.name_ = name
      widget.fg_ = "green"
      widget.bg_ = ImageColor.getrgb( "#1f0f0f" )
      widget.activeFg_       = "white"
      widget.activeBg_       = "black"
      
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
    for cfg in self.configWidgets_ :
      cfg["widget"].draw( canvas )
      
    if self.model_.currentConfigIdx_ :
      for name, dataset in self.model_.configs_[self.model_.currentConfigIdx_].datasets_.items() :
        data = np.array( ( dataset.time_,
                           dataset.value_ ) )
        incy = ( dataset.max_ - dataset.min_ ) / self.valueSubdivisions_
        
        self.mainWidgets_[ "PreviewGraph" ].drawData( data, self.model_.timeResolution_, incy, "blue", "red" )
        
  def settings( self, canvas ) :
    pass
  def configs( self, canvas ) :
    pass
  def edit( self, canvas ) :
    pass
  def run( self, canvas ) :
    pass
    
  def addConfig( self, config ) :
    # We have at least one config now
    self.mainWidgets_.widgets_[ "ConfigsBar" ].text_ = ""
    truncName = ( config.name_[:6] + '..') if len(config.name_) > 8 else config.name_
    widgetHeight = 16
    startPos = ( self.mainWidgets_.widgets_[ "ConfigsBar" ].y_ + 1 
                  if len( self.configWidgets_.widgetsList_ ) == 0 
                  else self.configWidgets_.widgetsList_[-1].y_ + widgetHeight + 1 )
    cfgWidget = widgets.TextBox(
                                truncName,
                                "darkgreen",
                                2, 3,
                                self.mainWidgets_[ "ConfigsBar" ].x_ + 1,
                                startPos,
                                self.mainWidgets_[ "ConfigsBar" ].width_ - 2,
                                widgetHeight,
                                self.font_, 1
                                )

    cfgWidget.name_ = config.name_
    cfgWidget.fg_ = "green"
    cfgWidget.bg_ = ImageColor.getrgb( "#1f0f0f" )
    cfgWidget.activeFg_       = "white"
    cfgWidget.activeBg_       = "black"

    self.configWidgets_.addWidget( cfgWidget )
    
  def buttonPress( self, button ) :
    pressType = self.hwctrl_.buttonMap_[ button.pin.number ] 
    print( "You pressed " + pressType )

    # Get the current context widget manager
    self.contexts_[ self.currentContext_ ][1].onInput( pressType )
    
    # if self.contexts_[ self.currentContext_ ][1] is None :
    #   # Assign default
    #   self.contexts_[ self.currentContext_ ][1] = self.contexts_[ self.currentContext_ ][2]
    #   self.contexts_[ self.currentContext_ ][1].select()

    # #  We have an active widget
    # else: #self.contexts_[ self.currentContext_ ][1] is not None :
    #   if not self.contexts_[ self.currentContext_ ][1].hasFocus() :
    #     newCurrentWidget = self.contexts_[ self.currentContext_ ][1].getLink( pressType )
    #     if newCurrentWidget is not None :
    #       self.contexts_[ self.currentContext_ ][1] = newCurrentWidget
    #   else :
    #     # Widget has focus from main control method, go to its handler
    #     self.contexts_[ self.currentContext_ ][1].onInput( pressType )

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

    # These are NOT the value min/max
    # but the expected absolute max of the system
    self.max_   = 1
    self.min_   = 0
    
        
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
      dataset.min_   = data["min"]
      dataset.max_   = data["max"]
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
  

