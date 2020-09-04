import PIL
import numpy as np

class Widget( object ) :
  def __init__( self, canvas, x=0, y=0, width=1, height=1 ):
    self.x_ = x
    self.y_ = y
    self.width_ = width
    self.height_ = height
    self.fg_     = "white"
    self.bg_     = "black"
    self.canvas_ = canvas

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

  def flush( self, img ) :
    self.canvas_.merge( self.draw() )

  def draw( self ) :
    pass


class Graph(Widget):
  """A Scolling graph"""
  def __init__( self, canvas, size=50, x=0, y=0, width=1, height=1 ):
    super(Graph, self).__init__( canvas, x, y, width, height )
    self.size_ = size
    self.drawPos_ = size
    self.borderpx_ = 2
    self.gridpx_   = 1
    self.gridcolor_ = "green"

    # pixels to increment by 
    self.gridincx_  = 5
    self.gridincy_  = 5

    self.leftAligned_ = True
    self.threshold_   = -1


  def drawLeftAligned( self, policy ) :
    self.leftAligned_ = policy

  def setDataSize( self, size ) :
    self.size_ = size
    for data in self.data_ :
      data.resize( size )

  def setDrawPos( self, pos ) :
    self.drawPos_ = pos % self.size_

  def assignDataPos( self, pos, index=0 ) :
    self.currentPos_[index] = pos % self.size_

  def prepend( self, data, index=0 ) :
    self.assignDataPos( self.currentPos_[index] + 1 )
    self.data_[index][self.currentPos_[index]] = data

  def append( self, data, index=0 ) :
    self.assignDataPos( self.currentPos_[index] - 1 )
    self.data_[index][self.currentPos_] = data

  def moveLeft( self ) :
    self.setDrawPos( self.drawPos_ - 1 )

  def moveRight( self ) :
    self.setDrawPos( self.drawPos_ + 1 )

  def draw( self ) :
    self.canvas_.rectangle( [ self.x_, self.y_, self.x_ + self.width_, self.y_ + self.height_ ], fill=self.bg_, outline=self.fg_, width=self.borderpx_  )

    for linePos in range( self.x_,
                          self.x_ + self.width_, 
                          self.gridincx_ + self.gridpx_
                          ) :
      self.canvas_.line( 
                        [ linePos, self.y_ + self.borderpx_, 
                          linePos, self.y_ + self.height_ - self.borderpx_ ] 
                        )

    for linePos in range( 
                          self.y_ + self.height_, 
                          self.y_, 
                          -( self.gridincy_ + self.gridpx_ ) 
                          ) :
      self.canvas_.line( 
                        [ self.x_ + self.borderpx_, linePos, 
                          self.x_ + self.width_ - self.borderpx_, linePos ] 
                        )
  # list( zip( x[0], y[0]  ) )
  def drawData( self, data, color ) :

    # Data should be all the data we are showing + 1 on each side
    # this means that all data will need to be buffered and a data point of 1
    # will actually have 3 indices
    # This is to simplify my drawing life
    minDataX = np.min( data[0][1:-1] )
    maxDataX = np.max( data[0][1:-1] )

    minDataY = np.min( data[1][1:-1] )
    maxDataY = np.max( data[1][1:-1] )

    dataToDrawX = np.append(  )

    self.canvas_.line( 
                        list( zip( x[0], x[1] ) ),

                          






