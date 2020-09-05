# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 21:03:44 2020

@author: Anthony
"""


import PIL
import widgets
import numpy as np

baseCanvas = PIL.Image.new( "RGB", ( 160, 128 ) )
widgetCanvas = PIL.ImageDraw.Draw( baseCanvas )

graph = widgets.Graph( widgetCanvas, x=38, y=44, width=84, height=84 )
graph.gridPxIncx_ = 8
graph.gridPxIncy_ = 8


data = np.array( ( range( 0, 101, 20 ), range( 0, 101, 20 ) ) )

# PIL is weird as fuck and renders in reverse order, layering things underneath
graph.draw()
graph.drawData( data, 10, 10, "blue", "red" )

graph.draw()
baseCanvas.show()