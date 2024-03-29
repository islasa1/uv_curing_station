from enum import Enum
import glob
import json
import sys
import numpy as np

# What State the hardware control is in
class ControlModes( Enum ) :
  AUTO_RUN = 0
  MANUAL   = 1
    

class DataSet( object ) :
  def __init__( self, name ) :
    self.name_  = name
    self.time_  = np.zeros( (0) )
    self.value_ = np.zeros( (0) )
    self.lineColor_  = "blue"
    self.pointColor_ = "red"

    # These are NOT the value min/max
    # but the expected absolute max of the system
    self.max_   = 1
    self.min_   = 0

  def normalize( self, value ) :
    return ( value - self.min_ ) / ( self.max_ - self.min_ )
    
        
class Configuration( object ) :
  def __init__( self, name ) :
    self.name_ = name
    self.filename_ = None
    self.datasets_ = {}
    
  def loadFile( self, filename ) :
    print( "Loading " + filename + "..." )
    raw = json.load( open( filename ) )
    self.name_ = raw["name"]

    for data in raw["datasets" ] :
      dataset = DataSet( data["name"] )
      dataset.time_  = np.array( data["time"] )
      dataset.value_ = np.array( data["value"] )
      dataset.min_   = data["min"]
      dataset.max_   = data["max"]
      if "lineColor" in data :
        dataset.lineColor_ = data["lineColor"]
      if "pointColor" in data :
        dataset.pointColor_ = data["pointColor"]
      self.datasets_[dataset.name_] = dataset
     
  
    self.filename_ = filename
    
class DataModel( object ) :
  def __init__( self ) :
    # Config data
    self.configs_ = []
    self.controlMode_ = ControlModes.AUTO_RUN

    # Time graph resolution in seconds
    self.timeResolution_ = 30

    # Current config selected
    self.currentConfigIdx_ = 0

    # Current time into config in seconds
    self.currentTime_ = -1

    self.currentData_ = { "zaxis" : 0, "fan" : 0, "lights" : 0 }
    self.currentTotalTime_ = 0

    #######################
    # Data specific
    self.zaxisEnabled_ = True
    self.fanEnabled_   = True
    self.uvledEnabled_ = True
    #
    #######################

    # where to load from
    self.dataFolder_ = "configs/"

  def loadFolder( self, folder=None ) :
    if folder is not None :
      self.dataFolder_ = folder

    files = glob.glob( self.dataFolder_ + "/*.cfg" )
    
    for cfg in files :
      cfgData = Configuration( "temp" )
      cfgData.loadFile( cfg )
      self.configs_.append( cfgData )

    if self.currentConfigIdx_ is None and len( self.configs_ ) > 0 :
      self.currentConfigIdx_ = 0

  def getProfileNames( self ) :
    return [ cfg.name_ for cfg in self.configs_ ]
      
  def getCurrentConfig( self ) :
    if self.currentConfigIdx_ >= 0 :
      return self.configs_[ self.currentConfigIdx_ ]
    else :
      return None

  def getCurrentTotalTime( self ) :
    if self.controlMode_ == ControlModes.AUTO_RUN :
      currentConfig = self.getCurrentConfig()
      
      if currentConfig is None : return None
      
      # Return longest time
      totalTime = 0
      for name, dataset in currentConfig.datasets_.items() :
        totalTime = np.maximum( np.max( dataset.time_ ), totalTime )

        self.currentTotalTime_ = totalTime
        
    return self.currentTotalTime_

  def getCurrentData( self, data=None ) :

    if self.controlMode_ == ControlModes.AUTO_RUN :
      currentConfig = self.getCurrentConfig()
      if currentConfig is None : return None

      
                
      if data is None :
        for name, dataset in currentConfig.datasets_.items() :
          # Return interpolated data for current time in order of
          # { dataset : value }
          if   name == "zaxis" and not self.zaxisEnabled_ : continue
          elif name == "fan"   and not self.fanEnabled_   : continue
          elif name == "uvled" and not self.uvledEnabled_ : continue
          
          self.currentData_[ name ] = np.interp( self.currentTime_, dataset.time_, dataset.value_ )
          
      else :
        if ( ( data == "zaxis" and self.zaxisEnabled_ ) or
             ( data == "fan"   and self.fanEnabled_   ) or
             ( data == "uvled" and self.uvledEnabled_ ) ) :
          self.currentData_[ data ] = np.interp( self.currentTime_, currentConfig.datasets_[ data ].time_, currentConfig.datasets_[ data ].value_ )
        

    if data is None :
      return self.currentData_
    else :
      return self.currentData_[ data ]
