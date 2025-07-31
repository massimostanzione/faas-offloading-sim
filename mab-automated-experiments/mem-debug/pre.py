import os
import sys

import spec
from spec import generate_temp_spec, write_spec, write_spec_custom

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _api.traces import generate_trace

def hours(secs:float): return secs*60*60

print("Specfiles/traces generation, please wait...")




funcs=["f"+str(i) for i in range(1,5+1)]

path = os.path.join(os.path.dirname(__file__), "../_specfiles")
if not os.path.exists(path): os.mkdir(path)



print("Trace generation, please wait...")
DURATION=hours(4)
DURATION_SAT=60*30
PERIOD_STD=DURATION
PERIOD_4= DURATION/4
PERIOD_2= DURATION/2
DELAY=PERIOD_4/4 # un quarto d'onda di sfasamento
generate_trace("linear-debug", "linear", 0, 500, DURATION, 5, DURATION)
generate_trace("bell-debug", "bell", 0, 500, PERIOD_4, 5, DURATION)
generate_trace("const50", "linear", 50, 50, DURATION, 5, DURATION)
generate_trace("const200", "linear", 200, 200, DURATION, 5, DURATION)
generate_trace("const500", "linear", 500, 500, DURATION, 5, DURATION)
generate_trace("const1000", "linear", 1000, 1000, DURATION, 5, DURATION)
generate_trace("const1500", "linear", 1500, 1500, DURATION, 5, DURATION)
generate_trace("const2000", "linear", 2000, 2000, DURATION, 5, DURATION)
generate_trace("actmem-saturation", "linear", 10000, 10000, DURATION, 5, DURATION)
generate_trace("2square-debug", "square-wave", 0, 500, PERIOD_2, 5, DURATION)
generate_trace("2square_inv-debug", "square-wave-inverted", 0, 500, PERIOD_2, 5, DURATION)
generate_trace("2sawtooth-debug", "sawtooth-wave", 0, 500, PERIOD_2, 5, DURATION)
generate_trace("gauss-debug", "gaussian-modulated", 0, 500, DURATION, 5, DURATION)
generate_trace("sinus-debug", "sinusoid", 0, 500, DURATION, 5, DURATION)
generate_trace("4sinus-debug", "sinusoid", 0, 500, PERIOD_4, 5, DURATION)