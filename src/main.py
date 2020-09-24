#!/usr/bin/env python3

import gpiozero as gz
from luma.lcd.device import st7735 as luma_st7735
from luma.core.interface.serial import spi as luma_spi
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite
from PIL import ImageFont, ImageColor, Image
import multitimer
import widgets

USE_BLYNK=True

if USE_BLYNK :
  import blynklib

import sys
import io
import time
import signal
import builtins
import numpy as np
import atexit
import json
import glob
import threading
from datetime import datetime
from enum import Enum

# Shield
#KEY_UP_PIN     = 6
#KEY_DOWN_PIN   = 19
#KEY_LEFT_PIN   = 5
#KEY_RIGHT_PIN  = 26
#KEY_PRESS_PIN  = 13
#KEY1_PIN       = 21
#KEY2_PIN       = 20
#KEY3_PIN       = 16

KEY_UP_PIN     = 26
KEY_DOWN_PIN   =  5
KEY_LEFT_PIN   = 19
KEY_RIGHT_PIN  =  6
KEY_PRESS_PIN  = 13

ZAXIS_RST  = 0 

ZAXIS_DIR  = 0
ZAXIS_STEP = 0
ZAXIS_M1   = 0
ZAXIS_M2   = 0
ZAXIS_M3   = 0
ZAXIS_SLP  = 0

FAN_CTRL   = 15
UV_CTRL    = 14


class Capture:
  def __init__(self):
    self.captured = []
  def __eq__(self, other):
    self.captured.append(other)
    return False

# What State the hardware control is in
class ControlModes( Enum ) :
  AUTO_RUN = 0
  MANUAL   = 1
  MANUAL_TIME = 2
  
class HardwareController( object ) :
  def __init__( self ) :
    self.controlMode_ = ControlModes.AUTO_RUN
    
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

    self.outputs_ = {}
    #self.outputs_[ "zaxis" ] = {}
    #self.outputs_[ "zaxis" ][ "ctrl" ] = gz.PhaseEnableMotor(
    self.outputs_[ "fan" ] = gz.PWMOutputDevice( FAN_CTRL )

  

class Renderer( object ) :
  def __init__( self, ctrl, model ) :
    self.hwctrl_ = ctrl
    self.model_  = model
    self.updateHz_ = 30
    self.runningTimer_ = False
    self.manualTimeAdjust_ = 2.5 # To dial in actual time stepping, this isn't fancy ok it barely works
    # We are going to make it think it's running 2x faster, as it is slow af
    self.timer_ = multitimer.MultiTimer( interval=1.0/self.updateHz_, function=self.runTimer, kwargs={ 'interval' : self.manualTimeAdjust_/self.updateHz_ }, runonstart=True )
    self.frameReg_ = luma_sprite.framerate_regulator( fps=self.updateHz_ )
    self.font_   = ImageFont.truetype( "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size=8 )
    self.smallfont_   = ImageFont.truetype( "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", size=7 )

    self.lock_ = threading.Lock()

    self.baseCanvas_ = None
    self.setupImg_   = Image.open( "resources/setup.png" )
    self.buildImg_   = Image.open( "resources/build_plate_trans.png" )
    self.buildPlateYPos_ = 55

    for key, value in self.hwctrl_.buttons_.items() :
      value.when_pressed = self.buttonPress

    self.valueSubdivisions_ = 10
    self.maxCursorPosition_ = 35
    self.dataCursorColor_   = "orange"
    self.dataCursorPix_     = -1
    
    # Widgets
    self.mainWidgets_ = widgets.WidgetManager( )
    self.mainWidgets_.name_ = "main"

    #self.mainWidgets_.addWidget( "Settings",         widgets.TextBox( "Settings", "darkgreen", 1, 5,  0,  0, 43, 16, self.font_, 1 ) )
    #self.mainWidgets_.addWidget( "Hardware",         widgets.TextBox( "Hardware", "darkgreen", 1, 5, 44,  0, 43, 16, self.font_, 1 ) )
    #self.mainWidgets_.addWidget( "Help",             widgets.TextBox( "Help",     "darkgreen", 10, 5, 88,  0, 40, 16, self.font_, 1 ) )
    self.mainWidgets_.addWidget( "ConfigsBar",       widgets.TextBox( "No\nConfigs\nLoaded", "darkgreen", 2, 5, 0, 0, 43, 128, self.font_, 2 ) )
    self.mainWidgets_.addWidget( "Resolution",       widgets.TextBox( "Interval " + str( self.model_.timeResolution_ ) + " sec", "darkgreen", 2, 2, 44, 0, 84, 17, self.font_, 1, spacing=2 ), canSelect=False )
    self.mainWidgets_.addWidget( "TimeAdjustUp",     widgets.TextBox( "^UP",   "lightblue", 2, 1, 129,  0, 30, 8, self.font_, 1, spacing=2 ), takeImmediateInput=True )
    self.mainWidgets_.addWidget( "TimeAdjustDown",   widgets.TextBox( "vDOWN", "tomato",    2, 1, 129,   9, 30, 8, self.font_, 1, spacing=2 ), takeImmediateInput=True )
    #self.mainWidgets_.addWidget( "InfoLabel",        widgets.TextBox( "For detailed info ->", "blue", 2, -1, 44, 38, 84, 6, self.smallfont_, 0 ), canSelect=False )

    # Still part of main widgets just a subcategory
    self.dataWidgets_ = widgets.WidgetManager()
    self.dataWidgets_.addWidget( "Data_zaxis",       widgets.TextBox( "NO DATA", "blue", 0, 1,  44, 18, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
    self.dataWidgets_.addWidget( "Data_fan",         widgets.TextBox( "NO DATA", "blue", 3, 1, 102, 18, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
    self.dataWidgets_.addWidget( "Data_lights",      widgets.TextBox( "NO DATA", "blue", 0, 1,  44, 31, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
    self.dataWidgets_.addWidget( "Data_time",        widgets.TextBox( "NO DATA", "blue", 3, 1, 102, 31, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
    self.dataWidgets_.addWidget( "UV",               widgets.TextBox( "", "blue", 2, -1, 132, 113, 22, 9, self.smallfont_, 0 ), canSelect=False )
    self.dataWidgets_.addWidget( "Fan",              widgets.TextBox( "", "blue", 2, -1, 131, 105, 24, 3, self.smallfont_, 0 ), canSelect=False )

    self.mainWidgets_.addWidget( "PreviewGraph", widgets.Graph( x=44, y=44, width=84, height=84 ) )
    self.mainWidgets_.widgets_[ "PreviewGraph" ].gridPxIncx_ = 8
    self.mainWidgets_.widgets_[ "PreviewGraph" ].gridPxIncy_ = 8
    
    self.configWidgets_ = widgets.WidgetManager()
    self.configWidgets_.name_ = "configs"
    self.configWidgets_.adjustCentroid_ = False

    # Callbacks
    self.mainWidgets_.widgets_[ "ConfigsBar" ].addInput( self.configWidgets_.onInput )
    self.mainWidgets_.widgets_[ "ConfigsBar" ].addInput( self.handleConfigs )
    self.mainWidgets_.widgets_[ "ConfigsBar" ].defocusCondition_ = self.checkLeaveConfigs

    self.mainWidgets_.widgets_[ "PreviewGraph" ].addInput( self.handleGraph )
    self.mainWidgets_.widgets_[ "PreviewGraph" ].defocusCondition_ = self.checkLeaveGraph

    self.mainWidgets_.widgets_[ "TimeAdjustUp"   ].addInput( self.handleResAdjustUp   )
    self.mainWidgets_.widgets_[ "TimeAdjustDown" ].addInput( self.handleResAdjustDown )

    self.maxConfigsOnScreen_ = 4
    self.configHeight_       = 17
    for cfg in self.model_.configs_ :
      self.addConfig( cfg )
    self.checkLeaveConfigs( "noop" )
    
    for name, widget in self.mainWidgets_.widgets_.items() :
      widget.name_ = name
      widget.fg_ = "green"
      widget.bg_ = ImageColor.getrgb( "#1f0f0f" )
      widget.selectFg_       = "white"
      widget.selectBg_       = "black"
      
      widget.focusFg_       = "orange"
      widget.focusBg_       = "black"
      widget.deselect()

    for name, widget in self.configWidgets_.widgets_.items() :
      widget.name_ = name
      widget.fg_ = "green"
      widget.bg_ = ImageColor.getrgb( "#1f0f0f" )
      widget.selectFg_       = "white"
      widget.selectBg_       = "black"
      
      widget.focusFg_       = "orange"
      widget.focusBg_       = "black"
      widget.deselect()
      
    self.quit_ = False

    self.currentContext_ = "main"
    
    self.contexts_ = {}
    self.contexts_[ "main" ]       = [ self.main, self.mainWidgets_ ]

  def runTimer( self, interval=1.0 ) :
    if not self.runningTimer_ : return
        
    if self.model_.currentTime_ > self.model_.getCurrentTotalTime() :
      # Stop yourself before you wreck yourself
      print( "Profile finished... Stopping [ total profile time : " + str( self.model_.getCurrentTotalTime() ) + "]" )
      self.handleStopTimer()

    #print( "Current time is : " + str( self.model_.currentTime_ ) + " seconds" )
    # Write data to hw controller
    currentData   = self.model_.getCurrentData( )
                   
    for name, value in currentData.items() :      
      if name == "fan" :
        self.hwctrl_.outputs_[ name ].value = value
      elif name == "lights" :
        pass
      elif name == "zaxis" :
        pass
    
    self.render()
    self.model_.currentTime_ += interval
    

  def main( self, canvas ) :

    # Time at which to handle
    self.handleDataCursor( self.model_.currentTime_ )
    
    for name, widgets in self.mainWidgets_.widgets_.items() :
      widgets.draw( canvas )
    for name, cfg in self.configWidgets_.widgets_.items() :
      cfg.draw( canvas )
    for name, data in self.dataWidgets_.widgets_.items() :
      data.draw( canvas )
      
    if self.model_.getCurrentConfig() is not None:
      # print( "Previewing config : " + self.model_.getCurrentConfig().name_ )
           
      for name, dataset in self.model_.getCurrentConfig().datasets_.items() :
        data = np.array( ( dataset.time_,
                           dataset.value_ ) )
        incy = ( dataset.max_ - dataset.min_ ) / self.valueSubdivisions_
        
        self.mainWidgets_.widgets_[ "PreviewGraph" ].drawData(
                                                              data,
                                                              self.model_.timeResolution_ / self.valueSubdivisions_,
                                                              incy,
                                                              dataset.lineColor_,
                                                              dataset.pointColor_
                                                              )
        if self.dataCursorPix_ >= 0 :
          x  = self.dataCursorPix_ + self.mainWidgets_.widgets_[ "PreviewGraph" ].x_ + self.mainWidgets_.widgets_[ "PreviewGraph" ].borderpx_ + 1
          y1 = self.mainWidgets_.widgets_[ "PreviewGraph" ].y_ + self.mainWidgets_.widgets_[ "PreviewGraph" ].borderpx_
          y2 = y1 + self.mainWidgets_.widgets_[ "PreviewGraph" ].height_ - self.mainWidgets_.widgets_[ "PreviewGraph" ].borderpx_
          canvas.line( [ x, y1, x, y2 ], self.dataCursorColor_ )

    # Draw fancy
    # Now paste the setup 
    self.baseCanvas_.image.paste( self.setupImg_, ( 128, 44 ), mask=self.setupImg_ )
    self.baseCanvas_.image.paste( self.buildImg_, ( 128, self.buildPlateYPos_ ), mask=self.buildImg_ )

  def settings( self, canvas ) :
    pass
  def configs( self, canvas ) :
    pass
  def edit( self, canvas ) :
    pass
  def run( self, canvas ) :
    pass


  def handleDataCursor( self, time ) :
    if self.baseCanvas_ is not None :
      
      if time < 0 :  
        self.buildPlateYPos_ = 55
        for name, widget in self.dataWidgets_.widgets_.items() :
          widget.hide()
        self.dataCursorPix_ = -1

      else :
        for name, widget in self.dataWidgets_.widgets_.items() :
          widget.unhide()
          if "Data" in name :
            widget.text_ = ""
        
        # Convert time to grid draw position
        # seconds per pixel
        secPerPixX = ( self.model_.timeResolution_ / self.valueSubdivisions_ ) / self.mainWidgets_.widgets_[ "PreviewGraph" ].gridPxIncx_

        # How many pixels into the data we are
        pixels = time / secPerPixX

        self.dataCursorPix_ = np.minimum( self.maxCursorPosition_, int( pixels ) )
        self.mainWidgets_.widgets_[ "PreviewGraph" ].drawPosX_ = np.maximum( 0, int( pixels ) - self.dataCursorPix_ )
                
        # Gather data at time
        currentData   = self.model_.getCurrentData( )
        currentConfig = self.model_.getCurrentConfig( )
        
        self.dataWidgets_.widgets_[ "Data_time" ].text_ = "Time " + "{:3.2f}".format( self.model_.currentTime_ ) + " sec"
        
        for name, value in currentData.items() :
          # This is very dependent on the data widgets being there, I don't like it but I'm so tired at this point
          self.dataWidgets_.widgets_[ "Data_" + name ].text_ += "{0: <4}".format( name ) + " " + "{:3.2f}".format( value )
          self.dataWidgets_.widgets_[ "Data_" + name ].textColor_    = currentConfig.datasets_[ name ].lineColor_

          if name == "fan" :
            self.dataWidgets_.widgets_[ "Fan" ].currentBg_ = ImageColor.getrgb( "rgb( {0}, {1}, {2} )".format( 25, 25, int( 255 * currentConfig.datasets_[ name ].normalize( value ) ) ) )
            self.dataWidgets_.widgets_[ "Fan" ].bg_ = self.dataWidgets_.widgets_[ "Fan" ].currentBg_
          elif name == "lights" :
            val = currentConfig.datasets_[ name ].normalize( value )
            self.dataWidgets_.widgets_[ "UV" ].currentBg_ = ImageColor.getrgb( "rgb( {0}, {1}, {2} )".format( int( 255 * val ), 25, int( 255 * val ) )  )
            self.dataWidgets_.widgets_[ "UV" ].bg_ = self.dataWidgets_.widgets_[ "UV" ].currentBg_
          elif name == "zaxis" :
            yHeight = 46
            yStart  = 50
            self.buildPlateYPos_ = int( yStart + yHeight * currentConfig.datasets_[ name ].normalize( value ) )
                      
        
        
  def handleGraph( self, direction ) :
    # Up and down are flipped because of the Y inverted pixels
    #if direction == "up" :
    #  self.mainWidgets_.widgets_[ "PreviewGraph" ].moveDown()
    #elif direction == "down" :
    #  self.mainWidgets_.widgets_[ "PreviewGraph" ].moveUp()
    if direction == "left" :
      self.model_.currentTime_ -= self.model_.timeResolution_ / self.valueSubdivisions_ / 8
      # self.mainWidgets_.widgets_[ "PreviewGraph" ].moveLeft()
    elif direction == "right" :
      self.model_.currentTime_ += self.model_.timeResolution_ / self.valueSubdivisions_ / 8
      # self.mainWidgets_.widgets_[ "PreviewGraph" ].moveRight()

  def checkLeaveGraph( self, direction ) :
    leaveGraph = ( direction == "press" ) or ( direction == "up" )
    if leaveGraph :
      self.mainWidgets_.widgets_[ "PreviewGraph" ].drawPosX_ = 0
      self.mainWidgets_.widgets_[ "PreviewGraph" ].drawPosY_ = 0
      self.model_.currentTime_ = -1
      self.dataCursorPix_      = -1
    return leaveGraph
    
  def handleConfigs( self, direction ) :
    currentIdx = self.configWidgets_.getCurrentWidgetIndex( )

    # We are actively running a profile and are changing, abort
    if self.runningTimer_ or self.model_.currentTime_ != 0 :
      if self.model_.currentConfigIdx_ != currentIdx :
        self.handleStartPauseTimer( )
        # This does extra and resets values
        self.handleStopTimer( )
        
    self.model_.currentConfigIdx_ = currentIdx
    
    # Loop and move everything up, hiding others        
    for i in range( 0, len( self.configWidgets_.widgetsList_ ) ) :
      if currentIdx > self.maxConfigsOnScreen_ and currentIdx != len( self.configWidgets_.widgetsList_ ) - 1 :
        if direction == "up" :
          self.configWidgets_.widgetsList_[i].setY( self.configWidgets_.widgetsList_[i].y_ + self.configHeight_ )
        elif direction == "down" :
          self.configWidgets_.widgetsList_[i].setY( self.configWidgets_.widgetsList_[i].y_ - self.configHeight_ )
      if ( ( self.configWidgets_.widgetsList_[i].centerY_ < self.mainWidgets_.widgets_[ "ConfigsBar" ].y_ ) or
           ( self.configWidgets_.widgetsList_[i].centerY_ > ( self.mainWidgets_.widgets_[ "ConfigsBar" ].y_ + self.mainWidgets_.widgets_[ "ConfigsBar" ].height_ ) ) ) :
        self.configWidgets_.widgetsList_[i].hide()
        
      else : # within bounds
        self.configWidgets_.widgetsList_[i].unhide()
        

      
  def checkLeaveConfigs( self, direction ) :
    currentIdx = self.configWidgets_.getCurrentWidgetIndex( )
    return ( ( direction == "right" ) or
             ( ( direction == "up" ) and
               ( currentIdx == 0 )
               )
             )
    
  def addConfig( self, config ) :
    # We have at least one config now
    self.mainWidgets_.widgets_[ "ConfigsBar" ].text_ = ""
    truncName = ( config.name_[:6] + '..') if len(config.name_) > 8 else config.name_
    startPos = ( self.mainWidgets_.widgets_[ "ConfigsBar" ].y_ + 1 
                  if len( self.configWidgets_.widgetsList_ ) == 0 
                  else self.configWidgets_.widgetsList_[-1].y_ + self.configHeight_ + 1 )
    cfgWidget = widgets.TextBox(
                                truncName,
                                "darkgreen",
                                2, 3,
                                self.mainWidgets_.widgets_[ "ConfigsBar" ].x_ + 1,
                                startPos,
                                self.mainWidgets_.widgets_[ "ConfigsBar" ].width_ - 2,
                                self.configHeight_,
                                self.font_, 1
                                )
    
    name = config.name_ + " - " + str( len( self.configWidgets_.widgetsList_ ) )
    cfgWidget.addInput( self.handleStartPauseTimer )
    print( "Adding config widget : " + name ) 
    self.configWidgets_.addWidget( name, cfgWidget, takeImmediateInput=True )

  def handleResAdjustUp( self, direction ) :
    if direction == "press" :
      self.model_.timeResolution_ = np.minimum( self.model_.timeResolution_ + 5, 60 )
      self.mainWidgets_.widgets_[ "Resolution" ].text_ = "Interval " + str( self.model_.timeResolution_ ) + " sec"

  def handleResAdjustDown( self, direction ) :
    if direction == "press" :
      self.model_.timeResolution_ = np.maximum( self.model_.timeResolution_ - 5, 5 )
      self.mainWidgets_.widgets_[ "Resolution" ].text_ = "Interval " + str( self.model_.timeResolution_ ) + " sec"

  def handleStartPauseTimer( self ) :
    if self.runningTimer_ :
      self.timer_.stop()
      self.runningTimer_ = False
      print( "Pausing profile" )
    else :
      self.timer_.start()
      self.runningTimer_ = True
      # Our first time in here
      if self.model_.currentTime_ == -1 :
        self.model_.currentTime_ = 0
        
      print( "Starting profile" )

  def handleStopTimer( self ) :
    self.timer_.stop()
    self.runningTimer_ = False
    self.model_.currentTime_ = -1
    self.mainWidgets_.widgets_[ "PreviewGraph" ].drawPosX_ = 0
    print( "Stopping profile" )

  def buttonPress( self, button ) :

    pressType = self.hwctrl_.buttonMap_[ button.pin.number ]
    
    if self.hwctrl_.controlMode_ == ControlModes.AUTO_RUN and pressType == "select" :
      print( "Hardware is manual mode, user cannot select" )
    else :
      # Get the current context widget manager
      self.contexts_[ self.currentContext_ ][1].onInput( pressType )
      self.render()
    

  def quit( self ) :
    return self.quit_
      
  def render( self ) :
    self.lock_.acquire()
    
    with self.frameReg_ :
      self.baseCanvas_ = luma_render.canvas( self.hwctrl_.device_, dither=True )
      with  self.baseCanvas_ as canvas :
        self.contexts_[ self.currentContext_ ][0]( canvas )
        #if self.contexts_[ self.currentContext_ ][1].currentWidget_ is not None :
          # print( "Active Widget is : " + self.contexts_[ self.currentContext_ ][1].currentWidget_.name_ )

    self.lock_.release()
          
        

class DataSet( object ) :
  def __init__( self, name ) :
    self.name_  = name
    self.time_  = np.zeros( (0) )
    self.value_ = np.zeros( (0) )
    self.lineColor_  = "blue"
    self.pointColor_ = "red"

    # These are NOT the value min/max
    # but the expected absolute max of the system
    self.max_   = 1
    self.min_   = 0

  def normalize( self, value ) :
    return ( value - self.min_ ) / ( self.max_ - self.min_ )
    
        
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
      if "lineColor" in data :
        dataset.lineColor_ = data["lineColor"]
      if "pointColor" in data :
        dataset.pointColor_ = data["pointColor"]
      self.datasets_[dataset.name_] = dataset
     
  
    self.filename_ = filename
    
class DataModel( object ) :
  def __init__( self ) :
    # Config data
    self.configs_ = []
    
    # Time graph resolution in seconds
    self.timeResolution_ = 30

    # Current config selected
    self.currentConfigIdx_ = -1

    # Current time into config in seconds
    self.currentTime_ = -1

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
      
  def getCurrentConfig( self ) :
    if self.currentConfigIdx_ >= 0 :
      return self.configs_[ self.currentConfigIdx_ ]
    else :
      return None

  def getCurrentTotalTime( self ) :
    currentConfig = self.getCurrentConfig()

    if currentConfig is None : return None
      
    # Return longest time
    totalTime = 0
    for name, dataset in currentConfig.datasets_.items() :
      totalTime = np.maximum( np.max( dataset.time_ ), totalTime )

    return totalTime

  def getCurrentData( self ) :
    currentConfig = self.getCurrentConfig()

    if currentConfig is None : return None
      
    # Return interpolated data for current time in order of
    # { dataset : value }
    currentData = {}
    for name, dataset in currentConfig.datasets_.items() :
      currentData[ name ] = np.interp( self.currentTime_, dataset.time_, dataset.value_ )

    return currentData

class BlynkInterface( object ) :
  def __init__( self, auth, server=None ) :

    # PRINT HACKS
    self._print = print
    builtins.print = self.debugPrint
    
    self.renderer_ = None
    # No SSL, so 8080
    self.blynk_    = blynklib.Blynk( auth, server=server or "blynk-cloud.com", port=8080 )
    # WHYYYYYY
    self.blynk_.VPIN_MAX_NUM = 255
    
    self.com_      = True
    self.blynkthread_ = multitimer.MultiTimer( interval=0.1, function=self.communicate, runonstart=True )

    # We will keep track of whether to ignore writes of zero - this is to filter out button taps
    # that write zero out as a signal
    self.pins_ = {}
    self.pins_[ "main_terminal" ] = { "vnum" : 255, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_terminal" ] = { "vnum" : 254, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_terminal" ] = { "vnum" : 253, "value" : 0, "ignoreZero" : False }
    self.pins_[ "poweroff" ] = { "vnum" : 252, "value" : 0, "ignoreZero" : True }
    self.pins_[ "cpu_usage"       ] = { "vnum" : 251, "value" : 0, "ignoreZero" : False }
    self.pins_[ "cpu_temperature" ] = { "vnum" : 250, "value" : 0, "ignoreZero" : False }

    # Manual Mode
    self.pins_[ "zaxis"            ] = { "vnum" : 0, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_zaxis_inc" ] = { "vnum" : 3, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_zaxis_rst" ] = { "vnum" : 6, "value" : 0, "ignoreZero" : True }

    self.pins_[ "fan"            ] = { "vnum" : 1, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_fan_inc" ] = { "vnum" : 4, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_fan_rst" ] = { "vnum" : 7, "value" : 0, "ignoreZero" : True }
    
    self.pins_[ "uvled"            ] = { "vnum" : 2, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_uvled_inc" ] = { "vnum" : 5, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_uvled_rst" ] = { "vnum" : 8, "value" : 0, "ignoreZero" : True }

    self.pins_[ "manual_rst_all"     ] = { "vnum" :  9, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_start_timer" ] = { "vnum" : 10, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_stop_timer" ] = { "vnum" : 51, "value" : 0, "ignoreZero" : True }
    
    self.pins_[ "manual_hardware_preview" ] = { "vnum" : 11, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_mode"      ] = { "vnum" : 12, "value" : 0, "ignoreZero" : False }

    self.pins_[ "manual_time_rem" ] = { "vnum" : 13, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_time_sec" ] = { "vnum" : 14, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_time_min" ] = { "vnum" : 15, "value" : 0, "ignoreZero" : False }

    self.pins_[ "active_profile" ] = { "vnum" : 17, "value" : 0, "ignoreZero" : False }
    self.pins_[ "auto_mode"      ] = { "vnum" : 16, "value" : 0, "ignoreZero" : False }
    self.pins_[ "auto_runner"    ] = { "vnum" : 18, "value" : 0, "ignoreZero" : False }
    self.pins_[ "active_data"    ] = { "vnum" : 19, "value" : 0, "ignoreZero" : False }
    
    self.pins_[ "edit_profile"          ] = { "vnum" : 20, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_resolution"       ] = { "vnum" : 21, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_hardware_preview" ] = { "vnum" : 22, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_profile_preview"  ] = { "vnum" : 23, "value" : 0, "ignoreZero" : False }

    self.pins_[ "edit_zaxis_text"  ] = { "vnum" : 24, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_fan_text"    ] = { "vnum" : 25, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_uvled_text"  ] = { "vnum" : 26, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_time_text"   ] = { "vnum" : 27, "value" : 0, "ignoreZero" : False }
    

    self.pins_[ "edit_data"    ] = { "vnum" : 28, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_value"   ] = { "vnum" : 29, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_time "   ] = { "vnum" : 30, "value" : 0, "ignoreZero" : False }

    self.pins_[ "edit_run_preview"  ] = { "vnum" : 31, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_point"    ] = { "vnum" : 32, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_add"      ] = { "vnum" : 33, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_delete_point" ] = { "vnum" : 34, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_save"     ] = { "vnum" : 35, "value" : 0, "ignoreZero" : True }

    self.pins_[ "edit_zaxis_disabled"   ] = { "vnum" : 36, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_fan_disabled"     ] = { "vnum" : 37, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_uvled_disabled"   ] = { "vnum" : 38, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_profile_name" ] = { "vnum" : 39, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_filename"     ] = { "vnum" : 40, "value" : 0, "ignoreZero" : False }

    self.pins_[ "edit_duplicate"      ] = { "vnum" : 41, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_new_profile"    ] = { "vnum" : 42, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_delete_profile" ] = { "vnum" : 43, "value" : 0, "ignoreZero" : True }

    self.pins_[ "settings_global_zaxis_disabled" ] = { "vnum" : 44, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_global_fan_disabled"   ] = { "vnum" : 45, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_global_uvled_disabled" ] = { "vnum" : 46, "value" : 0, "ignoreZero" : False }

    self.pins_[ "settings_manual_half_notify_disabled" ] = { "vnum" : 47, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_manual_full_notify_disabled" ] = { "vnum" : 48, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_auto_half_notify_disabled" ] = { "vnum" : 49, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_auto_full_notify_disabled" ] = { "vnum" : 50, "value" : 0, "ignoreZero" : False }
    
    self.virtualPinMap_ = {}
    for key, value in self.pins_.items() :
      self.virtualPinMap_[ value[ "vnum" ] ] = { "name" : key }
      self.pins_[ key ][ "handler" ] = self.main_handler

      if "edit" in key :
        self.pins_[ key ][ "handler" ] = self.edit_handler
      elif "settings" in key :
        self.pins_[ key ][ "handler" ] = self.settings_handler
        
    
    print( "Manual decoration for Blynk Server..." )
    blynklib.Blynk.handle_event( self.blynk_, "connect")( self.connect_handler )
    blynklib.Blynk.handle_event( self.blynk_, 'internal_rtc' )( self.rtc_handler )

    blynklib.Blynk.handle_event( self.blynk_, 'write V*' )( self.pinwrite_handler )
    # blynklib.Blynk.handle_event( self.blynk_, 'write *' )( self.pinwrite_handler )

  def debugPrint( self, *args, **kw ) :
    oldstdout = sys.stdout
    newstdout = io.StringIO()
    sys.stdout = newstdout
    
    self._print( *args, **kw )
    output = newstdout.getvalue()[:-1]
    
    if hasattr( self, "blynk_" ) and self.blynk_ is not None and self.blynk_._socket is not None :
      if hasattr( self, "pins_" ) and "settings_terminal" in  self.pins_ :
        self.blynk_.virtual_write( self.pins_[ "settings_terminal" ][ "vnum" ], output )

    sys.stdout = oldstdout
    self._print( output )

  def main_handler( self, pin ) :
    print( "In main handler via pin " + str( pin ) + " called " + self.virtualPinMap_[ pin ][ "name" ] )

    if self.virtualPinMap_[pin]["name"] == 

  def edit_handler( self, pin ) :
    print( "In edit handler via pin " + str( pin ) + " called " + self.virtualPinMap_[ pin ][ "name" ] )

  def settings_handler( self, pin ) :
    print( "In settings handler via pin " + str( pin ) + " called " + self.virtualPinMap_[ pin ][ "name" ] )


      
  def communicate( self ) :
    while self.com_ :
      self.blynk_.run()

      if self.renderer_ is not None :
        if self.renderer_.runningTimer_ :
          currentData   = self.renderer_.model_.getCurrentData( )
        
          for name, value in currentData.items() :      
            if name == "zaxis" :
              self.blynk_.virtual_write( 0, value )
            elif name == "fan" :
              self.blynk_.virtual_write( 1, value )
            elif name == "lights" :
              self.blynk_.virtual_write( 2, value )
      
  def run( self ) :
    self.blynkthread_.start()
    print( "Waiting for server to start..." )       

  def stop( self ) :
    self.blynk_.notify( "BAWCS Offline" )
    self.blynkthread_.stop()

  def connect_handler( self ):
    self.blynk_.internal("rtc", "sync")
    self.blynk_.notify( "BAWCS Online" )
    msg  = "\n\n\nHello World!\n"
    msg += "Welcome to BAWCS\n"
    msg += "Your one-stop-shop\n"
    msg += "for :\n"
    msg += "Better\n"
    msg += "Automated\n"
    msg += "Washing and\n"
    msg += "Curing\n"
    msg += "Station\n\n"
    msg += "- Anthony Islas"
    self.blynk_.virtual_write( self.pins_[ "main_terminal" ][ "vnum" ], msg + "\n" )
    
    print( "RTC sync request was sent" )

  # From https://github.com/blynkkk/lib-python/blob/master/examples/10_rtc_sync.py
  def rtc_handler( self, rtc_data_list ) :
    
    hr_rtc_value = datetime.utcfromtimestamp( int( rtc_data_list[0] ) ).strftime( '%Y-%m-%d %H:%M:%S' )
    print('Raw RTC value from server: {}'.format( rtc_data_list[0] ) )
    print('Human readable RTC value: {}'.format( hr_rtc_value ) )
  

  def pinwrite_handler( self, pin, value ) :
    if pin in self.virtualPinMap_ :
      if ( value != 0 and 0 not in value and '0' not in value ) or not self.pins_[ self.virtualPinMap_[pin]["name"] ][ "ignoreZero" ] :
        print( "You modified " + str( pin ) + " to value " + str( value ) + " which is " + self.virtualPinMap_[pin]["name"] )
        self.pins_[ self.virtualPinMap_[pin]["name"]]["value"] = value
        self.pins_[ self.virtualPinMap_[pin]["name"]]["handler"]( pin )
      else :
        print( "Fallthrough... we ignored " + str( pin ) + " which is " + self.virtualPinMap_[pin]["name"] )
  
if __name__ == '__main__':
  
  try:
    blynkint = None
    if USE_BLYNK :
      blynkint = BlynkInterface( open( "cred/.secrets" ).read(), "192.168.0.10" )
      blynkint.run()
      
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

    # Link the two
    if blynkint is not None :
      blynkint.renderer_ = renderer
    
    renderer.render()
    while not renderer.quit() :
      time.sleep( 1 )
  except :
    print( "Failed to start program." )
    raise
  

