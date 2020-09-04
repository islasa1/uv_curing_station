# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 21:03:44 2020

@author: Anthony
"""


import PIL
import widgets

baseCanvas = PIL.Image.new( "RGB", ( 256, 256 ) )
widgetCanvas = PIL.ImageDraw.Draw( baseCanvas )

graph=widgets.Graph( widgetCanvas, size=100, dims=3, x=15, y=15, width=100, height=75 )
graph.draw()
graph.lineColors_[0] = "red"
graph.lineColors_[0] = "green"
graph.lineColors_[0] = "blue"

baseCanvas.show()