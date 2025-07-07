import csv
import math
import os

import matplotlib.pyplot as plt
import numpy as np

# based on a work by anastasia brinati
"""
  1 Genera un numero di arrivi seguendo una distribuzione data per ogni step temporale indicato:
    in pratica divide il tempo in intervalli e calcola quanti eventi devono arrivare in ogni step.
  2 Distribuisce gli arrivi casualmente all'interno di ogni intervallo temporale.
  3 calcola i tempi inter-arrivo per ottenere una serie temporale realistica.
"""
ampiezza = 100000.0

# o questo...
frequenza = 1 / (60 * 60)  # FREQ
durata = 3 * 60 * 60  # PERIOD

# -----------------------
DISTRIBUTION = None
np.random.seed(123456789)


def _generate_sinusoidal(i, min_rate, max_rate, period, step_len):
    FREQ = 2 / period * 1 * np.pi
    return np.round(min_rate + (max_rate - min_rate) / 2 + ((max_rate - min_rate) / 2) * math.sin(FREQ * step_len * i))


def _generate_bell(i, min_rate, max_rate, period, step_len):
    FREQ = 2 / period * .5 * np.pi
    return np.round(min_rate + (max_rate - min_rate) / 2 + ((max_rate - min_rate) / 2) * math.sin(FREQ * step_len * i))


def _generate_halfbell(i, min_rate, max_rate, period, step_len):
    FREQ = 2 / period * .25 * np.pi
    return np.round(min_rate + (max_rate - min_rate) / 2 + ((max_rate - min_rate) / 2) * math.sin(FREQ * step_len * i))


def _generate_shifted_sinusoidal(i, min_rate, max_rate, period, step_len):
    FREQ = 2 / period * 1 * np.pi
    return np.round(
        min_rate + (max_rate - min_rate) / 2 + (max_rate - min_rate) / 2 * math.sin(FREQ * step_len * i + np.pi))


def _generate_linear(i, min_rate, max_rate, period, step_len, duration):
    STEPS = int(duration / step_len)  # Numero di passi temporali (es. 5400 / 60 = 90)
    return np.round(min_rate + (max_rate - min_rate) * (i / STEPS))


def _generate_square_wave(i, min_rate, max_rate, period, step_len):
    return max_rate if 2 * (i * step_len) % (2 * period) < period else min_rate


def _generate_square_wave_inverted(i, min_rate, max_rate, period, step_len):
    return min_rate if 2 * (i * step_len) % (2 * period) < period else max_rate


def _generate_step(i, min_rate, max_rate, step, step_len):
    return min_rate if (i * step_len) < step else max_rate


def _generate_sawtooth_wave(i, min_rate, max_rate, period, step_len):
    phase = (i * step_len) % period / period
    return np.round(min_rate + (max_rate - min_rate) * phase)


def _generate_logistic_map(i, r=3.8, x0=0.5, min_rate=50, max_rate=600, period=20):
    x = x0
    for _ in range(i):
        x = r * x * (1 - x)
    return np.round(min_rate + (max_rate - min_rate) * x)


def _generate_gaussian_modulated(i, min_rate, max_rate, sigma, step_len, duration, period):
    STEPS = int(duration / step_len)

    # Calculate the effective index within the given period
    # This ensures the Gaussian shape repeats
    effective_i = i % int(period / step_len)

    # Calculate the center of the Gaussian for a single period
    period_steps = int(period / step_len)
    gaussian_center = period_steps / 2

    mod = np.exp(-0.5 * ((effective_i - gaussian_center) / (sigma * period_steps / 2)) ** 2)
    return np.round(min_rate + (max_rate - min_rate) * mod)


def _graph(interarrivals, rates, duration, step_len, distribution, file_path):
    path = os.path.join(os.path.dirname(__file__), "../_traces/img")
    if not os.path.exists(path): os.makedirs(path)
    STEPS = int(duration / step_len)  # Numero di passi temporali (es. 5400 / 60 = 90)

    # Creazione del grafico con due subplot affiancati
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))

    # Grafico degli interarrivi
    axs[0].plot(interarrivals)  # , bins=30, color='blue', alpha=0.7, edgecolor='black')
    axs[0].set_xlabel("Interarrival Time (s)")
    axs[0].set_ylabel("Frequency")
    axs[0].set_title("Interarrival Times")
    axs[0].grid(True)

    # Grafico dei rates
    axs[1].plot(np.arange(STEPS) * step_len, rates, label=f"Arrival Rate (per {step_len}s)", marker="o",
                color="r")  # , drawstyle='steps-post')
    axs[1].set_xlabel("Time (minutes)")
    axs[1].set_ylabel(f"Arrival Rate")
    axs[1].set_title(f"*{distribution}* Arrival Rate Over Time")
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(file_path)


def generate_trace(name: str, distribution: str, min_rate: float, max_rate: float, period: float, step_len: float,
                   duration: float):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/" + name + "_arrivals.iat"))
    if os.path.exists(path):
        print("Trace", name, "already generated, skipping...")
    else:

        STEPS = int(duration / step_len)  # Numero di passi temporali (es. 5400 / 60 = 90)

        nArrivals = np.zeros(STEPS)  # Inizializza un array per gli arrivi in ogni step

        for i in range(STEPS):
            # Genera la quantità di arrivi per ogni step a seconda della distribuzione
            if distribution == "sinusoid":
                nArrivals[i] = _generate_sinusoidal(i, min_rate, max_rate, period, step_len)
            elif distribution == "bell":
                nArrivals[i] = _generate_bell(i, min_rate, max_rate, period, step_len)
            elif distribution == "halfbell":
                nArrivals[i] = _generate_halfbell(i, min_rate, max_rate, period, step_len)
            elif distribution == "shifted-sinusoid":
                nArrivals[i] = _generate_shifted_sinusoidal(i, min_rate, max_rate, period, step_len)
            elif distribution == "linear":
                nArrivals[i] = _generate_linear(i, min_rate, max_rate, period, step_len, duration)
            elif distribution == "square-wave":
                nArrivals[i] = _generate_square_wave(i, min_rate, max_rate, period, step_len)
            elif distribution == "square-wave-inverted":
                nArrivals[i] = _generate_square_wave_inverted(i, min_rate, max_rate, period, step_len)
            elif distribution == "step":
                # period --> step instant
                nArrivals[i] = _generate_step(i, min_rate, max_rate, period, step_len)
            elif distribution == "sawtooth-wave":
                nArrivals[i] = _generate_sawtooth_wave(i, min_rate, max_rate, period, step_len)
            elif distribution == "logistic-map":
                nArrivals[i] = _generate_logistic_map(i)
            elif distribution == "gaussian-modulated":
                sigma = 0.5
                nArrivals[i] = _generate_gaussian_modulated(i, min_rate, max_rate, sigma, step_len, duration, period)
            else:
                print(f"Distribuzione '{distribution}' non supportata!")
                return

        # Otteniamo i rates a partire dall'array di arrivi (qui STEP_LEN=120s)
        print("narr", nArrivals)
        rates = nArrivals / step_len
        print("rates", rates)
        total_arrivals = int(sum(nArrivals))  # Calcola il numero totale di arrivi
        arrival_times = np.zeros(total_arrivals)  # Inizializza gli array dei tempi di arrivo
        count = 0
        rng = np.random.default_rng(123)
        for i in range(STEPS):
            t0 = step_len * i  # Inizio dell'intervallo temporale
            t1 = t0 + step_len  # Fine dell'intervallo temporale
            # Genera arrivi casuali dentro [t0, t1] e li ordina;
            # praticamente genera tempi di arrivo uniformemente distribuiti in ogni step.
            print("> genero", nArrivals[i].astype(int))
            arrival_times[count:count + int(nArrivals[i])] = np.sort(rng.uniform(t0, t1, nArrivals[i].astype(int)))
            count += int(nArrivals[i])
        inter_arrival_times = np.diff(arrival_times)
        print("SUM", np.sum(inter_arrival_times))

        # Genera e salva grafico
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_traces", "img", f"{name}_plot.png"))
        # if not os.path.exists(file_path):
        _graph(inter_arrival_times, rates, duration, step_len, distribution,
               file_path)  # f"../_traces/img/{name}_plot.png")

        print(f"Generated {len(nArrivals)} rates.")

        # Salva interarrivi (simulation trace), seconda metà
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/" + name + "_arrivals.iat"))
        pathfolder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces"))
        if not os.path.exists(pathfolder): os.makedirs(pathfolder)

        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(zip(inter_arrival_times))

        # Salva rates (training data), prima metà
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/" + name + "_rates.iat"))
        # if not os.path.exists(path):
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Rate"])
            writer.writerows(zip(rates))


generate_trace("step", "step", 0, 500, 100, 5, 14400)
DURATION = 14400
generate_trace("step1", "step", 0, 116, 1, 5, DURATION)
generate_trace("step2", "step", 0, 232, 4800, 5, DURATION)
generate_trace("step3", "step", 0, 350, 9200, 5, DURATION)
