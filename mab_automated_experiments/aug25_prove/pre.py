import os
import sys

import spec

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from mab_automated_experiments._api.traces import generate_trace

def hours(secs:float): return secs*60*60
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
    #"linear-debug-complete-spectrum",
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
DURATION=hours(4)
PERIOD_STD=DURATION
PERIOD_4= DURATION/4
DELAY=PERIOD_4/4 # un quarto d'onda di sfasamento
generate_trace("const50", "linear", 50, 50, DURATION, 5, DURATION)
generate_trace("const200", "linear", 200, 200, DURATION, 5, DURATION)
generate_trace("const500", "linear", 500, 500, DURATION, 5, DURATION)
generate_trace("const1000", "linear", 1000, 1000, DURATION, 5, DURATION)
generate_trace("const1500", "linear", 1500, 1500, DURATION, 5, DURATION)
generate_trace("const2000", "linear", 2000, 2000, DURATION, 5, DURATION)
generate_trace("step_delay0", "linear", 0, 500, DURATION, 5, DURATION, delay=0*DELAY)
generate_trace("step_delay1", "linear", 0, 1000, DURATION, 5, DURATION, delay=1*DELAY)
generate_trace("step_delay2", "linear", 0, 2000, DURATION, 5, DURATION, delay=2*DELAY)

SATURATION_LIMIT=1000#10000/3
SATURATION_MULTIFUNCTION=250
DURATION_REDUCED=DURATION #/2
PERIOD_4_REDUCED=PERIOD_4 #DURATION_REDUCED/2
DELAY_REDUCED=DELAY #PERIOD_4/4 # un quarto d'onda di sfasamento
generate_trace("linear-debug-fullspectrum", "linear", 0, SATURATION_LIMIT, DURATION_REDUCED, 5, DURATION_REDUCED)
generate_trace("bell-debug-fullspectrum", "bell", 0, SATURATION_LIMIT, PERIOD_4_REDUCED, 5, DURATION_REDUCED)
generate_trace("sinus-debug-fullspectrum", "sinusoid", 0, SATURATION_LIMIT, DURATION_REDUCED, 5, DURATION_REDUCED)
generate_trace("4sinus-debug-fullspectrum", "sinusoid", 0, SATURATION_LIMIT, PERIOD_4_REDUCED, 5, DURATION_REDUCED)

generate_trace("sinus_delay0-fullspectrum", "sinusoid", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=0*DELAY_REDUCED)
generate_trace("sinus_delay1-fullspectrum", "sinusoid", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=1*DELAY_REDUCED)
generate_trace("sinus_delay2-fullspectrum", "sinusoid", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=2*DELAY_REDUCED)
generate_trace("sinus_delay3-fullspectrum", "sinusoid", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=3*DELAY_REDUCED)
generate_trace("sinus_delay4-fullspectrum", "sinusoid", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=4*DELAY_REDUCED)
generate_trace("sinus_delay5-fullspectrum", "sinusoid", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=5*DELAY_REDUCED)
generate_trace("bell_delay0-fullspectrum", "bell", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=0*DELAY_REDUCED)
generate_trace("bell_delay1-fullspectrum", "bell", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=1*DELAY_REDUCED)
generate_trace("bell_delay2-fullspectrum", "bell", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=2*DELAY_REDUCED)
generate_trace("bell_delay3-fullspectrum", "bell", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=3*DELAY_REDUCED)
generate_trace("bell_delay4-fullspectrum", "bell", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=4*DELAY_REDUCED)
generate_trace("bell_delay5-fullspectrum", "bell", 0, SATURATION_MULTIFUNCTION, PERIOD_4_REDUCED, 5, DURATION_REDUCED, delay=5*DELAY_REDUCED)