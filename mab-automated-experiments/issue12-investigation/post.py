import os
import sys
from datetime import datetime

from matplotlib import pyplot as plt
from numpy import arange
import numpy as np
from scipy.interpolate import interp1d

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _api.datarecords import extract_datarecords_from_exp_name, extract_result_dict_from_datarecord
from _internal import consts, utils


# raccogli i dati delle istanze
records=extract_datarecords_from_exp_name("issue12-investigation")

timestamp = datetime.now().replace(microsecond=0)
graphs_ctr=0
# TODO ma i times servono? anche come salvati, per forza?
# per ogni istanza fai roba:
trace_iat=[]
tempi_transizioni=[]
valori_plot=[]
mem=[]
instances=[]
for r in records:
    trace_iat=[]
    tempi_transizioni=[]
    valori_plot=[]
    mem=[]
    instances=[]
    path=""
    print("RECORD", r.identifiers["axis_post"])
    tracename=r.identifiers["specfile"]
    if "specbase" in tracename:
        tempi_transizioni=[0,0,0]
        valori_plot=[0,0,0]
    else:
        print("UUUUUUUUUUU")
        path=os.path.abspath("_traces/"+tracename.replace("_f1", "").replace("_x5", "").replace("_full", "")
+"_rates.iat")
        print(path)
        if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        tempi_transizioni.append(float(line))
        """path=os.path.abspath("_traces/"+tracename+"_rates.iat")
             if os.path.exists(path):
            with open(path) as file:
                line_old=0
                for line in file:
                    if line!="Rate\n":
                        print(line)
                        valori_plot.append(float(line))
        """
    mem = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys")
    mem_cloud={"cloud"+str(i):[] for i in range(1,9)}
    for data in extract_result_dict_from_datarecord(r, "avgMemoryUtilization"):
        for i in range(1,9):
            mem_cloud["cloud"+str(i)].append( data["cloud"+str(i)])
    #print(mem_cloud)
    rates = extract_result_dict_from_datarecord(r, "sampledRate")
    warmctr = extract_result_dict_from_datarecord(r, "warm_ctr")
    #instances = extract_result_dict_from_datarecord(r, "instance_invoked")
    time = extract_result_dict_from_datarecord(r, "time")
    #policies = extract_result_dict_from_datarecord(r, "policy")
    #rewards = extract_result_dict_from_datarecord(r, "reward")

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

    policy_colors = utils.get_policy_colors()

    # Itera attraverso i dati e assegna i valori alle liste corrette
    for i, label in enumerate(labels):
        policy = "none"#policies[i]
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

    fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))

    ax1.set_title("Utilizzo memoria e policy scelte")
    
    ax1.hlines(y=0.333, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={3}$")
    ax1.hlines(y=0.666, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={6}$")
    ax1.hlines(y=1, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label=f"$VC_{{max}}={1}$")

    color = 'tab:red'
    ax1.set_xlabel('Tempo [s]')
    ax1.set_ylabel('avgMemoryUtilization_sys', color=color)
    ax1.set_ylim([0,1])
    # Plotta i dati per ciascuna label
    #for label, data in dati_per_label.items():
    #    ax1.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
    #    ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')
    ax1.scatter(time, mem)
    #ax1.plot(t, data1, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second Axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)  # we already handled the x-label with ax1
    
    
    tempi_n1 = np.array(time)
    tempi_destinazione=[]
    dati_n2_resampled=[]

    if os.path.exists(path):


        # Converti la lista 'time' in un array NumPy
        # --- Resampling della seconda serie dati ---
        # 1. Crea un array di "tempi" impliciti per la seconda serie dati
        tempi_n2_impliciti = np.linspace(tempi_n1.min(), tempi_n1.max(), len(tempi_transizioni)) # Stesso intervallo di tempi_n1, ma lunghezza di tempi_transizioni

        # 2. Crea l'asse dei tempi di destinazione (basato su time)
        tempi_destinazione = np.linspace(tempi_n1.min(), tempi_n1.max(), len(tempi_n1))

        # 3. Crea una funzione di interpolazione basata sui "tempi" impliciti e i valori della seconda serie
        funzione_interpolazione = interp1d(tempi_n2_impliciti, tempi_transizioni, kind='linear', fill_value="extrapolate")

        # 4. Usa la funzione di interpolazione per ottenere i nuovi valori della seconda serie ai tempi della prima
        dati_n2_resampled = funzione_interpolazione(tempi_destinazione)

        ax2.plot(tempi_destinazione, dati_n2_resampled, color=color, drawstyle='steps-post', linestyle='--', linewidth=0.7)
        ax2.scatter(time, rates, color="lightgray")#, color=color, drawstyle='steps-post', linestyle='--', linewidth=0.7)
        ax2.tick_params(axis='y', labelcolor=color)
    """
        # Plotta la stessa serie resampled anche nel grafico di destra (ax_destro)
        ax_destro.plot(tempi_destinazione, dati_n2_resampled, color=color, drawstyle='steps-post', linestyle='--', linewidth=0.7)
        ax_destro.tick_params(axis='y', labelcolor=color)


    # --- Inizia a popolare il secondo grafico (ax_destro) ---

    # --- Inizia ad aggiungere le linee verticali al secondo grafico (ax_destro) ---
    label_precedente = None
    for i in range(len(instances)):
        label_corrente = instances[i]
        if i > 0 and label_corrente != label_precedente:
            # Aggiungi una linea verticale alla posizione x corrispondente
            ax1.axvline(x=time[i], color='gray', linestyle='--', linewidth=0.7)
            ax_destro.axvline(x=time[i], color='gray', linestyle='--', linewidth=0.7)
        label_precedente = label_corrente
    #ax1.legend()
    # --- Fine dell'aggiunta delle linee verticali ---
    
# --- Inizia a popolare il secondo grafico (ax_destro) ---

    # Primo plot nel grafico di destra (con il suo asse y)
    ax_destro.plot(time, rewards, marker='o', linestyle='-', color='green', label='Reward')
    ax_destro.set_xlabel('Tempo [s]')
    ax_destro.set_ylabel('Reward (puntuale)', color='green')
    ax_destro.tick_params(axis='y', labelcolor='green')
    ax_destro.set_title('Reward (puntuale)')

    # Imposta i limiti dell'asse y per le rewards
    min_rewards = np.min(rewards)
    max_rewards = np.max(rewards)
    ax_destro.set_ylim(min_rewards, max_rewards)

    if os.path.exists(path):
        # Crea un secondo asse y indipendente che condivide l'asse x con ax_destro
        ax_destro_y2 = ax_destro.twinx()
        color = 'tab:blue'
        ax_destro_y2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)
        ax_destro_y2.plot(tempi_destinazione, dati_n2_resampled, color=color, drawstyle='steps-post', linestyle='--', linewidth=0.7, label='Traccia')
        ax_destro_y2.tick_params(axis='y', labelcolor=color)

        # Imposta i limiti dell'asse y per i dati resampled
        min_y2 = np.min(dati_n2_resampled)
        max_y2 = np.max(dati_n2_resampled)
        ax_destro_y2.set_ylim(min_y2, max_y2)

       # --- Fine del codice per il secondo grafico ---
    """
    #fig.tight_layout()
    plt.suptitle(r.identifiers["strategy"]+" ("+r.identifiers["axis_pre"]+") "+", "+r.identifiers["specfile"])

    #plt.legend()
    plt.tight_layout()
    fig.tight_layout()
    #plt.show()

    #fig.title(r.identifiers["axis_pre"]+" "+r.identifiers["strategy"]+" "+r.identifiers["specfile"]+" "+tracename)


    graphs_ctr += 1
    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + "a.svg"))
    fig.clf()
























    fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))

    ax1.set_title("Utilizzo memoria")

    color = 'tab:red'
    ax1.set_xlabel('Tempo [s]')
    ax1.set_ylabel('avgMemoryUtilization_sys', color=color)
    ax1.set_ylim([0, 1])
    # Plotta i dati per ciascuna label
    # for label, data in dati_per_label.items():
    #    ax1.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
    #    ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')
    for i in range(1,9):
        ax1.scatter(time, mem_cloud["cloud"+str(i)])
    #ax1.scatter(time, mem)
    # ax1.plot(t, data1, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second Axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)  # we already handled the x-label with ax1






    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + "b.svg"))
    fig.clf()











    fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))

    ax1.set_title("warm containers totali")

    color = 'tab:red'
    ax1.set_xlabel('Tempo [s]')
    ax1.set_ylabel('avgMemoryUtilization_sys', color=color)
    #ax1.set_ylim([0, 1])
    # Plotta i dati per ciascuna label
    # for label, data in dati_per_label.items():
    #    ax1.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
    #    ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')

    output={k:[] for k in warmctr[0].keys()}
    for dict in warmctr:
        for k, v in dict.items():
            output[k].append(v)
    for k in warmctr[0].keys():
        ax1.plot(time, output[k])

    #ax1.scatter(time, mem)
    # ax1.plot(t, data1, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second Axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)  # we already handled the x-label with ax1







    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + "c.svg"))
    fig.clf()






















    avMem = extract_result_dict_from_datarecord(r, "availableMemory")

    fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))

    ax1.set_title("available memory")

    color = 'tab:red'
    ax1.set_xlabel('Tempo [s]')
    ax1.set_ylabel('avgMemoryUtilization', color=color)
    # Plotta i dati per ciascuna label
    # for label, data in dati_per_label.items():
    #    ax1.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
    #    ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')
    #for i in range(1,9):
    #ax1.scatter(time, avMem)
    #ax1.scatter(time, mem)

    output={k:[] for k in avMem[0].keys()}
    for dict in avMem:
        for k, v in dict.items():
            output[k].append(v)
    for k in avMem[0].keys():
        ax1.plot(time, output[k])

    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second Axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)  # we already handled the x-label with ax1






    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + "d.svg"))
    fig.clf()













    avMemsys = extract_result_dict_from_datarecord(r, "availableMemory_sys")

    fig, ax1 = plt.subplots(1, 1, figsize=(12, 6))

    ax1.set_title("available memory")

    color = 'tab:red'
    ax1.set_xlabel('Tempo [s]')
    ax1.set_ylabel('avgMemoryUtilization_sys', color=color)
    # Plotta i dati per ciascuna label
    # for label, data in dati_per_label.items():
    #    ax1.scatter(data["x"], data["y"], marker='x', c=data["c"], label=f'{label} (primi 7)')
    #    ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"], label=f'{label} (successivi)')
    #for i in range(1,9):
    #ax1.scatter(time, avMem)
    #ax1.scatter(time, mem)
    ax1.plot(time, avMemsys)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second Axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel('Frequenza arrivi (traccia) [req/s]', color=color)  # we already handled the x-label with ax1







    fig.savefig(os.path.join(SCRIPT_DIR, "output",
                             consts.DELIMITER_HYPHEN.join(
                                 [str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                            '-') + "e.svg"))
    fig.clf()
