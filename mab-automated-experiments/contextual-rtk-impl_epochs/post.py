import os
import sys
from datetime import datetime

from matplotlib import pyplot as plt
from numpy import arange
import numpy as np
from scipy.interpolate import interp1d

from conf import EXPIRATION_TIMEOUT

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _api.datarecords import (extract_datarecords_from_exp_name, extract_result_dict_from_datarecord,
                              extract_timeseries_from_result_single, extract_timeseries_from_result_multiple,
                              filter_datarecords_by_specfiles
                              )
from _internal import consts, utils


# raccogli i dati delle istanze
records=extract_datarecords_from_exp_name("contextual-rtk-impl_epochs")

timestamp = datetime.now().replace(microsecond=0)
graphs_ctr=0
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
        path=os.path.abspath("_traces/"+tracename
                             .replace("_f1", "")
                             .replace("_f2", "")
                             .replace("_f3", "")
                             .replace("_f4", "")
                             .replace("_f5", "")
                             .replace("_x5", "")
                             .replace("_full", "")
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
    mem = extract_result_dict_from_datarecord(r, "avgActiveMemoryUtilization_sys")
    instances = extract_result_dict_from_datarecord(r, "instance_invoked")
    time = extract_result_dict_from_datarecord(r, "time")
    policies = extract_result_dict_from_datarecord(r, "policy")
    rewards = extract_result_dict_from_datarecord(r, "reward")
    ctx_epochstart_series = extract_result_dict_from_datarecord(r, "epochStartTimes_ctx")

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
    print("x", len(valori), len(labels))
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

    fig, (ax1, ax_destro) = plt.subplots(1, 2, figsize=(12, 6))

    ax1.set_title("Utilizzo memoria e policy scelte")
    
    ax1.hlines(y=0.333, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1, label="limiti istanze")#, label=f"$VC_{{max}}={3}$")
    ax1.hlines(y=0.666, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1)#, label=f"$VC_{{max}}={6}$")
    ax1.hlines(y=1, xmin=xmin, xmax=xmax, color='r', linestyle='-', linewidth=1)#, label=f"$VC_{{max}}={1}$")

    color = 'tab:red'
    ax1.set_xlabel('Tempo [s]')
    ax1.set_ylabel('avgMemoryUtilization', color=color)
    ax1.set_ylim([0,1])
    # Plotta i dati per ciascuna label
    for label, data in dati_per_label.items():
        ax1.scatter(data["x"], data["y"], marker='x', c=data["c"])#, label=f'croci: INIT')
        ax1.scatter(data["o_x"], data["o_y"], marker='o', c=data["o_c"])#, label=f'pallini: post-init')
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
        ax2.tick_params(axis='y', labelcolor=color)

        # Plotta la stessa serie resampled anche nel grafico di destra (ax_destro)
        ax_destro.plot(tempi_destinazione, dati_n2_resampled, color=color, drawstyle='steps-post', linestyle='--', linewidth=0.7)
        ax_destro.tick_params(axis='y', labelcolor=color)


    # --- Inizia a popolare il secondo grafico (ax_destro) ---

    # --- Inizia ad aggiungere le linee verticali al secondo grafico (ax_destro) ---
    # Assicurati che questo blocco sia presente per le linee grigie!
    label_precedente = None
    for i in range(len(instances)):
        label_corrente = instances[i]
        if i > 0 and label_corrente != label_precedente:
            # Queste sono le linee verticali grigie originali
            ax1.axvline(x=time[i], color='gray', linestyle='--', linewidth=0.7)#, label="cambio istanza")
            ax_destro.axvline(x=time[i], color='gray', linestyle='--', linewidth=0.7)
        label_precedente = label_corrente

    linee_verticali_config = []
    for item in ctx_epochstart_series:
        for key, time_value in item.items():
            parts = key.split('-')
            try:
                ymin_str = parts[-2]
                ymax_str = parts[-1]
                ymin_val = float(ymin_str)
                ymax_val = float(ymax_str)
                linee_verticali_config.append({"time": time_value, "ymin": ymin_val, "ymax": ymax_val})
            except (IndexError, ValueError) as e:
                print(
                    f"Errore durante l'estrazione di ymin/ymax dalla chiave '{key}': {e}. Salto questa configurazione.")
                continue

    for line_data in linee_verticali_config:
        t = line_data["time"]
        ymin_val = line_data["ymin"]
        ymax_val = line_data["ymax"]

        # RIMOSSO: transform=ax1.get_yaxis_transform()
        ax1.axvline(x=t, ymin=ymin_val, ymax=ymax_val, color='orange', linestyle='--', linewidth=1.5)
        ax_destro.axvline(x=t, ymin=ymin_val, ymax=ymax_val, color='orange', linestyle='--', linewidth=1.5)

    if linee_verticali_config:
        ax1.plot([], [], color='orange', linestyle='--', linewidth=1.5, label='Inizio epoca')
        ax1.legend()
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
                                                                            '-') + ".svg"))
    fig.clf()

# - plotta traccia
# - plotta utilizzazione
# - plotta contesti (???)
    """ grafici drops
    filtered_records = filter_datarecords_by_specfiles(records)
    # per ogni specfile
    for specfile in list(filtered_records.keys()):
        curr_specfile = specfile
        print("> plotting for", specfile)
        # exp_timeout=[0, 5, 10, 15, 25, 50, 100, 150, 250, 500, 1000, 1500, 2500, 3750, 5000]
        series_avgMemUtil = {}
        series_avgMemUtilUO = {}
        series_warmContainers = {}
        series_availMem = {}
        series_coldStartProb = {}
        series_drops = {}
        series_srate = {}

        # per ogni EXPIRATION_FACTOR (ogni record è un expfact, gli altri parametri sono fissi) (del relativo specfile)
        for r in filtered_records[specfile]:
            # DOCS: datarecord > dict > result
            # PER CIASCUN PARAMETRO EXPIRATION_FACTOR:
            # estrai i risultati
            time = extract_result_dict_from_datarecord(r, "time")
            et = r.identifiers[EXPIRATION_TIMEOUT]
            #mem = extract_result_dict_from_datarecord(r, "avgMemoryUtilization_sys")
            memUO = extract_result_dict_from_datarecord(r, "avgActiveMemoryUtilization_sys")
            #warm_ctr = extract_result_dict_from_datarecord(r, "warm_ctr")
            #avMem = extract_result_dict_from_datarecord(r, "availableMemory_sys")
            #coldStartProb = extract_result_dict_from_datarecord(r, "coldStartProb")
            drops = extract_result_dict_from_datarecord(r, "drops_sys")
            #srate = extract_result_dict_from_datarecord(r, "sampledRate")

            # dai risultati ricava le serie temporali
            #series_avgMemUtil[et] = extract_timeseries_from_result_single(mem)
            series_avgMemUtilUO[et] = extract_timeseries_from_result_single(memUO)
            #series_warmContainers[et] = (extract_timeseries_from_result_multiple(warm_ctr))
            #series_availMem[et] = extract_timeseries_from_result_single(avMem)
            #series_coldStartProb[et] = extract_timeseries_from_result_multiple(coldStartProb)
            series_drops[et] = extract_timeseries_from_result_single(drops)
            #series_srate[et] = extract_timeseries_from_result_single(srate)

        # sbroglia e somma la serie sui container warm
        # qui ho {exp_timeout:{"cloud1":[lista], "cloud2":[lista], ...}}
        r = records[0]
        time = extract_result_dict_from_datarecord(r, "time")

        refined = {k: [0] * len(time) for k, _ in series_warmContainers.items()}
        for EF, ef_dict_cloud_series in series_warmContainers.items():
            # itero sui dizionari per parametro expiration_timeout k
            # qui ho k= exp_timeout, v={"cloud1":[lista], "cloud2":[lista], ...}
            for cloud_label, timeseries_list in ef_dict_cloud_series.items():
                # itero su ciascuna macchina rispetto al parametro expiration_timeout k
                # qui ho k1="cloud1", v1=[lista]
                for i in range(len(timeseries_list)):
                    refined[EF][i] += timeseries_list[i]

        refined_CS = {k: [0] * len(time) for k, _ in series_coldStartProb.items()}
        for EF, ef_dict_cloud_series in series_coldStartProb.items():
            # itero sui dizionari per parametro expiration_timeout k
            # qui ho k= exp_timeout, v={"cloud1":[lista], "cloud2":[lista], ...}
            for cloud_label, timeseries_list in ef_dict_cloud_series.items():
                # itero su ciascuna macchina rispetto al parametro expiration_timeout k
                # qui ho k1="cloud1", v1=[lista]
                for i in range(len(timeseries_list)):
                    refined_CS[EF][i] += timeseries_list[i]
            refined_CS[EF] = [k / 8 for k in refined_CS[EF]]

        from issue12_plots_copia import graph_drops
        graph_drops(series_drops, time, curr_specfile)
        graphs_ctr += 1
    """