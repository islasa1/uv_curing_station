#!/usr/bin/env python3

import gpiozero as gz
import luma_device
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite 
import sys
import signal
import widgets
import numpy as np

KEY_UP_PIN     = 6
KEY_DOWN_PIN   = 19
KEY_LEFT_PIN   = 5
KEY_RIGHT_PIN  = 26
KEY_PRESS_PIN  = 13
KEY1_PIN       = 21
KEY2_PIN       = 20
KEY3_PIN       = 16

class HardwareController( object ) :
  def __init__( self, config ) :
    self.device_ = luma_device.get_device( config )
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
  def __init__( self, ctrl ) :
    self.hwctrl_ = ctrl
    self.hwctrl_.buttons_[ "up"    ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "down"  ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "left"  ].when_pressed = self.buttonPress
    self.hwctrl_.buttons_[ "right" ].when_pressed = self.buttonPress

    self.graph_    = widgets.Graph( x=38, y=44, width=84, height=84 )
    self.graph_.gridPxIncx_ = 8
    self.graph_.gridPxIncy_ = 8

  
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

    self.render()
      
  def render( self ) :
    data = np.array( ( range( 0, 101, 20 ), range( 0, 101, 20 ) ) )

    with self.hwctrl_.frameReg_ :
      with luma_render.canvas( self.hwctrl_.device_, dither=True ) as canvas :  
        self.graph_.draw( canvas )
        self.graph_.drawData( data, 10, 10, "blue", "red" )  
    

  
if __name__ == '__main__':

  try:
    hwctrl   = HardwareController( sys.argv[1] )
    print( "HW Controller Set Up" )
    renderer = Renderer( hwctrl )
    print( "Renderer Set Up" )

    renderer.render()
    signal.pause()
  except :
    print( "Failed to start program." )
    raise 

