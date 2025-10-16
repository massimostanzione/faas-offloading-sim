from conf import MAB_RTK_CONTEXTUAL_SCENARIOS
from mab.contextual.utils import is_strategy_RTK
from mab_automated_experiments._api.stability import compute_stability_index
from mab_automated_experiments._internal.reward_function_representation import RewardFunctionIdentifierConverter, \
    RewardFnAxis


def heatmap_with_baseline_multiple_rewards_functions(
        records,
        gradient_limits=None,
        target=None,
        strategies=["UCB", "UCBTuned", "UCB2", "KL-UCBsp", "RTK-UCBTuned", "RTK-UCB2", "RTK-UCB2-ER", "RTK-KL-UCBsp"],
        scenarios=['', "KD", "KIT", "KI2", "KR"],
        specfiles=["CYC", "SAT", "DEC", "BUR"],
        title_preamble=""):
    reward_functions = []
    for r in records:
        repr = RewardFunctionIdentifierConverter.deserialize_reward_function(r.identifiers)
        if repr not in reward_functions:
            reward_functions.append(repr)

    plots = []
    title_preamble_act = ""
    for rew in reward_functions:
        if rew.is_by_axes() and rew.axis_pre == RewardFnAxis.RESPONSETIME:
            title_preamble_act = title_preamble + r" $(\beta=1)$"
        elif rew.is_by_axes() and rew.axis_pre == RewardFnAxis.COLD_STARTS:
            title_preamble_act = title_preamble + r" $(\eta=1)$"
        elif rew.is_by_reward_config() and rew.get_representation().beta == 0.5:
            title_preamble_act = title_preamble + r" $(\beta=\eta=0.5)$"

        plt, ax1, ax2 = (
            heatmap_with_baseline_single_reward_function(records, rew, gradient_limits, target, strategies, scenarios,
                                                         specfiles, title_param=title_preamble_act))
        plots.append([plt, ax1, ax2])
    return plots


import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


def heatmap_with_baseline_single_reward_function(
        records,
        reward_function,
        gradient_limits=None,
        target=None,
        strategies=["UCB", "UCBTuned", "UCB2", "KL-UCBsp",
                    "RTK-UCBTuned", "RTK-UCB2", "RTK-UCB2-ER", "RTK-KL-UCBsp"],
        scenarios=['', "KD", "KIT", "KI2", "KR"],
        specfiles=["CYC", "SAT", "DEC", "BUR"],
        title_param=""
):
    plt.rcParams.update({
        "text.usetex": True,
        "font.family": "serif",
        "font.serif": ['Computer Modern Roman'],
        "font.sans-serif": "Helvetica",
        'mathtext.fontset': "cm",
        'font.size': 16,
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'legend.fontsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
    })

    is_ctx = False
    for s in strategies:
        if is_strategy_RTK(s):
            is_ctx = True
            break

    values = []
    for specfile in specfiles:
        values_iter = np.array([])
        for strategy in strategies:
            for scenario in scenarios:
                for_seeds = []
                for r in records:
                    if (reward_function, specfile, strategy, scenario) == (
                            RewardFunctionIdentifierConverter.deserialize_reward_function(r.identifiers),
                            r.identifiers["specfile"],
                            r.identifiers["strategy"],
                            r.identifiers[MAB_RTK_CONTEXTUAL_SCENARIOS] if is_strategy_RTK(strategy) else '',
                    ) and not "NOTICE" in r.results:  # NOTA: non buono per bayesopt
                        if target:
                            for_seeds.append(compute_stability_index(r.results, r.identifiers["strategy"]))
                        else:
                            for_seeds.append(r.results["cumavg-reward"])
                if len(for_seeds) > 0:
                    if strategy == "RTK-KL-UCBsp" or strategy == "KL-UCBsp":
                        print(reward_function, scenario, for_seeds)
                    values_iter = np.append(values_iter, np.average(for_seeds))

        values.append(values_iter)

    # transpose for baseline row
    values = np.array(values).T

    if values.size == 0:
        raise ValueError("empty values matrix")

    baseline_row = values[:1, :]
    data_rows = values[1:, :]

    labels_y = []
    for s in strategies:
        label = s
        if s == "UCB":
            label = "UCB1"
        elif s == "KL-UCBsp":
            label = "KL--UCB"
        elif s == "RTK-KL-UCBsp":
            label = "RTK-KL-UCB"

        if not is_strategy_RTK(s):
            labels_y.append(label)

    for s in strategies:
        if is_strategy_RTK(s):
            for sc in scenarios:
                if sc != "":
                    sc_act = sc
                    if sc == "KIT": sc_act = "KI1"
                    labels_y.append(f"{s} ({sc_act})")

    # normalization + colormap

    if target == "stability_index":
        cmap_heatmap = plt.colormaps["coolwarm"]
    elif target == "stability_index_abs":
        cmap_heatmap = plt.colormaps["YlOrRd"]

    else:
        cmap_heatmap = plt.colormaps["RdYlGn"]

    n_lower = data_rows.shape[0]
    n_cols = baseline_row.shape[1]

    all_percs = []
    for j in range(n_cols):
        base = baseline_row[0, j]
        col = data_rows[:, j] if n_lower > 0 else np.array([])
        if np.isclose(base, 0):
            continue
        perc = ((col - base) / abs(base)) * 100.0
        if perc.size > 0:
            all_percs.extend(perc[~np.isnan(perc)])
    if target is None:
        max_abs_perc_global = 20
    elif target == "stability_index":
        max_abs_perc_global = 100
    elif target == "stability_index_abs":
        max_abs_perc_global = 1
    if target == "stability_index_abs":
        normalized_values = data_rows.copy()
    else:
        if n_lower > 0:
            normalized_values = np.full_like(data_rows, 0.5, dtype=float)
            for j in range(n_cols):
                base = baseline_row[0, j]
                col = data_rows[:, j]
                if np.isclose(base, 0):
                    normalized_values[:, j] = np.nan
                    continue
                perc = ((col - base) / abs(base)) * 100.0
                if max_abs_perc_global > 0:
                    normalized_values[:, j] = (perc + max_abs_perc_global) / (2 * max_abs_perc_global)
                else:
                    normalized_values[:, j] = 0.5
                normalized_values[np.isnan(perc), j] = np.nan
        else:
            normalized_values = np.zeros((0, n_cols), dtype=float)

    fig = plt.figure(
        figsize=(max(8, n_cols * 0.6), 1.6 + n_lower * 0.45),
        constrained_layout=False
    )

    wspace = 0.18  # hdistance heatmap - colorbar
    hspace = 0.18  # vdistance baseline - heatmap

    gs = GridSpec(
        nrows=2, ncols=2, figure=fig,
        width_ratios=[20, 1],
        height_ratios=[0.7, max(3, n_lower)],
        wspace=wspace, hspace=hspace
    )

    ax1 = fig.add_subplot(gs[0, 0])  # baseline
    ax2 = fig.add_subplot(gs[1, 0], sharex=ax1)  # heatmap principale
    cax = fig.add_subplot(gs[:, 1])  # colorbar

    title = r"$\bar{R}$" if not target else r"$I_S$"
    ax1.set_title(title_param + r" --- " + title)

    if target == "stability_index_abs":
        baseline_normalized = baseline_row.copy()
        im_baseline = ax1.imshow(baseline_normalized, cmap=cmap_heatmap, aspect="auto",
                                 interpolation="nearest",
                                 extent=[-0.5, n_cols - 0.5, -0.5, 0.5],
                                 vmin=0, vmax=1)

    else:
        neutral = np.zeros_like(baseline_row)
        ax1.imshow(neutral, cmap="binary", aspect="auto",
                   interpolation="nearest",
                   extent=[-0.5, n_cols - 0.5, -0.5, 0.5])

    xtick_labels = []
    for sf in specfiles:
        if sf == "enrico":
            xtick_labels.append("base")
        else:
            xtick_labels.append(sf)

    ax1.set_xticks(range(n_cols))
    ax1.set_xticklabels(xtick_labels, rotation=45)
    ax1.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False)

    ax2.tick_params(axis="x", labelbottom=False, bottom=False)

    ax1.xaxis.set_label_position("top")
    ax1.xaxis.tick_top()

    for j in range(n_cols):
        val = baseline_row[0, j]
        if not np.isnan(val):
            ax1.text(j, 0, f"{val:.6f}", ha='center', va='center', color='black', fontsize=14)

    if len(labels_y) > 0:
        ax1.set_yticks([0])
        ax1.set_yticklabels([labels_y[0]])
        ax1.tick_params(axis='y', pad=10)

    ax1.set_xlim(-0.5, n_cols - 0.5)
    ax2.set_xlim(-0.5, n_cols - 0.5)

    if n_lower > 0:
        im = ax2.imshow(normalized_values, cmap=cmap_heatmap, aspect='auto',
                        interpolation='nearest', vmin=0, vmax=1)
    else:
        im = ax2.imshow(np.zeros((1, n_cols)), cmap=cmap_heatmap, aspect='auto',
                        interpolation='nearest', vmin=0, vmax=1)

    all_percs_text = []
    for i in range(n_lower):
        for j in range(n_cols):
            val = data_rows[i, j]
            base = baseline_row[0, j]
            if np.isnan(val):
                continue

            fontsize = 11
            weight = "normal"

            # per i casi contestuali, per il confronto con la versione base non-ctx
            if is_ctx and val > data_rows[0, j]:
                weight = "bold"

            if (not np.isnan(base)) and (base != 0):
                signum = -1 if not target else 1
                diff_perc = signum * round(((val - base) / base) * 100.0, 1)
                if target == "stability_index_abs":
                    txt = f"{round(val, 6)}"
                    all_percs_text.append(diff_perc)
                    fontsize = 11
                else:
                    line1 = f"{round(val, 6)}"
                    line2 = f"{diff_perc:+.1f}\\%"
                    txt = f"\\shortstack{{{line1}\\\\{line2}}}"
                    all_percs_text.append(diff_perc)
            else:
                txt = f"{round(val, 6)}"

            if weight == "bold":
                txt = r"\textbf{\mbox{" + txt + r"}}"

            ax2.text(j, i, txt, ha='center', va='center', color='black', fontsize=fontsize)  # , fontweight=weight)

    ylabels_for_data = labels_y[1:1 + n_lower] if len(labels_y) >= 1 + n_lower else [f"r{i}" for i in range(n_lower)]
    if n_lower > 0:
        ax2.set_yticks(range(n_lower))
        ax2.set_yticklabels(ylabels_for_data)
    else:
        ax2.set_yticks([])

    cbar = fig.colorbar(im, cax=cax, orientation='vertical')

    cbar.ax.tick_params(labelsize=10)

    max_abs_perc = max_abs_perc_global if max_abs_perc_global > 0 else (
        max(abs(np.array(all_percs_text))) if len(all_percs_text) > 0 else 0)
    ticks = np.linspace(0, 1, 5)
    cbar.set_ticks(ticks)
    if target != "stability_index_abs":
        labels = np.linspace(-max_abs_perc, max_abs_perc, 5)
        cbar.set_ticklabels([f'+{round(l, 1)}\%' if l > 0 else f'{round(l, 1)}\%' for l in labels])
        cbar.set_label('Variazione \% risp. baseline', rotation=270, labelpad=12, fontsize=10)
    else:
        labels = np.linspace(0, max_abs_perc, 5)
        cbar.set_ticklabels([f'{round(l, 2)}' for l in labels])
        cbar.set_label(r'$I_S$', rotation=270, labelpad=12, fontsize=10)

    if is_ctx:
        fig.subplots_adjust(left=0.22, top=0.73, right=0.86)
    else:
        fig.subplots_adjust(top=0.73, right=0.86)
    return (fig, ax1, ax2)
