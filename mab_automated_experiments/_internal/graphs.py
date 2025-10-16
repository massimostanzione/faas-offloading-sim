import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import shapiro, skew, kurtosis

from mab_automated_experiments._internal import consts

UPDATE_INTERVAL = 3600


def plot_simple_xy(series: dict, title: str = "", xlabel: str = "", ylabel: str = ""):
    for item in series.items():
        key = item[0]
        value = item[1]
        plt.plot(value["x"], value["y"], label=key)
    plt.legend()
    plt.xlabel(xlabel)  # add X-axis label
    plt.ylabel(ylabel)  # add Y-axis label
    plt.title(title)  # add title
    return plt


def plot_policy_choices(series: dict):
    rcParams['mathtext.fontset'] = 'stix'
    rcParams['font.family'] = 'STIXGeneral'
    col = -1
    for item in series.items():
        col += 1
        key = item[0]
        value = item[1]
        cum_rewards = []
        cum_reward = 0
        time_frames = value["x"]
        rewards = value["y"]
        axis_pre = value["ax_pre"]
        axis_post = value["ax_post"]

        for i in range(0, len(time_frames)):
            cum_reward += rewards[i]
            n = i + 1
            cum_rewards.append(cum_reward / n)

        plt.plot(time_frames, cum_rewards, label=key)

        # ok se si ripete
        title = "Cum. avg. reward: "
        is_stationary = axis_pre == axis_post
        if not is_stationary: title += "non-"
        title += "stationary scenario "
        title += "(" + axis_pre
        if not is_stationary:
            title += "$\\rightarrow$" + axis_post
        title += ")"

    xlabel = "Time (s)"
    ylabel = "Reward (cum. avg.)"

    plt.axvline(x=UPDATE_INTERVAL, color='black', linestyle='--', label='weights updated')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(axis="y")
    plt.legend(
        # bbox_to_anchor=(0.5, -0.1),
        # loc='upper center',
        fancybox=True,
        shadow=True,
        # ncol=4,
        # fontsize="small"
    )
    plt.title(title)  # add title
    return plt


def plot_rewards_paramconfs(series: dict, strat: str):
    rcParams['mathtext.fontset'] = 'stix'
    rcParams['font.family'] = 'STIXGeneral'
    col = -1
    color_map = plt.cm.get_cmap("prism", len(consts.RewardFnAxis))
    line_styles = ['-', '--', ':', '-.', (0, (1, 1))]

    example_key = next(iter(series.keys()))
    is_simple_labels = "," not in example_key

    if is_simple_labels:
        unique_axes = sorted(set(series.keys()))
    else:
        unique_axes = sorted(set(label.split(",")[0].strip() for label in series.keys()))
        unique_values = sorted(set(label.split("=")[-1].strip() for label in series.keys()))

    for item in series.items():
        col += 1
        key = item[0]
        lab = "$" + item[0].replace("alpha", r"\alpha") + "$"
        value = item[1]
        if is_simple_labels:
            axis = key.strip()
            label = axis
        else:
            axis, value_label = key.split(",")
            axis = axis.strip()
            parameter, value_label = value_label.split("=")
            parameter = parameter.strip()
            value_label = value_label.strip()
            if parameter == "alpha":
                parameter = r"\alpha"
            label = f"{axis}, ${parameter}={value_label}$"
        cum_rewards = []
        cum_reward = 0
        time_frames = value["x"]
        rewards = value["y"]
        axis_pre = value["ax_pre"]
        axis_post = value["ax_post"]

        for i in range(0, len(time_frames)):
            cum_reward += rewards[i]
            n = i + 1
            cum_rewards.append(cum_reward / n)

        style_idx = 0 if is_simple_labels else unique_values.index(value_label) % len(line_styles)

        color_idx = unique_axes.index(axis)
        plt.plot(time_frames, cum_rewards, label=lab,
                 linestyle=line_styles[style_idx], color=color_map(color_idx))

        # ok se si ripete
        title = "Cum. avg. reward: " + strat + ", "
        is_stationary = axis_pre == axis_post
        if not is_stationary: title += "non-"
        title += "stationary scenario "
        title += "(" + axis_pre
        if not is_stationary:
            title += "$\\rightarrow$" + axis_post
        title += ")"

    xlabel = "Time (s)"
    ylabel = "Reward (cum. avg.)"

    plt.axvline(x=UPDATE_INTERVAL, color='black', linestyle='--', label='weights updated')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(axis="y")
    plt.legend(
        bbox_to_anchor=(0.5, -0.1),
        loc='upper center',
        fancybox=True,
        shadow=True,
        ncol=4,
        fontsize="small"
    )
    plt.title(title)  # add title
    return plt


# seeds
def plot_reward_distributions(series: dict, strat: str, axis_pre: str, axis_post: str):
    rcParams['mathtext.fontset'] = 'stix'
    rcParams['font.family'] = 'STIXGeneral'
    col = -1

    bbox_to_anchor = (1, 0.5),
    loc = 'center left',
    fancybox = True,
    shadow = True,

    # ncol=4,
    # fontsize="small"

    def analyze_distribution(y_values, seed):
        # Statistiche descrittive
        mean_y = np.mean(y_values)
        var_y = np.var(y_values)
        skewness = skew(y_values)
        kurt = kurtosis(y_values)

        stat, p_value = shapiro(y_values)
        normality = "Normale" if p_value > 0.05 else "Non normale"

        return {
            "Seed": seed,
            "Media": mean_y,
            "Varianza": var_y,
            "Skewness": skewness,
            "Curtosi": kurt,
            "Shapiro-Wilk stat": stat,
            "p-value": p_value,
            "Normalità": normality
        }

    report = []
    for seed, data in series.items():
        y_values = data["y"]
        report.append(analyze_distribution(y_values, seed))

    for entry in report:
        print(f"Risultati per seed {entry['Seed']}, caso con {strat}, assi: {axis_pre}, {axis_post}")
        print(f"  Media: {entry['Media']:.3f}")
        print(f"  Varianza: {entry['Varianza']:.3f}")
        print(f"  Skewness: {entry['Skewness']:.3f}")
        print(f"  Curtosi: {entry['Curtosi']:.3f}")
        print(f"  Shapiro-Wilk stat: {entry['Shapiro-Wilk stat']:.3f}")  # Nome corretto
        print(f"  p-value: {entry['p-value']:.3e}")
        print(f"  Normalità: {entry['Normalità']}")
        print("-" * 40)

    return plt


from matplotlib import rcParams


def plot_arms_disparity(series: dict, strategy: str, is_stationary: bool = True, ef_range=None, var_coeff_max: int = 3,
                        ax_pre: str = None):
    import matplotlib.pyplot as plt
    import numpy as np

    rcParams['mathtext.fontset'] = 'stix'
    rcParams['font.family'] = 'STIXGeneral'

    if ef_range is None:
        ef_range = [0, 1]
    y_max = round(var_coeff_max, 6)
    color_map = plt.cm.get_cmap("prism", len(consts.RewardFnAxis))
    line_styles = ['-', '--', ':', '-.', (0, (1, 1))]

    example_key = next(iter(series.keys()))
    is_simple_labels = "," not in example_key

    if is_simple_labels:
        unique_axes = sorted(set(series.keys()))
    else:
        unique_axes = sorted(set(label.split(",")[0].strip() for label in series.keys()))
        unique_values = sorted(set(label.split("=")[-1].strip() for label in series.keys()))

    plt.figure(figsize=(8, 5))

    for key, value in series.items():
        if is_simple_labels:
            axis = key.strip()
            label = axis
        else:
            axis, value_label = key.split(",")
            axis = axis.strip()
            parameter, value_label = value_label.split("=")
            parameter = parameter.strip()
            value_label = value_label.strip()
            if parameter == "alpha":
                parameter = r"\alpha"
            label = f"{axis}, ${parameter}={value_label}$"

        color_idx = unique_axes.index(axis)
        style_idx = 0 if is_simple_labels else unique_values.index(value_label) % len(line_styles)
        if is_stationary or (not is_stationary and not axis.split("$\\rightarrow$ ")[1] == ax_pre):
            colorx = color_map(color_idx)
        else:
            colorx = 'silver'
        plt.plot(
            value["x"], value["y"],
            label=label,
            color=colorx,
            linestyle=line_styles[style_idx]
        )

    min_x, max_x = ef_range[0], ef_range[1]
    num_points = next(len(val["x"]) for val in series.values())
    step = (max_x - min_x) / (num_points - 1)
    x_ticks = np.arange(0, max_x + step, step)
    plt.xticks(x_ticks)
    plt.grid(axis='x', linestyle='--', color='gray', alpha=0.7)

    plt.ylim(0, y_max + 0.1)
    plt.axhline(y=y_max, color='black', linestyle='--', linewidth=1, label=f"$VC_{{max}}={y_max}$")

    xlabel = "Exploration Factor" if not strategy == "KL-UCBsp" else "$c$"
    plt.xlabel(xlabel)
    plt.ylabel("VC for arm choices")
    title = ("Stationary " if is_stationary else "Non-stationary ") + f"scenario: {strategy}"
    if not is_stationary:
        title += f" ({ax_pre})"
    plt.title(title)

    # per ogni riga, 4 items
    legend_rows = (len(series) + 3) // 4
    legend_bottom = -0.2 - (legend_rows - 1) * 0.1

    plt.legend(
        bbox_to_anchor=(0.5, -0.1),
        loc='upper center',
        fancybox=True,
        shadow=True,
        ncol=4,
        fontsize="small"
    )

    plt.tight_layout()

    return plt
