#!/usr/bin/env python3

import gpiozero as gz
from luma.lcd.device import st7735 as luma_st7735
from luma.core.interface.serial import spi as luma_spi
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite
from PIL import ImageFont, ImageColor, Image
import multitimer

USE_BLYNK=True

if USE_BLYNK :
  import blynklib

import sys
import time
import signal
import widgets
import numpy as np
import atexit
import json
import glob
import threading

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

  

class Renderer( object ) :
  def __init__( self, ctrl, model ) :
    self.hwctrl_ = ctrl
    self.model_  = model
    self.updateHz_ = 30
    self.manualTimeAdjust_ = 2.5 # To dial in actual time stepping, this isn't fancy ok it barely works
    # We are going to make it think it's running 2x faster, as it is slow af
    self.profileRunner_ = multitimer.MultiTimer( interval=1.0/self.updateHz_, function=self.runProfile, kwargs={ 'interval' : self.manualTimeAdjust_/self.updateHz_ }, runonstart=True )
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
    self.mainWidgets_.addWidget( "Resolution",       widgets.TextBox( "Interval " + str( self.model_.timeResolution_ ) + " sec", "darkgreen", 2, 2, 44, 0, 84, 16, self.font_, 1, spacing=2 ), canSelect=False )
    self.mainWidgets_.addWidget( "TimeAdjustUp",     widgets.TextBox( "^UP",   "lightblue", 2, 1, 128,  0, 31, 8, self.font_, 1, spacing=2 ) )
    self.mainWidgets_.addWidget( "TimeAdjustDown",   widgets.TextBox( "vDOWN", "tomato",    2, 1, 128,   8, 31, 8, self.font_, 1, spacing=2 ) )
    #self.mainWidgets_.addWidget( "InfoLabel",        widgets.TextBox( "For detailed info ->", "blue", 2, -1, 44, 38, 84, 6, self.smallfont_, 0 ), canSelect=False )

    # Still part of main widgets just a subcategory
    self.dataWidgets_ = widgets.WidgetManager()
    self.dataWidgets_.addWidget( "Data_zaxis",       widgets.TextBox( "NO DATA", "blue", 0, 1,  44, 17, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
    self.dataWidgets_.addWidget( "Data_fan",         widgets.TextBox( "NO DATA", "blue", 3, 1, 102, 17, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
    self.dataWidgets_.addWidget( "Data_lights",      widgets.TextBox( "NO DATA", "blue", 0, 1,  44, 30, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
    self.dataWidgets_.addWidget( "Data_time",        widgets.TextBox( "NO DATA", "blue", 3, 1, 102, 30, 58, 12, self.font_, 0, spacing=0 ), canSelect=False )
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

  def runProfile( self, interval=1.0 ) :
    if self.model_.currentTime_ == -1 : self.model_.currentTime_ = 0
    
    if self.model_.currentTime_ > self.model_.getCurrentTotalTime() :
      # Stop yourself before you wreck yourself
      print( "Profile finished... Stopping [ total profile time : " + str( self.model_.getCurrentTotalTime() ) + "]" )
      self.model_.currentTime_ = -1
      self.mainWidgets_.widgets_[ "PreviewGraph" ].drawPosX_ = 0
      self.profileRunner_.stop()

    #print( "Current time is : " + str( self.model_.currentTime_ ) + " seconds" )
    # Write data to hw controller
    # todo
    
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
    cfgWidget.addInput( self.profileRunner_.start )
    print( "Adding config widget : " + name ) 
    self.configWidgets_.addWidget( name, cfgWidget )

  def handleResAdjustUp( self, direction ) :
    if direction == "press" :
      self.model_.timeResolution_ = np.minimum( self.model_.timeResolution_ + 5, 60 )
      self.mainWidgets_.widgets_[ "Resolution" ].text_ = "Timescale\n" + str( self.model_.timeResolution_ ) + " sec"

  def handleResAdjustDown( self, direction ) :
    if direction == "press" :
      self.model_.timeResolution_ = np.maximum( self.model_.timeResolution_ - 5, 5 )
      self.mainWidgets_.widgets_[ "Resolution" ].text_ = "Timescale\n" + str( self.model_.timeResolution_ ) + " sec"
    
  def buttonPress( self, button ) :
    pressType = self.hwctrl_.buttonMap_[ button.pin.number ] 
    # print( "You pressed " + pressType )

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
  def __init__( self, auth, renderer, server=None ) :
    
    self.renderer_ = renderer
    # No SSL, so 8080
    self.blynk_    = blynklib.Blynk( auth, server=server or "blynk-cloud.com", port=8080 )
    self.com_      = True
    self.blynkthread_ = multitimer.MultiTimer( interval=0.1, function=self.communicate, runonstart=True )

  def communicate( self ) :
    while self.com_ :
      self.blynk_.run()
      
  def run( self ) :
    self.blynkthread_.start()
    print( "Waiting for server to start..." )
    time.sleep( 1 )
    self.blynk_.notify( "BAWCS Online" )

  def stop( self ) :
    self.blynk_.notify( "BAWCS Offline" )
    self.blynkthread_.stop()
  
if __name__ == '__main__':
  
  try:
    hwctrl   = HardwareController( )
    print( "HW Controller Set Up" )

    dataModel = DataModel( )
    dataModel.loadFolder( "config" )
    print( "Data Model Set Up" )
    
    renderer = Renderer( hwctrl, dataModel )
    print( "Renderer Set Up" )

    if USE_BLYNK :
      blynkint = BlynkInterface( open( "cred/.secrets" ).read(), renderer, "192.168.0.10" )
      blynkint.run()
      

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
  

