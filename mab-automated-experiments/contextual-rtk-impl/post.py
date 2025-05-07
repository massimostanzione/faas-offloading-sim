import os
import sys
from datetime import datetime

from matplotlib import pyplot as plt
from numpy import arange

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _api.datarecords import extract_datarecords_from_exp_name, extract_result_dict_from_datarecord
from _internal import consts


# raccogli i dati delle istanze
records=extract_datarecords_from_exp_name("contextual-rtk-impl")

timestamp = datetime.now().replace(microsecond=0)
graphs_ctr=1
# per ogni istanza fai roba:
trace_iat=[]
tempi_transizioni=[]
valori_plot=[]
mem=[]
instances=[]
for r in records:
    print("RECORD", r.identifiers["axis_post"])
    tracename=r.identifiers["specfile"]
    if "specbase" in tracename:
        tempi_transizioni=[0,0,0]
        valori_plot=[0,0,0]
    else:
        path=os.path.abspath("_traces/"+tracename+"_rates.iat")
        if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        tempi_transizioni.append(float(line))
        path=os.path.abspath("_traces/"+tracename+"_rates.iat")
        if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        valori_plot.append(float(line))

    mem = extract_result_dict_from_datarecord(r, "avgMemoryUtilization")
    instances = extract_result_dict_from_datarecord(r, "instance_invoked")
    time = extract_result_dict_from_datarecord(r, "time")
    policies = extract_result_dict_from_datarecord(r, "policy")

    # campiona se i punti della traccia sono più dei campioni temporali
    # i.e., quando non è una traccia sintetica stile anastasia
    trace_rates=[]
    trace_ratesa=[] #appoggio fixme
    if len(time)>len(tempi_transizioni):
        # ho più campionamenti che punti traccia
        # aggiungo punti fittizi
        pass
    if len(time)<len(tempi_transizioni):
        step=int(len(tempi_transizioni) / len(time))
        print(len(time), len(tempi_transizioni), step)
        for i in arange(0, len(tempi_transizioni), step):
            #print("step",i,step, trace_rates_raw[i])
            trace_ratesa.append(tempi_transizioni[i])
            trace_rates=trace_ratesa[1:]#fixme
    else:
        trace_rates=tempi_transizioni



#    plt.title(tracename)
    #plt.plot(trace_iat)
#    plt.plot(trace)
#    plt.show()
    #plt.clf()

    #fig, ax = plt.subplots()
    x=mem

    z=mem
    #ax.scatter(range(mem), mem[z < 12], marker='s', color='b', label='z < 12')
    #ax.scatter(x[z >= 12], y[z >= 12], marker='o', facecolors='none', edgecolors='r', label='z >= 12')
    labels=instances
    valori=mem
    # Crea un dizionario per raggruppare i valori per label
    dati_per_label = {}
    for label in set(labels):
        dati_per_label[label] = {"x": [], "y": [], "c": [], "o_x": [], "o_y": [], "o_c": []}

    # presi da quelli di enrico
    policy_colors = {"random-lb": "green", "round-robin-lb": "blue", "mama-lb": "orange", "const-hash-lb": "purple",
                     "wrr-speedup-lb": "lawngreen", "wrr-memory-lb": "dodgerblue", "wrr-cost-lb": "fuchsia"}

    # Itera attraverso i dati e assegna i valori alle liste corrette
    for i, label in enumerate(labels):
        policy = policies[i]
        policy_colore = policy_colors[policy]
        if len(dati_per_label[label]["y"]) < 7:
            dati_per_label[label]["x"].append(time[i])
            dati_per_label[label]["y"].append(valori[i])
            dati_per_label[label]["c"].append(policy_colore)
        else:
            dati_per_label[label]["o_x"].append(time[i])
            dati_per_label[label]["o_y"].append(valori[i])
            dati_per_label[label]["o_c"].append(policy_colore)
    """
    # Plotta i dati per ciascuna label
    for label, data in dati_per_label.items():
        plt.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
        plt.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')

    # Scala la sinusoide tra 0 e 1
    min_sinusoide = min(trace_rates)
    max_sinusoide = max(trace_rates)
    if max_sinusoide==min_sinusoide: max_sinusoide+=1e-10 #fixme accrocco, ma serve es. per gaussiana
    sinusoide_scalata = [(x - min_sinusoide) / (max_sinusoide - min_sinusoide) for x in valori_plot]
    print(tracename, "x=", valori_plot, trace_rates, "y=", sinusoide_scalata)

    #plt.plot(tempi_transizioni, sinusoide_scalata, drawstyle='steps-post')

    """
    xmin=0
    xmax=time[len(time)-1]

    """
    plt.hlines(y=0.333, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={3}$")
    plt.hlines(y=0.666, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={6}$")
    plt.hlines(y=1, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={1}$")

    plt.xlim([xmin, xmax])
    plt.ylim([0,1])

    #plt.show()
    plt.clf()

    """
#############################################################à
    fig, ax1 = plt.subplots()

    plt.hlines(y=0.333, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={3}$")
    plt.hlines(y=0.666, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={6}$")
    plt.hlines(y=1, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={1}$")

    color = 'tab:red'
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('exp', color=color)
    ax1.set_ylim([0,1])
    # Plotta i dati per ciascuna label
    for label, data in dati_per_label.items():
        ax1.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
        ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')
    #ax1.plot(t, data1, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second Axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('sin', color=color)  # we already handled the x-label with ax1
    ax2.plot(valori_plot, color=color, drawstyle='steps-post')
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    #plt.show()

    plt.title(r.identifiers["axis_pre"]+" "+r.identifiers["strategy"]+" "+r.identifiers["specfile"]+" "+tracename)
    #fig.title(r.identifiers["axis_pre"]+" "+r.identifiers["strategy"]+" "+r.identifiers["specfile"]+" "+tracename)



    graphs_ctr += 1
    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + ".svg"))
    fig.clf()




