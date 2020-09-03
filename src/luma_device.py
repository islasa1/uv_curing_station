# Originally from LUMA LCD
import sys
import logging

from luma.core import cmdline, error

# logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)-15s - %(message)s'
)

# ignore PIL debug messages
logging.getLogger('PIL').setLevel( logging.ERROR )

def display_settings( args )
    iface = ''
    display_types = cmdline.get_display_types()
    if args.display not in display_types['emulator']:
        iface = 'Interface: {}\n'.format(args.interface)

    lib_name = cmdline.get_library_for_display_type(args.display)
    if lib_name is not None:
        lib_version = cmdline.get_library_version(lib_name)
    else:
        lib_name = lib_version = 'unknown'

    import luma.core
    version = 'luma.{} {} (luma.core {})'.format(
        lib_name, lib_version, luma.core.__version__)

    return 'Version: {}\nDisplay: {}\n{}Dimensions: {} x {}\n{}'.format(
        version, args.display, iface, args.width, args.height, '-' * 60 )

def get_device( configuration ):
    # load config from file
    config = cmdline.load_config( configuration )
    args = parser.parse_args( config )

    print( display_settings( args ) )

    # create device
    try:
        device = cmdline.create_device(args)
    except error.Error as e:
        parser.error(e)
    return device
