import os
import sys

import spec
from spec import generate_temp_spec, write_spec, write_spec_custom

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _api.traces import generate_trace

def hours(secs:float): return secs*60*60
# TODO oss.: le tracce base non sono generate qui
classes = [{'name': 'standard', 'max_resp_time': 0.5, 'utility': 0.01, 'arrival_weight': 0.7},
           {'name': 'critical_1', 'max_resp_time': 0.5, 'utility': 1.0, 'arrival_weight': 0.1},
           {'name': 'critical_2', 'max_resp_time': 0.5, 'utility': 1.0, 'arrival_weight': 0.1, 'deadline_penalty': 0.75,
            'drop_penalty': 0.75},
           {'name': 'batch', 'max_resp_time': 100.0, 'utility': 1.0, 'arrival_weight': 0.1}
           ]
nodes = [
    {'name': 'cloud1', 'region': 'cloud', 'cost': 0.000005, 'policy': 'cloud', 'speedup': 0.5, 'memory': 8000},
    {'name': 'cloud2', 'region': 'cloud', 'cost': 0.000005, 'policy': 'cloud', 'speedup': 0.5, 'memory': 8000},
    {'name': 'cloud3', 'region': 'cloud', 'cost': 0.00001, 'policy': 'cloud', 'speedup': 1.0, 'memory': 16000},
    {'name': 'cloud4', 'region': 'cloud', 'cost': 0.00001, 'policy': 'cloud', 'speedup': 1.0, 'memory': 16000},
    {'name': 'cloud5', 'region': 'cloud', 'cost': 0.00003, 'policy': 'cloud', 'speedup': 1.2, 'memory': 16000},
    {'name': 'cloud6', 'region': 'cloud', 'cost': 0.00005, 'policy': 'cloud', 'speedup': 1.2, 'memory': 24000},
    {'name': 'cloud7', 'region': 'cloud', 'cost': 0.00007, 'policy': 'cloud', 'speedup': 1.4, 'memory': 24000},
    {'name': 'cloud8', 'region': 'cloud', 'cost': 0.0001, 'policy': 'cloud', 'speedup': 1.4, 'memory': 32000},
    {'name': 'lb1', 'region': 'cloud', 'policy': 'random-lb', 'memory': 0}

]

functions = [{'name': 'f1', 'memory': 512, 'duration_mean': 0.4, 'duration_scv': 1.0, 'init_mean': 0.5},
             {'name': 'f2', 'memory': 512, 'duration_mean': 0.2, 'duration_scv': 1.0, 'init_mean': 0.25},
             {'name': 'f3', 'memory': 128, 'duration_mean': 0.3, 'duration_scv': 1.0, 'init_mean': 0.6},
             {'name': 'f4', 'memory': 1024, 'duration_mean': 0.25, 'duration_scv': 1.0, 'init_mean': 0.25},
             {'name': 'f5', 'memory': 256, 'duration_mean': 0.45, 'duration_scv': 1.0, 'init_mean': 0.5}]




files=[
    "sinus-saturation-test500_f4",
    "sinus-saturation-test1000_f4",
    "sinus-saturation-test1500_f4",
    "sinus-saturation-test2000_f4",
    "linear-saturation-test_f4",
    "4sinus-saturation-test50_f4",
    "4sinus-saturation-test100_f4",
    "4sinus-saturation-test250_f4",
    "4sinus-saturation-test500_f4",
    "4sinus-saturation-test1000_f4",
    "4sinus-saturation-test1500_f4",
    "4sinus-saturation-test2000_f4",
    "bell-saturation-test500_f4",
    "bell-saturation-test1000_f4",
    "bell-saturation-test1500_f4",
    "bell-saturation-test2000_f4",
    "bell-saturation-test2500_f4",
    "bell-saturation-test3000_f4",
    "bell-saturation-test3500_f4",
       ]



print("Specfiles/traces generation, please wait...")




funcs=["f"+str(i) for i in range(1,5+1)]

path = os.path.join(os.path.dirname(__file__), "../_specfiles")
if not os.path.exists(path): os.mkdir(path)
for file in files:
    name=os.path.abspath(os.path.join(os.path.dirname(__file__),"../_specfiles/"+file+".yml"))
    # le tre fisse vanno evitate, sono già fatte
    if "specbase" in name: continue
    tracename=file
    tracename=tracename.replace("_f1","")
    tracename=tracename.replace("_f2","")
    tracename=tracename.replace("_f3","")
    tracename=tracename.replace("_f4","")
    tracename=tracename.replace("_f5","")
    tracename=tracename.replace("_x5","")
    tracename=tracename.replace("_full","")
    #tracename=tracename.replace("4","")
    print("->", tracename)
    arrivals_trace=[]
    print(file)
    with open(name, "w+") as f:
        if "_f1" in name and not "_f1_x5" in name:
                # solo f1
                func="f1"
                a = {"node": 'lb1', "function": func, 'trace': '_traces/' + tracename + "_arrivals.iat"}  # os.path.join(SCRIPT_DIR, wl_name+".iat")}]
                arrivals_trace.append(a)
        elif "_f4" in name and not "_f4_x5" in name:
                # solo f1
                func="f4"
                a = {"node": 'lb1', "function": func, 'trace': '_traces/' + tracename + "_arrivals.iat"}  # os.path.join(SCRIPT_DIR, wl_name+".iat")}]
                arrivals_trace.append(a)
        elif "_f1_x5" in name:
            # solo f1, ma ripetuta 5 volte
            for i in range(1,5+1):
                a = {"node": 'lb1', "function": "f1", 'trace': '_traces/' + tracename + "_arrivals.iat"} # os.path.join(SCRIPT_DIR, wl_name+".iat")}]
                arrivals_trace.append(a)

        elif "full" in name:
            # da f1 a f5, con stessa traccia
            for fn in funcs:
                a = {"node": 'lb1', "function": fn, 'trace': '_traces/' + tracename + "_arrivals.iat"} # os.path.join(SCRIPT_DIR, wl_name+".iat")}]
                arrivals_trace.append(a)

        else:
            print("what?", file)
            exit(1)

        spec.write_spec_custom(f, functions, classes, nodes, arrivals_trace)

print("... done.")


print("Trace generation, please wait...")
DURATION=hours(8)
PERIOD_STD=DURATION
PERIOD_4= DURATION/4
DELAY=PERIOD_4/4 # un quarto d'onda di sfasamento
generate_trace("bell-saturation-test500", "bell", 0, 500, hours(2), 5, hours(2))
generate_trace("bell-saturation-test1000", "bell", 0, 1000, hours(2), 5, hours(2))
generate_trace("bell-saturation-test1500", "bell", 0, 1500, hours(2), 5, hours(2))
generate_trace("bell-saturation-test2000", "bell", 0, 2000, hours(2), 5, hours(2))
generate_trace("bell-saturation-test2500", "bell", 0, 2500, hours(2), 5, hours(2))
generate_trace("bell-saturation-test3000", "bell", 0, 3000, hours(2), 5, hours(2))
generate_trace("bell-saturation-test3500", "bell", 0, 3500, hours(2), 5, hours(2))
generate_trace("sinus-saturation-test1000", "sinusoid", 0, 1000, hours(2), 5, hours(2))
generate_trace("sinus-saturation-test1500", "sinusoid", 0, 1500, hours(2), 5, hours(2))
generate_trace("sinus-saturation-test2000", "sinusoid", 0, 2000, hours(2), 5, hours(2))
generate_trace("linear-saturation-test", "linear", 0, 2000, hours(2), 5, hours(2))
generate_trace("4sinus-saturation-test50", "sinusoid", 0, 50, PERIOD_4, 5, DURATION)
generate_trace("4sinus-saturation-test100", "sinusoid", 0, 100, PERIOD_4, 5, DURATION)
generate_trace("4sinus-saturation-test250", "sinusoid", 0, 250, PERIOD_4, 5, DURATION)
generate_trace("4sinus-saturation-test500", "sinusoid", 0, 500, PERIOD_4, 5, DURATION)
generate_trace("4sinus-saturation-test1000", "sinusoid", 0, 1000, PERIOD_4, 5, DURATION)
generate_trace("4sinus-saturation-test1500", "sinusoid", 0, 1500, PERIOD_4, 5, DURATION)
generate_trace("4sinus-saturation-test2000", "sinusoid", 0, 2000, PERIOD_4, 5, DURATION)
generate_trace("sinus_delay0", "sinusoid", 0, 500, PERIOD_4, 5, DURATION, delay=0*DELAY)
generate_trace("sinus_delay1", "sinusoid", 0, 500, PERIOD_4, 5, DURATION, delay=1*DELAY)
generate_trace("sinus_delay2", "sinusoid", 0, 500, PERIOD_4, 5, DURATION, delay=2*DELAY)
generate_trace("sinus_delay3", "sinusoid", 0, 500, PERIOD_4, 5, DURATION, delay=3*DELAY)
generate_trace("sinus_delay4", "sinusoid", 0, 500, PERIOD_4, 5, DURATION, delay=4*DELAY)
generate_trace("sinus_delay5", "sinusoid", 0, 500, PERIOD_4, 5, DURATION, delay=5*DELAY)
