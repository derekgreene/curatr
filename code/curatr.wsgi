#!/opt/anaconda3/bin/python
import sys
from pathlib import Path

# Settings - modify these paths as appropriate
dir_curatr = Path("/opt/curatr")

dir_code = dir_curatr / "code"
dir_core = dir_curatr / "core"
dir_log = dir_curatr / "log"

# Update Python path
sys.path.insert(0, str(dir_code))

# Start Curatr
from curatr import app as application
from curatr import configure_server
print("Configuring server using core directory %s ..." % dir_core)
configure_server(dir_core, dir_log)
