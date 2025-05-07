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




files=["specbase", "specbase*0.05", "specbase*30", 
       "linear_f1", "linear_f1_x5", "linear_full", 
       "sinus_f1", "sinus_f1_x5", "sinus_full", 
       "4sinus_f1", "4sinus_f1_x5", "4sinus_full",
       "halfbell_f1", "halfbell_f1_x5", "halfbell_full",
       "bell_f1", "bell_f1_x5", "bell_full",
       "square_f1", "square_f1_x5", "square_full",
       "square_inv_f1", "square_inv_f1_x5", "square_inv_full",
       "sawtooth_f1", "sawtooth_f1_x5", "sawtooth_full",
       "4square_f1", "4square_f1_x5", "4square_full",
       "4square_inv_f1", "4square_inv_f1_x5", "4square_inv_full",
       "4sawtooth_f1", "4sawtooth_f1_x5", "4sawtooth_full",
       "gauss_f1", "gauss_f1_x5", "gauss_full",
       "4gauss_f1", "4gauss_f1_x5", "4gauss_full",
       "debs-scaled_f1", "debs-scaled_f1_x5", "debs-scaled_full"]



print("Specfiles/traces generation, please wait...")




funcs=["f"+str(i) for i in range(1,5+1)]

path = os.path.join(os.path.dirname(__file__), "../_specfiles")
if not os.path.exists(path): os.mkdir(path)
for file in files:
    name=os.path.abspath(os.path.join(os.path.dirname(__file__),"../_specfiles/"+file+".yml"))
    # le tre fisse vanno evitate, sono già fatte
    if "specbase" in name: continue
    tracename=file.replace("_f1","")
    tracename=tracename.replace("_x5","")
    tracename=tracename.replace("_full","")
    tracename=tracename.replace("4","")
    print("->", tracename)
    arrivals_trace=[]
    print(file)
    with open(name, "w+") as f:
        if "_f1" in name and not "_f1_x5" in name:
                # solo f1
                func="f1"
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
PERIOD_4= hours(4) / 2

generate_trace("linear", "linear", 1, 350, PERIOD_STD, 5, DURATION)

generate_trace("sinus", "sinusoid", 1, 350, PERIOD_STD, 5, DURATION)
generate_trace("bell", "bell", 1, 350, PERIOD_STD, 5, DURATION)
generate_trace("halfbell", "halfbell", 1, 350, PERIOD_STD, 5, DURATION)

generate_trace("square", "square-wave", 1, 350, PERIOD_STD, 5, DURATION)
generate_trace("square_inv", "square-wave-inverted", 1, 350, PERIOD_STD, 5, DURATION)
generate_trace("sawtooth", "sawtooth-wave", 1, 350, PERIOD_STD, 5, DURATION)
generate_trace("gauss", "gaussian-modulated", 1, 350, PERIOD_STD, 5, DURATION)

generate_trace("4sinus", "sinusoid", 1, 350, PERIOD_4, 5, DURATION)
generate_trace("4square", "square-wave", 1, 350, PERIOD_4, 5, DURATION)
generate_trace("4square_inv", "square-wave-inverted", 1, 350, PERIOD_4, 5, DURATION)
generate_trace("4sawtooth", "sawtooth-wave", 1, 350, PERIOD_4, 5, DURATION)


generate_trace("step1", "step", 1, 116, 0, 5, DURATION)
generate_trace("step2", "step", 1, 232, 4800, 5, DURATION)
generate_trace("step3", "step", 1, 350, 9200, 5, DURATION)


# riadatta debs
name_in = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/debs.iat"))
name_out = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/debs-scaled_arrivals.iat"))
sum=0
with open(name_in, "r") as debs_input:
    with open(name_out, "w") as debs_output:
        for i in debs_input:
            out=int(i)/10000
            sum+=out
            debs_output.write(str(out)+"\n")
print("debs time sums to", sum, "that is",sum/(60*60),"hours.")
print("... done.")
