#!/home/jlopez/virtualenv/bin/python
# EASY-INSTALL-ENTRY-SCRIPT: 'pyramid==1.4.5','console_scripts','pserve'
__requires__ = 'pyramid==1.4.5'
import sys
from pkg_resources import load_entry_point

sys.exit(
   load_entry_point('pyramid==1.4.5', 'console_scripts', 'pserve')()
)
