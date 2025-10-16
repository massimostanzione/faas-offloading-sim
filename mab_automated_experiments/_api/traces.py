import csv
import math
import os
from typing import List

import matplotlib.pyplot as plt
import numpy as np

from mab.contextual.utils import hours_to_secs

# based on a work by Anastasia Brinati

ampiezza = 100000.0

frequenza = 1 / (60 * 60)
durata = 3 * 60 * 60

DISTRIBUTION = None
np.random.seed(123456789)


def _generate_sinusoidal(i, min_rate, max_rate, period, step_len):
    FREQ = 2 / period * 1 * np.pi
    return np.round(min_rate + (max_rate - min_rate) / 2 + ((max_rate - min_rate) / 2) * math.sin(FREQ * step_len * i))


def _generate_bell(i, min_rate, max_rate, period, step_len):
    time_in_period = (i * step_len) % period
    normalized_time = time_in_period / period
    bell_shape = np.sin(np.pi * normalized_time)
    return min_rate + (max_rate - min_rate) * bell_shape

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


def _generate_triangle_wave(i, min_rate, max_rate, period, step_len):
    phase = ((i * step_len) % period) / period
    if phase < 0.5:
        val = 2 * phase
    else:
        val = 2 * (1 - phase)
    return np.round(min_rate + val * (max_rate - min_rate))

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


def _generate_exponential(i, min_rate, max_rate, duration, step_len):
    STEPS = int(duration / step_len)
    t = i / STEPS
    return min_rate + (max_rate - min_rate) * (math.exp(5 * t) - 1) / (math.exp(5) - 1)


def _generate_irregular_square(i, min_rate, intervals, steady_len):
    current_time = i * steady_len
    for start, end, rate in intervals:
        if start <= current_time < end:
            return rate
    return min_rate


def _generate_growing_steps(i, min_rate, max_rate, steady_len, step_len, duration):
    t = i * step_len
    if t >= duration:
        return max_rate

    total_steps = int(duration / steady_len)

    if total_steps <= 1:
        return max_rate

    step_num = (t) // steady_len

    rate_step = (max_rate - min_rate) / (total_steps - 1)

    return min_rate + (rate_step * step_num)


def _generate_decreasing_steps(i, min_rate, max_rate, steady_len, step_len, duration):
    t = i * step_len
    if t >= duration:
        return min_rate

    total_steps = int(duration / steady_len)

    if total_steps <= 1:
        return min_rate

    step_num = (t) // steady_len

    rate_step = (max_rate - min_rate) / (total_steps - 1)

    return max_rate - (rate_step * step_num)


def _generate_inverse_exponential_delayed(i, min_rate, max_rate, delay_steady, duration, step_len):
    t = i * step_len
    if t < delay_steady:
        return max_rate

    t_after_delay = t - delay_steady
    transition_duration = duration - delay_steady

    if t_after_delay >= transition_duration:
        return min_rate

    t_normalized = 1 - (t_after_delay / transition_duration)

    return min_rate + (max_rate - min_rate) * (math.exp(5 * t_normalized) - 1) / (math.exp(5) - 1)


def _generate_linear_delayed(i, min_rate, max_rate, delay_steady, duration, step_len):
    t = i * step_len
    if t < delay_steady:
        return max_rate

    t_after_delay = t - delay_steady
    transition_duration = duration - delay_steady

    if t_after_delay >= transition_duration:
        return min_rate

    return max_rate - (max_rate - min_rate) * (t_after_delay / transition_duration)


def _graph(interarrivals, rates, duration, step_len, distribution, file_path):
    path = os.path.join(os.path.dirname(__file__), "../_traces/img")
    if not os.path.exists(path): os.makedirs(path)
    STEPS = int(duration / step_len)

    fig, axs = plt.subplots(1, 2, figsize=(12, 5))

    # Grafico degli interarrivi
    axs[0].plot(interarrivals)
    axs[0].set_xlabel("Interarrival Time (s)")
    axs[0].set_ylabel("Frequency")
    axs[0].set_title("Interarrival Times")
    axs[0].grid(True)

    # Grafico dei rates
    axs[1].plot(np.arange(STEPS) * step_len, rates, label=f"", marker="o",
                color="r")  # , drawstyle='steps-post')
    axs[1].set_xlabel("Time (seconds)")
    axs[1].set_ylabel(f"Arrival Rate")
    axs[1].set_title(f"*{distribution}* Arrival Rate Over Time")
    axs[1].legend()
    axs[1].grid(True)

    plt.tight_layout()
    plt.savefig(file_path)


def generate_trace(name: str, distribution: str, min_rate: float, max_rate: float, period: float, step_len: float,
                   duration: float, delay: float = 0, steady_len=0):
    path=os.path.abspath(os.path.join(os.path.dirname(__file__),"../_traces/"+name+"_arrivals.iat"))
    if os.path.exists(path):
        print("Trace", name, "already generated, skipping...")
    else:
        STEPS = int(duration / step_len)
        nArrivals = np.zeros(STEPS)

        delay_steps = int(delay / step_len)

        for i in range(STEPS):
            if True:
                adjusted_i = i  # - delay_steps

                if distribution == "sinusoid":
                    nArrivals[i] = _generate_sinusoidal(adjusted_i, min_rate, max_rate, period, step_len) * step_len
                elif distribution == "bell":
                    nArrivals[i] = _generate_bell(adjusted_i, min_rate, max_rate, period, step_len) * step_len
                elif distribution == "halfbell":
                    nArrivals[i] = _generate_halfbell(adjusted_i, min_rate, max_rate, period, step_len) * step_len
                elif distribution == "shifted-sinusoid":
                    nArrivals[i] = _generate_shifted_sinusoidal(adjusted_i, min_rate, max_rate, period,
                                                                step_len) * step_len
                elif distribution == "linear":
                    nArrivals[i] = _generate_linear(adjusted_i, min_rate, max_rate, period, step_len,
                                                    duration - delay) * step_len
                elif distribution == "square-wave":
                    nArrivals[i] = _generate_square_wave(adjusted_i, min_rate, max_rate, period, step_len) * step_len
                elif distribution == "square-wave-inverted":
                    nArrivals[i] = _generate_square_wave_inverted(adjusted_i, min_rate, max_rate, period,
                                                                  step_len) * step_len
                elif distribution == "step":
                    nArrivals[i] = _generate_step(adjusted_i, min_rate, max_rate, period, step_len) * step_len
                elif distribution == "sawtooth-wave":
                    nArrivals[i] = _generate_sawtooth_wave(adjusted_i, min_rate, max_rate, period, step_len) * step_len
                elif distribution == "triangle":
                    nArrivals[i] = _generate_triangle_wave(adjusted_i, min_rate, max_rate, period, step_len) * step_len

                elif distribution == "logistic-map":
                    nArrivals[i] = _generate_logistic_map(adjusted_i) * step_len
                elif distribution == "gaussian-modulated":
                    sigma = 0.5
                    nArrivals[i] = _generate_gaussian_modulated(adjusted_i, min_rate, max_rate, sigma, step_len,
                                                                duration - delay, period) * step_len
                elif distribution == "exponential":
                    nArrivals[i] = _generate_exponential(adjusted_i, min_rate, max_rate, duration - delay,
                                                         step_len) * step_len
                elif distribution == "irregular-square":
                    RATE_INST3 = 1000
                    RATE_INST2 = 400
                    intervals = [(hours_to_secs(5), hours_to_secs(6), RATE_INST3),
                                 (hours_to_secs(9), hours_to_secs(10), RATE_INST2),
                                 (hours_to_secs(12), hours_to_secs(13), RATE_INST3),
                                 (hours_to_secs(14), hours_to_secs(15), RATE_INST2),
                                 (hours_to_secs(17), hours_to_secs(18), RATE_INST3),
                                 (hours_to_secs(21), hours_to_secs(22), RATE_INST2)
                                 ]
                    nArrivals[i] = _generate_irregular_square(adjusted_i, min_rate, intervals, step_len) * step_len

                elif distribution == "growing-steps":
                    nArrivals[i] = _generate_growing_steps(adjusted_i, min_rate, max_rate, steady_len,
                                                           step_len, duration) * step_len
                elif distribution == "decreasing-steps":
                    nArrivals[i] = _generate_decreasing_steps(adjusted_i, min_rate, max_rate, steady_len,
                                                              step_len, duration) * step_len
                elif distribution == "inverse-exponential-delayed":
                    nArrivals[i] = _generate_inverse_exponential_delayed(adjusted_i, min_rate, max_rate, delay,
                                                                         duration, step_len) * step_len
                elif distribution == "linear-delayed":
                    nArrivals[i] = _generate_linear_delayed(adjusted_i, min_rate, max_rate, delay, duration,
                                                            step_len) * step_len

                else:
                    print(f"Distribuzione '{distribution}' non supportata!")
                    return

        rates = nArrivals / step_len

        all_arrival_times_list = []
        rng = np.random.default_rng(123456789)

        for i in range(STEPS):
            num_arrivals_in_step = int(nArrivals[i])
            if num_arrivals_in_step > 0:
                t0 = step_len * i
                t1 = t0 + step_len

                arrivals_in_this_step = np.sort(rng.uniform(t0, t1, num_arrivals_in_step))
                all_arrival_times_list.extend(arrivals_in_this_step)

        arrival_times = np.array(all_arrival_times_list)

        if len(arrival_times) > 1:
            inter_arrival_times = np.diff(arrival_times)
        elif len(arrival_times) == 1:
            inter_arrival_times = np.array([arrival_times[0]])
        else:
            inter_arrival_times = np.array([])

        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_traces", "img", f"{name}_plot.png"))

        _graph(inter_arrival_times, rates, duration, step_len, distribution, file_path)

        print(f"Generated {len(nArrivals)} rates.")

        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/" + name + "_arrivals.iat"))
        pathfolder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces"))
        if not os.path.exists(pathfolder): os.makedirs(pathfolder)

        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(zip(inter_arrival_times))

        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/" + name + "_rates.iat"))
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Rate"])
            writer.writerows(zip(rates))


def print_traces(trace_names: List, step_len=5):
    plt.figure(figsize=(10, 6))
    for t in trace_names:
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../_traces/" + t + "_rates.iat"))
        try:
            rates = []
            with open(path, 'r') as f:
                reader = csv.reader(f)
                # Salta l'intestazione
                next(reader)
                # Leggi i tassi dal file
                rates = [float(row[0]) for row in reader]
        except FileNotFoundError:
            print(f"Errore: Il file {path} non è stato trovato.")
            return

        if not rates:
            print("Il file non contiene dati di tasso di arrivo.")
            return

        time_axis = np.arange(len(rates)) * step_len

        plt.plot(time_axis, rates, linestyle='-')
    plt.title('Traccia')
    plt.xlabel('Tempo [s]')
    plt.ylabel('Tasso di Arrivo [req/s]')
    plt.grid(True)

    outfile = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_traces", "img_custom", f"{t}_plot.png"))
    plt.savefig(outfile)
