import PIL
import numpy as np

class Widget( object ) :
  def __init__( self, x=0, y=0, width=1, height=1 ):
    self.x_ = x
    self.y_ = y
    self.width_ = width
    self.height_ = height
    self.fg_     = "white"
    self.bg_     = "black"
    self.activeFg_ = "black"
    self.activeBg_ = "white"
    self.selected_ = False
    self.swapOnSelect_ = True
    self.canvas_ = None
    self.links_  = {}
    self.onInput_  = None
    self.hasFocus_ = False
    self.hidden_   = False
    self.name_     = "Widget" 

  def setX( self, x ) :
    self.x_ = x

  def setY( self, y ) :
    self.y_ = y

  def setWidth( self, width ) :
    self.width_ = width

  def setHeight( self, height ) :
    self.height_ = height

  def setXY( self, x, y ) :
    self.x_ = x
    self.y_ = y

  def setWH( self, width, height ) :
    self.width_ = width
    self.height_ = height

  def setXY( self, xy ) :
    self.setXY( xy[0], xy[1] )

  def setWH( self, wh ) :
    self.setWH( wh[0], wh[1] )

  def setForeground( self, color ) :
    self.fg_ = color

  def setBackground( self, color ) :
    self.bg_ = color

  def hide( self ) :
    self.hidden_ = True
  def unhide( self ) :
    self.hidden_ = False
    
  def hasFocus( self ) :
    return self.hasFocus_

  def onInput( self, inputType="press" ) :
    if self.onInput_ is not None :
      self.onInput_( inputType )
      
  def swapActiveColors( self ) :
    if self.swapOnSelect_ :
      tmp = self.fg_
      self.fg_ = self.activeFg_
      self.activeFg_ = tmp
      tmp = self.bg_
      self.bg_ = self.activeBg_
      self.activeBg_ = tmp
      
      
  def select( self ) :
    self.selected_ = True
    # swap colors
    self.swapActiveColors()

  def deselect( self ) :
    self.selected_ = False
    self.swapActiveColors()
    
  def link( self, direction, widget ) :
    self.links_[direction] = widget

  def getLink( self, direction ) :
    if direction in self.links_ :
      self.links_[direction].select()
      self.deselect()
      return self.links_[direction]
    else :
      return None

  def draw( self, canvas ) :
    if not self.hidden_ :
      self.canvas_ = canvas
      self.render()

  def render( self ) :
    pass


class TextBox( Widget ):
  """A Scolling graph"""
  def __init__( self, text=None, color="green",  textPosX=0, textPosY=0, x=0, y=0, width=1, height=1, font=None, borderpx=2, aligned="left" ) :
    super(TextBox, self).__init__( x, y, width, height )
    self.borderpx_  = borderpx
    self.text_      = text or "Hello World!"
    self.textColor_ = color
    self.font_      = font
    self.textPosX_  = textPosX
    self.textPosY_  = textPosY
    self.align_     = aligned

  def render( self ) :
    self.canvas_.rectangle( [ self.x_, self.y_, self.x_ + self.width_, self.y_ + self.height_ ], fill=self.bg_, outline=self.fg_, width=self.borderpx_  )
    self.canvas_.text( [ self.textPosX_ + self.x_, self.textPosY_ + self.y_ ], self.text_, font=self.font_, fill=self.textColor_, align=self.align_ )

class Graph(Widget):
  """A Scolling graph"""
  def __init__( self, x=0, y=0, width=1, height=1 ):
    super(Graph, self).__init__( x, y, width, height )
    self.drawPosX_ = 0
    self.drawPosY_ = 0
    self.borderpx_ = 2
    self.gridpx_   = 1
    self.gridcolor_ = "darkgreen"

    # pixels to increment by 
    self.gridPxIncx_  = 5
    self.gridPxIncy_  = 5
    
    self.dataStart_   = 0
    self.dataEnd_     = 0
    self.dataMin_     = 0
    self.dataMax_     = 0

  def moveLeft( self ) :
    self.drawPosX_ -= 1

  def moveRight( self ) :
    self.drawPosX_ += 1

  def moveUp( self ) :
    self.drawPosY_ -= 1

  def moveDown( self ) :
    self.drawPosY_ += 1 

  def render( self ) :
    self.canvas_.rectangle( [ self.x_, self.y_, self.x_ + self.width_, self.y_ + self.height_ ], fill=None, outline=self.fg_, width=self.borderpx_  )

    for linePos in range( self.x_ + self.borderpx_,
                          self.x_ + self.width_ - self.borderpx_,
                          self.gridPxIncx_
                          ) :
      self.canvas_.line( 
                        [ linePos, self.y_ + self.borderpx_, 
                          linePos, self.y_ + self.height_ - self.borderpx_ ],
                          self.gridcolor_
                        )

    for linePos in range( 
                          self.y_ + self.height_ - self.borderpx_,
                          self.y_ + self.borderpx_, 
                          -( self.gridPxIncy_ ) 
                          ) :
      self.canvas_.line( 
                        [ self.x_ + self.borderpx_, linePos, 
                          self.x_ + self.width_ - self.borderpx_, linePos ],
                          self.gridcolor_
                        )

  def getXDataPx( self, data ) :
    return ( ( data - self.dataStart_ ) / ( self.dataEnd_ - self.dataStart_ ) ) * ( self.width_ - 2 * self.borderpx_ ) + ( self.x_ + self.borderpx_ )
  def getYDataPx( self, data ) :
    return ( 1.0 - ( data - self.dataMin_ ) / ( self.dataMax_ - self.dataMin_ ) ) * ( self.height_ - 2 * self.borderpx_ )  + ( self.y_ + self.borderpx_ )

  
  def drawData( self, data, incx, incy, color, ptColor, canvas=None ) :
    if self.hidden_ : return
    
    if canvas is not None :
      # overwrite current canvas
      self.canvas_ = canvas
      
    # First find start position based on current draw position
    dataPerPixX = incx / self.gridPxIncx_
    dataPerPixY = incy / self.gridPxIncx_

    self.dataStart_   = self.drawPosX_ * dataPerPixX
    self.dataEnd_     = dataPerPixX * ( self.width_ - 2 * self.borderpx_ ) + self.dataStart_

    self.dataMin_     = self.drawPosY_ * dataPerPixY
    self.dataMax_     = dataPerPixY * ( self.height_ - 2 * self.borderpx_ ) + self.dataMin_

    # print( "Plotting from X[ " + str( self.dataStart_ ) + ", " + str( self.dataEnd_ ) + " ] between Y[ " + str( self.dataMin_ ) + ", " + str( self.dataMax_ ) + " ]" )

    # Find bounding data
    indicesToDraw = ( data[0] >= self.dataStart_ ) & ( data[0] <= self.dataEnd_ )

    dataToDrawX   = data[0][indicesToDraw]
    dataToDrawY   = data[0][indicesToDraw]

    interpLeft     = False
    interpLeftIdx  = 0
    interpRight    = False
    interpRightIdx = 0


    if self.dataStart_ != dataToDrawX[0] : 
      interpLeftIdx = np.where( indicesToDraw == True )[0][0] - 1
      if interpLeftIdx > -1 :
        interpLeft  = True
    if self.dataEnd_   != dataToDrawX[-1] : 
      interpRightIdx = np.where( indicesToDraw == True )[0][-1] + 1
      if interpRightIdx < indicesToDraw.shape[0] :
        interpRight  = True


    if interpLeft :
      # LERP to start
      yValueLeft = np.interp( self.dataStart_, [ data[0][interpLeftIdx], dataToDrawX[0] ], [ data[1][interpLeftIdx], dataToDrawY[0] ] )

      self.canvas_.line( [ ( self.getXDataPx( self.dataStart_ ), self.getYDataPx( yValueLeft ) ), 
                           ( self.getXDataPx( dataToDrawX[0] ), self.getYDataPx( dataToDrawY[0] ) ) ],
                           fill=color,
                           width=1
                           )
      
    if interpRight :
      # LERP to start
      yValueRight = np.interp( self.dataEnd_, [ dataToDrawX[-1], data[0][interpRightIdx] ], [ dataToDrawY[-1], data[1][interpRightIdx] ] )

      self.canvas_.line( [ ( self.getXDataPx( dataToDrawX[-1] ), self.getYDataPx( dataToDrawY[-1] ) ),
                           ( self.getXDataPx( self.dataEnd_ ), self.getYDataPx( yValueRight ) ) ],
                           fill=color,
                           width=1
                           )

    # Now rest of lines
    pts = list( zip( self.getXDataPx( dataToDrawX ), self.getYDataPx( dataToDrawY ) ) )
    # print( pts )
    self.canvas_.line( pts, fill=color, width=1 )
    self.canvas_.point( pts, fill=ptColor )

