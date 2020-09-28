import builtins
import io
from datetime import datetime

import blynklib

class BlynkInterface( object ) :
  def __init__( self, auth, server=None ) :

    # PRINT HACKS
    self._print = print
    builtins.print = self.debugPrint
    
    self.renderer_ = None
    # No SSL, so 8080
    self.blynk_    = blynklib.Blynk( auth, server=server or "blynk-cloud.com", port=8080 )
    # WHYYYYYY
    self.blynk_.VPIN_MAX_NUM = 255
    
    self.com_      = True
    self.blynkthread_ = multitimer.MultiTimer( interval=0.1, function=self.communicate, runonstart=True )

    # We will keep track of whether to ignore writes of zero - this is to filter out button taps
    # that write zero out as a signal
    self.pins_ = {}
    self.pins_[ "main_terminal" ] = { "vnum" : 255, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_terminal" ] = { "vnum" : 254, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_terminal" ] = { "vnum" : 253, "value" : 0, "ignoreZero" : False }
    self.pins_[ "poweroff" ] = { "vnum" : 252, "value" : 0, "ignoreZero" : True }
    self.pins_[ "cpu_usage"       ] = { "vnum" : 251, "value" : 0, "ignoreZero" : False }
    self.pins_[ "cpu_temperature" ] = { "vnum" : 250, "value" : 0, "ignoreZero" : False }

    # Manual Mode
    self.pins_[ "zaxis"            ] = { "vnum" : 0, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_zaxis_inc" ] = { "vnum" : 3, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_zaxis_rst" ] = { "vnum" : 6, "value" : 0, "ignoreZero" : True }

    self.pins_[ "fan"            ] = { "vnum" : 1, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_fan_inc" ] = { "vnum" : 4, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_fan_rst" ] = { "vnum" : 7, "value" : 0, "ignoreZero" : True }
    
    self.pins_[ "uvled"            ] = { "vnum" : 2, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_uvled_inc" ] = { "vnum" : 5, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_uvled_rst" ] = { "vnum" : 8, "value" : 0, "ignoreZero" : True }

    self.pins_[ "manual_rst_all"     ] = { "vnum" :  9, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_start_timer" ] = { "vnum" : 10, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_stop_timer" ] = { "vnum" : 51, "value" : 0, "ignoreZero" : True }
    
    self.pins_[ "manual_hardware_preview" ] = { "vnum" : 11, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_mode"      ] = { "vnum" : 12, "value" : 0, "ignoreZero" : False }

    self.pins_[ "manual_time_rem" ] = { "vnum" : 13, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_time_sec" ] = { "vnum" : 14, "value" : 0, "ignoreZero" : False }
    self.pins_[ "manual_time_min" ] = { "vnum" : 15, "value" : 0, "ignoreZero" : False }

    self.pins_[ "active_profile" ] = { "vnum" : 17, "value" : 0, "ignoreZero" : False }
    self.pins_[ "auto_mode"      ] = { "vnum" : 16, "value" : 0, "ignoreZero" : False }
    self.pins_[ "auto_runner"    ] = { "vnum" : 18, "value" : 0, "ignoreZero" : False }
    self.pins_[ "active_data"    ] = { "vnum" : 19, "value" : 0, "ignoreZero" : False }
    
    self.pins_[ "edit_profile"          ] = { "vnum" : 20, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_resolution"       ] = { "vnum" : 21, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_hardware_preview" ] = { "vnum" : 22, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_profile_preview"  ] = { "vnum" : 23, "value" : 0, "ignoreZero" : False }

    self.pins_[ "edit_zaxis_text"  ] = { "vnum" : 24, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_fan_text"    ] = { "vnum" : 25, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_uvled_text"  ] = { "vnum" : 26, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_time_text"   ] = { "vnum" : 27, "value" : 0, "ignoreZero" : False }
    

    self.pins_[ "edit_data"    ] = { "vnum" : 28, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_value"   ] = { "vnum" : 29, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_time "   ] = { "vnum" : 30, "value" : 0, "ignoreZero" : False }

    self.pins_[ "edit_run_preview"  ] = { "vnum" : 31, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_point"    ] = { "vnum" : 32, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_add"      ] = { "vnum" : 33, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_delete_point" ] = { "vnum" : 34, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_save"     ] = { "vnum" : 35, "value" : 0, "ignoreZero" : True }

    self.pins_[ "edit_zaxis_disabled"   ] = { "vnum" : 36, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_fan_disabled"     ] = { "vnum" : 37, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_uvled_disabled"   ] = { "vnum" : 38, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_profile_name" ] = { "vnum" : 39, "value" : 0, "ignoreZero" : False }
    self.pins_[ "edit_filename"     ] = { "vnum" : 40, "value" : 0, "ignoreZero" : False }

    self.pins_[ "edit_duplicate"      ] = { "vnum" : 41, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_new_profile"    ] = { "vnum" : 42, "value" : 0, "ignoreZero" : True }
    self.pins_[ "edit_delete_profile" ] = { "vnum" : 43, "value" : 0, "ignoreZero" : True }

    self.pins_[ "settings_global_zaxis_disabled" ] = { "vnum" : 44, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_global_fan_disabled"   ] = { "vnum" : 45, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_global_uvled_disabled" ] = { "vnum" : 46, "value" : 0, "ignoreZero" : False }

    self.pins_[ "settings_manual_half_notify_disabled" ] = { "vnum" : 47, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_manual_full_notify_disabled" ] = { "vnum" : 48, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_auto_half_notify_disabled" ] = { "vnum" : 49, "value" : 0, "ignoreZero" : False }
    self.pins_[ "settings_auto_full_notify_disabled" ] = { "vnum" : 50, "value" : 0, "ignoreZero" : False }
    
    self.virtualPinMap_ = {}
    for key, value in self.pins_.items() :
      self.virtualPinMap_[ value[ "vnum" ] ] = { "name" : key }
      self.pins_[ key ][ "handler" ] = self.main_handler

      if "edit" in key :
        self.pins_[ key ][ "handler" ] = self.edit_handler
      elif "settings" in key :
        self.pins_[ key ][ "handler" ] = self.settings_handler
        
    
    print( "Manual decoration for Blynk Server..." )
    blynklib.Blynk.handle_event( self.blynk_, "connect")( self.connect_handler )
    blynklib.Blynk.handle_event( self.blynk_, 'internal_rtc' )( self.rtc_handler )

    blynklib.Blynk.handle_event( self.blynk_, 'write V*' )( self.pinwrite_handler )
    # blynklib.Blynk.handle_event( self.blynk_, 'write *' )( self.pinwrite_handler )

  def debugPrint( self, *args, **kw ) :
    oldstdout = sys.stdout
    newstdout = io.StringIO()
    sys.stdout = newstdout
    
    self._print( *args, **kw )
    output = newstdout.getvalue()[:-1]
    
    if hasattr( self, "blynk_" ) and self.blynk_ is not None and self.blynk_._socket is not None :
      if hasattr( self, "pins_" ) and "settings_terminal" in  self.pins_ :
        self.blynk_.virtual_write( self.pins_[ "settings_terminal" ][ "vnum" ], output )

    sys.stdout = oldstdout
    self._print( output )

  def syncAll( self ) :
    for key, value in self.pins_.items() :
      if key == "main_terminal" :
        self.pins_[ "main_terminal" ]["value"] = ""
      elif key == "settings_terminal" :
        self.pins_[ "settings_terminal" ]["value"] = ""
      elif key == "edit_terminal" :
        self.pins_[ "edit_terminal" ]["value"] = ""
      elif key == "poweroff" :
        self.pins_[ "poweroff" ]["value"] = 0
      elif key == "cpu_usage" :
        self.pins_[ "cpu_usage"       ]["value"] = str( os.popen("top -n1 | awk '/Cpu\(s\):/ {print $2}'").readline() )
      elif key == "cpu_temperature" :
        self.pins_[ "cpu_temperature" ]["value"] = gz.CPUTemperature().temperature
      elif key == "zaxis" :
        self.pins_[ "zaxis"            ]["value"] = self.renderer_.model_.getCurrentData( "zaxis" )
      # elif key == "manual_zaxis_inc" :
      #   self.pins_[ "manual_zaxis_inc" ]["value"] = 0
      # elif key == "manual_zaxis_rst" :
      #   self.pins_[ "manual_zaxis_rst" ]["value"] = 0
      elif key == "fan" :
        self.pins_[ "fan"            ]["value"] = self.renderer_.model_.getCurrentData( "fan" )
      # elif key == "manual_fan_inc" :
      #   self.pins_[ "manual_fan_inc" ]["value"] = 
      # elif key == "manual_fan_rst" :
      #   self.pins_[ "manual_fan_rst" ]["value"] = 
      elif key == "uvled" :
        self.pins_[ "uvled"            ]["value"] = self.renderer_.model_.getCurrentData( "lights" )
      # elif key == "manual_uvled_inc" :
      #   self.pins_[ "manual_uvled_inc" ]["value"] = 
      # elif key == "manual_uvled_rst" :
      #   self.pins_[ "manual_uvled_rst" ]["value"] = 
      elif key == "manual_rst_all" :
        self.pins_[ "manual_rst_all"     ]["value"] = 0
      elif key == "manual_start_timer" :
        self.pins_[ "manual_start_timer" ]["value"] = 0
      elif key == "manual_stop_timer" :
        self.pins_[ "manual_stop_timer" ]["value"] = 0
      elif key == "manual_hardware_preview" :
        self.pins_[ "manual_hardware_preview" ]["value"] = 0
      elif key == "manual_mode" :
        self.pins_[ "manual_mode"      ]["value"] = 0
      elif key == "manual_time_rem" :
        self.pins_[ "manual_time_rem" ]["value"] = 0
      elif key == "manual_time_sec" :
        self.pins_[ "manual_time_sec" ]["value"] = 0
      elif key == "manual_time_min" :
        self.pins_[ "manual_time_min" ]["value"] = 0
      elif key == "active_profile" :
        self.pins_[ "active_profile" ]["value"] = 0
      elif key == "auto_mode" :
        self.pins_[ "auto_mode"      ]["value"] = 0
      elif key == "auto_runner" :
        self.pins_[ "auto_runner"    ]["value"] = 0
      elif key == "active_data" :
        self.pins_[ "active_data"    ]["value"] = 0
      elif key == "edit_profile" :
        self.pins_[ "edit_profile"          ]["value"] = 0
      elif key == "edit_resolution" :
        self.pins_[ "edit_resolution"       ]["value"] = 0
      # elif key == "edit_hardware_preview" :
      #   self.pins_[ "edit_hardware_preview" ]["value"] = 
      # elif key == "edit_profile_preview" :
      #   self.pins_[ "edit_profile_preview"  ]["value"] = 
      elif key == "edit_zaxis_text" :
        self.pins_[ "edit_zaxis_text"  ]["value"] = 0
      elif key == "edit_fan_text" :
        self.pins_[ "edit_fan_text"    ]["value"] = 0
      elif key == "edit_uvled_text" :
        self.pins_[ "edit_uvled_text"  ]["value"] = 0
      elif key == "edit_time_text" :
        self.pins_[ "edit_time_text"   ]["value"] = 0
      elif key == "edit_data" :
        self.pins_[ "edit_data"    ]["value"] = 0
      elif key == "edit_value" :
        self.pins_[ "edit_value"   ]["value"] = 0
      elif key == "edit_time " :
        self.pins_[ "edit_time "   ]["value"] = 0
      elif key == "edit_run_preview" :
        self.pins_[ "edit_run_preview"  ]["value"] = 0
      elif key == "edit_point" :
        self.pins_[ "edit_point"    ]["value"] = 0
      elif key == "edit_add" :
        self.pins_[ "edit_add"      ]["value"] = 0
      elif key == "edit_delete_point" :
        self.pins_[ "edit_delete_point" ]["value"] = 0
      elif key == "edit_save" :
        self.pins_[ "edit_save"     ]["value"] = 0
      elif key == "edit_zaxis_disabled" :
        self.pins_[ "edit_zaxis_disabled"   ]["value"] = 0
      elif key == "edit_fan_disabled" :
        self.pins_[ "edit_fan_disabled"     ]["value"] = 0
      elif key == "edit_uvled_disabled" :
        self.pins_[ "edit_uvled_disabled"   ]["value"] = 0
      elif key == "edit_profile_name" :
        self.pins_[ "edit_profile_name" ]["value"] = self.renderer_.model_.getCurrentConfig().name_
      elif key == "edit_filename" :
        self.pins_[ "edit_filename"     ]["value"] = self.renderer_.model_.getCurrentConfig().filename_
      elif key == "edit_duplicate" :
        self.pins_[ "edit_duplicate"      ]["value"] = 0
      elif key == "edit_new_profile" :
        self.pins_[ "edit_new_profile"    ]["value"] = 0
      elif key == "edit_delete_profile" :
        self.pins_[ "edit_delete_profile" ]["value"] = 0
      elif key == "settings_global_zaxis_disabled" :
        self.pins_[ "settings_global_zaxis_disabled" ]["value"] = 0
      elif key == "settings_global_fan_disabled" :
        self.pins_[ "settings_global_fan_disabled"   ]["value"] = 0
      elif key == "settings_global_uvled_disabled" :
        self.pins_[ "settings_global_uvled_disabled" ]["value"] = 0
      elif key == "settings_manual_half_notify_disabled" :
        self.pins_[ "settings_manual_half_notify_disabled" ]["value"] = 0
      elif key == "settings_manual_full_notify_disabled" :
        self.pins_[ "settings_manual_full_notify_disabled" ]["value"] = 0
      elif key == "settings_auto_half_notify_disabled" :
        self.pins_[ "settings_auto_half_notify_disabled" ]["value"] = 0
      elif key == "settings_auto_full_notify_disabled" :
        self.pins_[ "settings_auto_full_notify_disabled" ]["value"] = 0

      self.blynk_.virtual_write( self.pins_[key][ "vnum" ], self.pins_[key]["value"] )

  def main_handler( self, pin ) :
    print( "In main handler via pin " + str( pin ) + " called " + self.virtualPinMap_[ pin ][ "name" ] )

    # elif self.virtualPinMap_[pin]["name"] == "main_terminal" :
    #   self.pins_[ "main_terminal" ]
    if self.virtualPinMap_[pin]["name"] == "zaxis" :
      if self.renderer_.model_.controlMode_ != ControlModes.AUTO_RUN :
        self.renderer_.model_.currenData_[ "zaxis" ] = self.pins_[ "zaxis" ][ "value" ]
      else :
        # Shoot back to user and revert
        print( "ERROR: Not in manual mode. Please switch to manual mode to change values..." )
        self.blynk_.virtual_write( pin, self.renderer_.model_.currenData_[ "zaxis" ] )

    elif self.virtualPinMap_[pin]["name"] == "manual_zaxis_inc" :
      self.pins_[ "manual_zaxis_inc" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_zaxis_rst" :
      self.pins_[ "manual_zaxis_rst" ]
    elif self.virtualPinMap_[pin]["name"] == "fan" :
      self.pins_[ "fan"            ]
    elif self.virtualPinMap_[pin]["name"] == "manual_fan_inc" :
      self.pins_[ "manual_fan_inc" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_fan_rst" :
      self.pins_[ "manual_fan_rst" ]
    elif self.virtualPinMap_[pin]["name"] == "uvled" :
      self.pins_[ "uvled"            ]
    elif self.virtualPinMap_[pin]["name"] == "manual_uvled_inc" :
      self.pins_[ "manual_uvled_inc" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_uvled_rst" :
      self.pins_[ "manual_uvled_rst" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_rst_all" :
      self.pins_[ "manual_rst_all"     ]
    elif self.virtualPinMap_[pin]["name"] == "manual_start_timer" :
      self.pins_[ "manual_start_timer" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_stop_timer" :
      self.pins_[ "manual_stop_timer" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_hardware_preview" :
      self.pins_[ "manual_hardware_preview" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_mode" :
      self.pins_[ "manual_mode"      ]
    elif self.virtualPinMap_[pin]["name"] == "manual_time_rem" :
      self.pins_[ "manual_time_rem" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_time_sec" :
      self.pins_[ "manual_time_sec" ]
    elif self.virtualPinMap_[pin]["name"] == "manual_time_min" :
      self.pins_[ "manual_time_min" ]
    elif self.virtualPinMap_[pin]["name"] == "active_profile" :
      self.pins_[ "active_profile" ]
    elif self.virtualPinMap_[pin]["name"] == "auto_mode" :
      self.pins_[ "auto_mode"      ]
    elif self.virtualPinMap_[pin]["name"] == "auto_runner" :
      self.pins_[ "auto_runner"    ]
    elif self.virtualPinMap_[pin]["name"] == "active_data" :
      self.pins_[ "active_data"    ]
    
  def edit_handler( self, pin ) :
    print( "In edit handler via pin " + str( pin ) + " called " + self.virtualPinMap_[ pin ][ "name" ] )

    if self.virtualPinMap_[pin]["name"] == "edit_terminal" :
      self.pins_[ "edit_terminal" ]
    elif self.virtualPinMap_[pin]["name"] == "edit_profile" :
      self.pins_[ "edit_profile"          ]
    elif self.virtualPinMap_[pin]["name"] == "edit_resolution" :
      self.pins_[ "edit_resolution"       ]
    elif self.virtualPinMap_[pin]["name"] == "edit_hardware_preview" :
      self.pins_[ "edit_hardware_preview" ]
    elif self.virtualPinMap_[pin]["name"] == "edit_profile_preview" :
      self.pins_[ "edit_profile_preview"  ]
    elif self.virtualPinMap_[pin]["name"] == "edit_zaxis_text" :
      self.pins_[ "edit_zaxis_text"  ]
    elif self.virtualPinMap_[pin]["name"] == "edit_fan_text" :
      self.pins_[ "edit_fan_text"    ]
    elif self.virtualPinMap_[pin]["name"] == "edit_uvled_text" :
      self.pins_[ "edit_uvled_text"  ]
    elif self.virtualPinMap_[pin]["name"] == "edit_time_text" :
      self.pins_[ "edit_time_text"   ]
    elif self.virtualPinMap_[pin]["name"] == "edit_data" :
      self.pins_[ "edit_data"    ]
    elif self.virtualPinMap_[pin]["name"] == "edit_value" :
      self.pins_[ "edit_value"   ]
    elif self.virtualPinMap_[pin]["name"] == "edit_time " :
      self.pins_[ "edit_time "   ]
    elif self.virtualPinMap_[pin]["name"] == "edit_run_preview" :
      self.pins_[ "edit_run_preview"  ]
    elif self.virtualPinMap_[pin]["name"] == "edit_point" :
      self.pins_[ "edit_point"    ]
    elif self.virtualPinMap_[pin]["name"] == "edit_add" :
      self.pins_[ "edit_add"      ]
    elif self.virtualPinMap_[pin]["name"] == "edit_delete_point" :
      self.pins_[ "edit_delete_point" ]
    elif self.virtualPinMap_[pin]["name"] == "edit_save" :
      self.pins_[ "edit_save"     ]
    elif self.virtualPinMap_[pin]["name"] == "edit_zaxis_disabled" :
      self.pins_[ "edit_zaxis_disabled"   ]
    elif self.virtualPinMap_[pin]["name"] == "edit_fan_disabled" :
      self.pins_[ "edit_fan_disabled"     ]
    elif self.virtualPinMap_[pin]["name"] == "edit_uvled_disabled" :
      self.pins_[ "edit_uvled_disabled"   ]
    elif self.virtualPinMap_[pin]["name"] == "edit_profile_name" :
      self.pins_[ "edit_profile_name" ]
    elif self.virtualPinMap_[pin]["name"] == "edit_filename" :
      self.pins_[ "edit_filename"     ]
    elif self.virtualPinMap_[pin]["name"] == "edit_duplicate" :
      self.pins_[ "edit_duplicate"      ]
    elif self.virtualPinMap_[pin]["name"] == "edit_new_profile" :
      self.pins_[ "edit_new_profile"    ]
    elif self.virtualPinMap_[pin]["name"] == "edit_delete_profile" :
      self.pins_[ "edit_delete_profile" ]

  def settings_handler( self, pin ) :
    print( "In settings handler via pin " + str( pin ) + " called " + self.virtualPinMap_[ pin ][ "name" ] )

    if self.virtualPinMap_[pin]["name"] == "settings_terminal" :
      self.pins_[ "settings_terminal" ]
    elif self.virtualPinMap_[pin]["name"] == "poweroff" :
      self.pins_[ "poweroff" ]
    elif self.virtualPinMap_[pin]["name"] == "cpu_usage" :
      self.pins_[ "cpu_usage"       ]
    elif self.virtualPinMap_[pin]["name"] == "cpu_temperature" :
      self.pins_[ "cpu_temperature" ]
    elif self.virtualPinMap_[pin]["name"] == "settings_global_zaxis_disabled" :
      self.pins_[ "settings_global_zaxis_disabled" ]
    elif self.virtualPinMap_[pin]["name"] == "settings_global_fan_disabled" :
      self.pins_[ "settings_global_fan_disabled"   ]
    elif self.virtualPinMap_[pin]["name"] == "settings_global_uvled_disabled" :
      self.pins_[ "settings_global_uvled_disabled" ]
    elif self.virtualPinMap_[pin]["name"] == "settings_manual_half_notify_disabled" :
      self.pins_[ "settings_manual_half_notify_disabled" ]
    elif self.virtualPinMap_[pin]["name"] == "settings_manual_full_notify_disabled" :
      self.pins_[ "settings_manual_full_notify_disabled" ]
    elif self.virtualPinMap_[pin]["name"] == "settings_auto_half_notify_disabled" :
      self.pins_[ "settings_auto_half_notify_disabled" ]
    elif self.virtualPinMap_[pin]["name"] == "settings_auto_full_notify_disabled" :
      self.pins_[ "settings_auto_full_notify_disabled" ]
      
  def communicate( self ) :
    while self.com_ :
      self.blynk_.run()

      if self.renderer_ is not None :
        if self.renderer_.runningTimer_ :
          currentData   = self.renderer_.model_.getCurrentData( )
        
          for name, value in currentData.items() :      
            if name == "zaxis" :
              self.blynk_.virtual_write( 0, value )
            elif name == "fan" :
              self.blynk_.virtual_write( 1, value )
            elif name == "lights" :
              self.blynk_.virtual_write( 2, value )
      
  def run( self ) :
    self.blynkthread_.start()
    print( "Waiting for server to start..." )       

  def stop( self ) :
    self.blynk_.notify( "BAWCS Offline" )
    self.blynkthread_.stop()

  def connect_handler( self ):
    self.blynk_.internal("rtc", "sync")
    self.blynk_.notify( "BAWCS Online" )
    msg  = "\n\n\nHello World!\n"
    msg += "Welcome to BAWCS\n"
    msg += "Your one-stop-shop\n"
    msg += "for :\n"
    msg += "Better\n"
    msg += "Automated\n"
    msg += "Washing and\n"
    msg += "Curing\n"
    msg += "Station\n\n"
    msg += "- Anthony Islas"
    self.blynk_.virtual_write( self.pins_[ "main_terminal" ][ "vnum" ], msg + "\n" )
    
    print( "RTC sync request was sent" )

  # From https://github.com/blynkkk/lib-python/blob/master/examples/10_rtc_sync.py
  def rtc_handler( self, rtc_data_list ) :
    
    hr_rtc_value = datetime.utcfromtimestamp( int( rtc_data_list[0] ) ).strftime( '%Y-%m-%d %H:%M:%S' )
    print('Raw RTC value from server: {}'.format( rtc_data_list[0] ) )
    print('Human readable RTC value: {}'.format( hr_rtc_value ) )
  

  def pinwrite_handler( self, pin, value ) :
    if pin in self.virtualPinMap_ :
      if ( value != 0 and 0 not in value and '0' not in value ) or not self.pins_[ self.virtualPinMap_[pin]["name"] ][ "ignoreZero" ] :
        print( "You modified " + str( pin ) + " to value " + str( value ) + " which is " + self.virtualPinMap_[pin]["name"] )
        self.pins_[ self.virtualPinMap_[pin]["name"]]["value"] = value
        self.pins_[ self.virtualPinMap_[pin]["name"]]["handler"]( pin )
      else :
        print( "Fallthrough... we ignored " + str( pin ) + " which is " + self.virtualPinMap_[pin]["name"] )
