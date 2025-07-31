import os
import sys
from datetime import datetime

import matplotlib.cm as cm
import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _internal import consts

timestamp = datetime.now().replace(microsecond=0)


def _prepare_plot(fig_title_prefix, curr_specfile, xlabel, ylabel, ylim=None):
    fig, ax1 = plt.subplots(figsize=(12, 6))
    fig.suptitle(f"{fig_title_prefix} - {curr_specfile}")
    ax1.set_title("by container expiration time")
    ax1.set_xlabel(xlabel)
    ax1.set_ylabel(ylabel)
    if ylim is not None:
        ax1.set_ylim(ylim)
    return fig, ax1


def _process_series_keys(series, key_type=float):
    try:
        sorted_keys = sorted([key_type(k) for k in series.keys()])
        sorted_keys_str = [str(k) for k in sorted(series.keys(), key=key_type)]
        return sorted_keys, sorted_keys_str
    except ValueError:
        print(f"Cannot convert 'series' keys to {key_type.__name__}.")
        return None, None


def _plot_series(ax, time, series, sorted_keys_str, colors, highlight):
    for i, key_str in enumerate(sorted_keys_str):
        print(series, key_str)
        v = series[int(key_str)]
        color = colors[i] if key_str not in highlight else "yellow"
        size = 10 if key_str not in highlight else 100
        ax.scatter(time, v, color=color, label=key_str, s=size)


def _add_colorbar(fig, ax, sorted_keys_float, sorted_keys_str, colormap, highlight):
    if len(sorted_keys_float) > 1:
        norm = plt.Normalize(vmin=sorted_keys_float[0], vmax=sorted_keys_float[-1])
        sm = cm.ScalarMappable(cmap=colormap, norm=norm)
        sm.set_array([])
        cbar = fig.colorbar(sm, ax=ax, label='expiration timeout')
        cbar.set_ticks(sorted_keys_float)
        cbar.set_ticklabels(sorted_keys_str)

        for label in cbar.ax.yaxis.get_majorticklabels():
            if label.get_text() in highlight:
                label.set_color('yellow')
                break

        cbar.ax.tick_params(labelsize='small')
        cbar.ax.yaxis.set_tick_params(pad=1)


def _finalize_plot(fig, ax, curr_specfile, filename_suffix):
    ax.legend()
    ax.grid(True)
    filepath = os.path.join(SCRIPT_DIR, "output",
                            consts.DELIMITER_HYPHEN.join(
                                [str(timestamp), curr_specfile]).replace(' ', '-') + "-" + filename_suffix + ".svg")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fig.savefig(filepath)
    plt.close(fig)


def _generate_graph(series: dict, time, curr_specfile, highlight=None,
                    fig_title_prefix="", xlabel='Time [s]', ylabel='',
                    ylim=None, filename_suffix="", key_type=float):
    if highlight is None:
        highlight = []

    fig, ax1 = _prepare_plot(fig_title_prefix, curr_specfile, xlabel, ylabel, ylim)

    sorted_keys_float, sorted_keys_str = _process_series_keys(series, key_type)
    if sorted_keys_float is None:
        plt.close(fig)
        return

    num_series = len(sorted_keys_float)
    colormap = plt.cm.coolwarm
    colors = [colormap(i / (num_series - 1)) if num_series > 1 else colormap(0) for i in range(num_series)]

    _plot_series(ax1, time, series, sorted_keys_str, colors, highlight)
    _add_colorbar(fig, ax1, sorted_keys_float, sorted_keys_str, colormap, highlight)
    _finalize_plot(fig, ax1, curr_specfile, filename_suffix)


def graph_avgMemUtil(series: dict, time, curr_specfile, highlight=None, active_memory=False):
    title_prefix = "Average ***ACTIVE*** Memory Utilization" if active_memory else "Average Memory Utilization"
    filename_suffix = "avgmemutilACTIVE" if active_memory else "avgmemutil"
    _generate_graph(series, time, curr_specfile, highlight,
                    fig_title_prefix=title_prefix,
                    xlabel='Time [s]',
                    ylabel='avgMemoryUtilization_sys',
                    ylim=[0, 1],
                    filename_suffix=filename_suffix,
                    key_type=float)


def graph_availMem(series: dict, time, curr_specfile, highlight=None):
    _generate_graph(series, time, curr_specfile, highlight,
                    fig_title_prefix="Total memory available",
                    xlabel='Tempo [s]',
                    ylabel='availMem_sys (SUM)',
                    filename_suffix="availMem",
                    key_type=float)


def graph_warmContainers(series: dict, time, curr_specfile, highlight=None):
    _generate_graph(series, time, curr_specfile, highlight,
                    fig_title_prefix="Warm containers",
                    xlabel='Tempo [s]',
                    ylabel='warm containers (SUM)',
                    filename_suffix="warm_ctrs",
                    key_type=int)


def graph_coldStartProb(series: dict, time, curr_specfile, highlight=None):
    _generate_graph(series, time, curr_specfile, highlight,
                    fig_title_prefix="Cold start prob",
                    xlabel='Tempo [s]',
                    ylabel='cold start prob (AVG)',
                    filename_suffix="coldStartProb",
                    key_type=int)


def graph_drops(series: dict, time, curr_specfile, highlight=None):
    _generate_graph(series, time, curr_specfile, highlight,
                    fig_title_prefix="Drops",
                    xlabel='Tempo [s]',
                    ylabel='drops (SUM)',
                    filename_suffix="drops",
                    key_type=int)

