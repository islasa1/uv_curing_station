#!/usr/bin/env python3

import luma_device
import luma.core.render as luma_render
import luma.core.sprite_system as luma_sprite 
import sys
import signal 

if __name__ == '__main__':
  device = luma_device( sys.argv[1] )
  frameReg = luma_sprite.framerate_regulator( fps=30 )

  with frameReg :
    with luma_render.canvas( device, dither=True ) as draw :

      draw.arc( [ 20, 20, 85, 85 ], 45, 135 )