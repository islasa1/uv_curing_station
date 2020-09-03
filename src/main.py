#!/usr/bin/env python3

import luma_device
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite 
import sys
import signal 

if __name__ == '__main__':
  device = luma_device.get_device( sys.argv[1] )
  frameReg = luma_sprite.framerate_regulator( fps=30 )

  
  for deg in range( 0, 135, 5 ) :

    with frameReg :
      with luma_render.canvas( device, dither=True ) as draw :

        draw.arc( [ 20, 20, 85, 85 ], 45 + deg, 135 + deg, width=2, fill="green" )
#      signal.pause()
