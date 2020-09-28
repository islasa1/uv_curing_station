import gpiozero as gz
from luma.lcd.device import st7735 as luma_st7735
from luma.core.interface.serial import spi as luma_spi
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite

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

    self.outputs_ = {}
    #self.outputs_[ "zaxis" ] = {}
    #self.outputs_[ "zaxis" ][ "ctrl" ] = gz.PhaseEnableMotor(
    self.outputs_[ "fan" ] = gz.PWMOutputDevice( FAN_CTRL )

