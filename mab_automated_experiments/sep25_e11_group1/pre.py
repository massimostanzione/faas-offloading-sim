import os
import sys

from mab.contextual.utils import hours_to_secs

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from mab_automated_experiments._api.traces import generate_trace

print("Trace generation, please wait...")
DURATION = hours_to_secs(7)
PERIOD_STD = DURATION
PERIOD_3 = DURATION / 3
DELAY = PERIOD_3 / 2  # mezzaonda di sfasamento
generate_trace("CYC_f1_e1r1", "triangle", 0, 300, PERIOD_3, 5, DURATION)
generate_trace("CYC_f2_e1r1", "sinusoid", 0, 30, PERIOD_3, 5, DURATION)
generate_trace("CYC_f3_e1r1", "shifted-sinusoid", 0, 30, PERIOD_3, 5, DURATION)
generate_trace("CYC_f4_e1r1", "square-wave-inverted", 0, 300, PERIOD_3, 5, DURATION)
generate_trace("CYC_f5_e1r1", "sawtooth-wave", 0, 30, PERIOD_3, 5, DURATION)

DURATION_FULL = hours_to_secs(24)
PERIOD_FULL = DURATION_FULL / 4
PEAK = 400
NOISE = 100
generate_trace("CYC_f1", "triangle", 0, PEAK, PERIOD_FULL, 5, DURATION_FULL)
generate_trace("CYC_f2", "sinusoid", 0, NOISE, PERIOD_FULL, 5, DURATION_FULL)
generate_trace("CYC_f3", "shifted-sinusoid", 0, NOISE, PERIOD_FULL, 5, DURATION_FULL)
generate_trace("CYC_f4", "square-wave", 0, PEAK, PERIOD_FULL, 5, DURATION_FULL)
generate_trace("CYC_f5", "sawtooth-wave", 0, NOISE, PERIOD_FULL, 5, DURATION_FULL)
