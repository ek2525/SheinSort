# config.py
USERS = {'admin': '$hipbee.lb@S0rting'}
STATUS_FILE = 'status.json'

# instead of a bare 'outputs', do this:
import os
BASE_DIR     = os.path.abspath(os.path.dirname(__file__))
OUTPUTS_DIR  = os.path.join(BASE_DIR, 'outputs')
