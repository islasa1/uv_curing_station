#!/usr/bin/env python3

# import gpiozero as gz
# from luma.lcd.device import st7735 as luma_st7735
# from luma.core.interface.serial import spi as luma_spi
# import luma.core.render as luma_render
# import luma.core.sprite_system as luma_sprite

# from PIL import ImageFont, ImageColor, Image

# import multitimer
# import widgets

USE_BLYNK=True

import signal
import atexit

import hardware
import renderer
import model

if USE_BLYNK :
  import blynkinterface

class Capture:
  def __init__(self):
    self.captured = []
  def __eq__(self, other):
    self.captured.append(other)
    return False

  
if __name__ == '__main__':
  
  try:
    blynkint = None
    if USE_BLYNK :
      blynkint = blynkinterface.BlynkInterface( open( "cred/.secrets" ).read(), "192.168.0.10" )
      blynkint.run()
      
    hwctrl   = hardware.HardwareController( )
    print( "HW Controller Set Up" )

    dataModel = model.DataModel( )
    dataModel.loadFolder( "config" )
    print( "Data Model Set Up" )
    
    renderer = renderer.Renderer( hwctrl, dataModel )
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
  

