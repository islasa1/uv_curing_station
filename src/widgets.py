import PIL
import numpy as np

class Widget( object ) :
  def __init__( self, x=0, y=0, width=1, height=1 ):
    self.x_ = x
    self.y_ = y
    self.width_ = width
    self.height_ = height

    self.centerX_ = -1
    self.centerY_ = -1
    self.calcCentroid()
    
    self.fg_     = "white"
    self.bg_     = "black"
    self.selectFg_ = "black"
    self.selectBg_ = "white"
    self.focusFg_ = "black"
    self.focusBg_ = "white"

    self.currentFg_ = self.fg_
    self.currentBg_ = self.bg_
    
    self.selected_ = False
    self.swapOnSelect_ = True
    self.canSelect_    = True

    self.canvas_ = None
    self.links_  = {}
    
    self.onInput_  = []
    self.defocusCondition_ = None
    
    self.hasFocus_ = False
    self.swapOnFocus_ = True
    self.hidden_   = False
    self.name_     = "Widget"

  def setX( self, x ) :
    self.x_ = x
    self.calcCentroid()

  def setY( self, y ) :
    self.y_ = y
    self.calcCentroid()

  def setWidth( self, width ) :
    self.width_ = width
    self.calcCentroid()

  def setHeight( self, height ) :
    self.height_ = height
    self.calcCentroid()

  def setXY( self, x, y ) :
    self.x_ = x
    self.y_ = y
    self.calcCentroid()

  def setWH( self, width, height ) :
    self.width_ = width
    self.height_ = height
    self.calcCentroid()

  def setXY( self, xy ) :
    self.setXY( xy[0], xy[1] )

  def setWH( self, wh ) :
    self.setWH( wh[0], wh[1] )

  def calcCentroid( self ) :
    self.centerX_ = self.x_ + self.width_ / 2
    self.centerY_ = self.y_ + self.height_ / 2

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

  def focus( self ) :
    self.hasFocus_ = True
    if self.swapOnFocus_ :
      self.swapCurrentColors( self.focusFg_, self.focusBg_ )
  def defocus( self ) :
    self.hasFocus_ = False
    if self.swapOnFocus_ :
      self.swapCurrentColors( self.fg_, self.bg_ )

  def addInput( self, handler ) :
    self.onInput_.append( handler )
    
  def onInput( self, direction ) :
    print( "Processing onInput( " + direction + " ) for Widget " + self.name_ )

    # Check for defocus before handling state change
    if self.defocusCondition_ is None or self.defocusCondition_( direction ) :
      # operation done
      self.defocus()
      
    if len( self.onInput_ ) > 0 :
      for handler in self.onInput_ :
        handler( direction )
      
    
      
  def swapCurrentColors( self, fg, bg ) :
    self.currentFg_ = fg
    self.currentBg_ = bg      
      
  def select( self ) :
    self.selected_ = True
    # swap colors
    if self.swapOnSelect_ :
      self.swapCurrentColors( self.selectFg_, self.selectBg_ )

  def deselect( self ) :
    self.selected_ = False
    if self.swapOnSelect_ :
      self.swapCurrentColors( self.fg_, self.bg_ )
    
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
  def __init__( self, text=None, color="green",  textPosX=0, textPosY=0, x=0, y=0, width=1, height=1, font=None, borderpx=2, aligned="left", spacing=4 ) :
    super(TextBox, self).__init__( x, y, width, height )
    self.borderpx_  = borderpx
    self.text_      = text or "Hello World!"
    self.textColor_ = color
    self.font_      = font
    self.textPosX_  = textPosX
    self.textPosY_  = textPosY
    self.align_     = aligned
    self.spacing_   = spacing

  def render( self ) :
    self.canvas_.rectangle( [ self.x_, self.y_, self.x_ + self.width_, self.y_ + self.height_ ], fill=self.currentBg_, outline=self.currentFg_, width=self.borderpx_  )
    self.canvas_.text( [ self.textPosX_ + self.x_, self.textPosY_ + self.y_ ], self.text_, font=self.font_, fill=self.textColor_, align=self.align_, spacing=self.spacing_ )

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
    self.canvas_.rectangle( [ self.x_, self.y_, self.x_ + self.width_, self.y_ + self.height_ ], fill=self.currentBg_, outline=self.currentFg_, width=self.borderpx_  )

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
    dataToDrawY   = data[1][indicesToDraw]
    
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
    # print( "X : " + str( dataToDrawX ) )
    # print( "Y : " + str( dataToDrawY ) )
    # print( pts )
    
    self.canvas_.line( pts, fill=color, width=1 )
    self.canvas_.point( pts, fill=ptColor )

class WidgetManager( Widget ) :
  def __init__( self ) :
    super(WidgetManager, self).__init__( )
    self.widgets_ = {}
    # For when we need order
    self.widgetsList_ = []
    self.currentWidget_ = None
    self.defaultWidget_ = None
    self.adjustCentroid_ = True

  def onInput( self, direction ) :
    print( "Inside of manager : " + self.name_ )
    if self.currentWidget_ is None :
      self.currentWidget_ = self.defaultWidget_
      if self.currentWidget_ is None :
        self.currentWidget_.select()
    else :
            
      if not self.currentWidget_.hasFocus() :
        if direction == "press" :
          self.currentWidget_.focus()
          # self.currentWidget_.onInput( direction )
        else :
          # First filter by all widgets to the direction of what we want
          # then by how close they
          widgetSelect = None
          pointA       = np.array( ( self.currentWidget_.centerX_, self.currentWidget_.centerY_ ) )
          lastDistance = -1
        
          for name, widget in self.widgets_.items() :          
            if ( widget.canSelect_ and
                 ( ( direction == "up" and widget.centerY_ < self.currentWidget_.centerY_    ) or
                   ( direction == "down" and widget.centerY_ > self.currentWidget_.centerY_  ) or 
                   ( direction == "left" and widget.centerX_ < self.currentWidget_.centerX_  ) or 
                   ( direction == "right" and widget.centerX_ > self.currentWidget_.centerX_ ) ) ) :
              pointB   = np.array( ( widget.centerX_, widget.centerY_ ) )
              distance = np.linalg.norm( pointA - pointB )
            
              if widgetSelect is None or distance < lastDistance :
                widgetSelect = widget
                lastDistance = distance
              
          if widgetSelect is not None :
            self.currentWidget_.deselect()
            widgetSelect.select()
            self.currentWidget_ = widgetSelect
          
      else :
        # Widget has focus from main control method, go to its handler
        self.currentWidget_.onInput( direction )

    print( "Current Widget for " + self.name_ + " is " + self.currentWidget_.name_ + " ( has focus : " + str( self.currentWidget_.hasFocus() ) + ")" )

  def addWidget( self, name, widget, canSelect=True ) :
    if self.defaultWidget_ is None : self.defaultWidget_ = widget
    self.widgets_[ name ] = widget
    self.widgetsList_.append( widget )
    self.widgets_[ name ].canSelect_ = canSelect
    
    # Revalutate center
    if self.adjustCentroid_ :
      
      x = [ v.centerX_ for k, v in self.widgets_.items() ]
      y = [ v.centerY_ for k, v in self.widgets_.items() ]

      self.centerX_ = np.sum( x ) / len( x )
      self.centerY_ = np.sum( y ) / len( y )
  
  def getCurrentWidgetIndex( self ) :
    if self.currentWidget_ is not None :
      return self.widgetsList_.index( self.currentWidget_ )
    else :
      return 0
