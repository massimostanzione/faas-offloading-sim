import configparser

import conf
from mab_automated_experiments._internal import consts
from mab_automated_experiments._internal.experiment import MABExperiment, extract_iterable_params_from_config
from mab_automated_experiments._internal.reward_function_representation import RewardFunctionRepresentation
from simulation import RewardConfig


def build_experiment_from_config(config: configparser.ConfigParser)->MABExperiment:
    change_axis_time = 0  # this is hardcoded, expand if you want to handle a specific axis change time
    # either you specify a complete reward config or a single/pair_of axis
    if "axis_pre" not in config["reward_fn"]:
        reward_config = RewardConfig(
            float(config["reward_fn"][conf.MAB_REWARD_ALPHA] if conf.MAB_REWARD_ALPHA in config["reward_fn"] else 0),
            float(config["reward_fn"][conf.MAB_REWARD_BETA] if conf.MAB_REWARD_BETA in config["reward_fn"] else 0),
            float(config["reward_fn"][conf.MAB_REWARD_GAMMA] if conf.MAB_REWARD_GAMMA in config["reward_fn"] else 0),
            float(config["reward_fn"][conf.MAB_REWARD_DELTA] if conf.MAB_REWARD_DELTA in config["reward_fn"] else 0),
            float(config["reward_fn"][conf.MAB_REWARD_ZETA] if conf.MAB_REWARD_ZETA in config["reward_fn"] else 0),
            float(config["reward_fn"][conf.MAB_REWARD_ETA] if conf.MAB_REWARD_ETA in config["reward_fn"] else 0),

            float(config["reward_fn"][conf.MAB_REWARD_ALPHA_POST] if conf.MAB_REWARD_ALPHA_POST in config[
                "reward_fn"] else (
                config["reward_fn"][conf.MAB_REWARD_ALPHA] if conf.MAB_REWARD_ALPHA in config["reward_fn"] else 0)),
            float(config["reward_fn"][conf.MAB_REWARD_BETA_POST] if conf.MAB_REWARD_BETA_POST in config[
                "reward_fn"] else (
                config["reward_fn"][conf.MAB_REWARD_BETA] if conf.MAB_REWARD_BETA in config["reward_fn"] else 0)),
            float(config["reward_fn"][conf.MAB_REWARD_GAMMA_POST] if conf.MAB_REWARD_GAMMA_POST in config[
                "reward_fn"] else (
                config["reward_fn"][conf.MAB_REWARD_GAMMA] if conf.MAB_REWARD_GAMMA in config["reward_fn"] else 0)),
            float(config["reward_fn"][conf.MAB_REWARD_DELTA_POST] if conf.MAB_REWARD_DELTA_POST in config[
                "reward_fn"] else (
                config["reward_fn"][conf.MAB_REWARD_DELTA] if conf.MAB_REWARD_DELTA in config["reward_fn"] else 0)),
            float(config["reward_fn"][conf.MAB_REWARD_ZETA_POST] if conf.MAB_REWARD_ZETA_POST in config[
                "reward_fn"] else (
                config["reward_fn"][conf.MAB_REWARD_ZETA] if conf.MAB_REWARD_ZETA in config["reward_fn"] else 0)),
            float(
                config["reward_fn"][conf.MAB_REWARD_ETA_POST] if conf.MAB_REWARD_ETA_POST in config["reward_fn"] else (
                    config["reward_fn"][conf.MAB_REWARD_ETA] if conf.MAB_REWARD_ETA in config["reward_fn"] else 0))
        )
        reward_functions = [RewardFunctionRepresentation.by_reward_config(reward_config, change_axis_time)]
    else:
        axes_pre = config["reward_fn"]["axis_pre"].replace(' ', '').split(consts.DELIMITER_COMMA)
        axes_post = config["reward_fn"]["axis_post"].replace(' ', '').split(consts.DELIMITER_COMMA) if "axis_post" in \
                                                                                                       config[
                                                                                                           "reward_fn"] else [
            '']

        reward_config = None
        reward_functions = []

        # single axis (static environment)
        for axis_pre in axes_pre:
            for axis_post in ([axis_pre] if axes_post == [''] else axes_post):
                reward_functions.append(
                    RewardFunctionRepresentation.by_axes_as_strings(axis_pre, axis_post, change_axis_time))

    exp = MABExperiment(
        config,
        config["experiment"]["name"],
        config["strategies"]["strategies"].replace(' ', '').split(consts.DELIMITER_COMMA),
        reward_functions,
        config["experiment"][conf.CLOSE_DOOR_TIME] if conf.CLOSE_DOOR_TIME in config["experiment"] else 28800,
        int(config["experiment"][conf.STAT_PRINT_INTERVAL]) if conf.STAT_PRINT_INTERVAL in config[
            "experiment"] else consts.DEFAULT_STAT_PRINT_INTERVAL,
        config["experiment"][conf.MAB_UPDATE_INTERVAL] if conf.MAB_UPDATE_INTERVAL in config[
            "experiment"] else consts.DEFAULT_MAB_UPDATE_INTERVAL,
        config["experiment"][
            conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL] if conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL in config[
            "experiment"] else None,
        config["experiment"][conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS].replace(' ', '').split(
            consts.DELIMITER_COMMA) if conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS in config["experiment"] else None,
        config["parameters"][conf.MAB_RTK_CONTEXTUAL_SCENARIOS].replace(' ', '').split(
            consts.DELIMITER_COMMA) if conf.MAB_RTK_CONTEXTUAL_SCENARIOS in config["parameters"] else None,

        extract_iterable_params_from_config(config),
        [],
        config["output"]["run-duplicates"],
        config.getint("experiment", "max-parallel-execution"),
        config["parameters"]["seeds"].replace(' ', '').split(consts.DELIMITER_COMMA),
        config["parameters"]["specfiles"].replace(' ', '').split(consts.DELIMITER_COMMA) if 'specfiles' in config[
            "parameters"] else ["../../spec"],
        config["parameters"][conf.EXPIRATION_TIMEOUT].replace(' ', '').split(
            consts.DELIMITER_COMMA) if conf.EXPIRATION_TIMEOUT in
                                                                                                        config[
                                                                                                            "parameters"] else
        [
            consts.DEFAULT_EXPIRATION_TIMEOUT],
        config["output"]["persist"].replace(' ', '').split(consts.DELIMITER_COMMA) if 'persist' in config[
            "output"] else "",
    )
    return exp
