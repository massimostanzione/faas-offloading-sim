import configparser

import conf
from simulation import RewardConfig
from .._internal.experiment import MABExperiment, extract_iterable_params_from_config
from .._internal import consts
from .._internal.reward_function_representation import RewardFunctionRepresentation


def build_experiment_from_config(config: configparser.ConfigParser)->MABExperiment:
    global axis_pre, axis_post, exp
    axis_pre = config["reward_fn"]["axis_pre"].replace(' ', '').split(consts.DELIMITER_COMMA)
    axis_post = config["reward_fn"]["axis_post"].replace(' ', '').split(consts.DELIMITER_COMMA)
    is_single_axis = axis_post == ['']
    change_axis_time=0 # TODO
    if axis_pre is not None and axis_post is not None:
        reward_config = None
        reward_function_representation=RewardFunctionRepresentation.by_axes_as_strings(axis_pre, axis_post, change_axis_time)
    else:
        reward_config = RewardConfig(
            config["reward_fn"][conf.MAB_REWARD_ALPHA],
            config["reward_fn"][conf.MAB_REWARD_BETA],
            config["reward_fn"][conf.MAB_REWARD_GAMMA],
            config["reward_fn"][conf.MAB_REWARD_DELTA],
            config["reward_fn"][conf.MAB_REWARD_ZETA],
            config["reward_fn"][conf.MAB_REWARD_ETA],

            config["reward_fn"][confp.MAB_REWARD_ALPHA_POST],
            config["reward_fn"][conf.MAB_REWARD_BETA_POST],
            config["reward_fn"][conf.MAB_REWARD_GAMMA_POST],
            config["reward_fn"][conf.MAB_REWARD_DELTA_POST],
            config["reward_fn"][conf.MAB_REWARD_ZETA_POST],
            config["reward_fn"][confp.MAB_REWARD_ETA_POST]
        )
        reward_function_representation=RewardFunctionRepresentation.by_reward_config(reward_config, change_axis_time)
    # TODO ripercorrere i passaggi dall'expconf all'esecuzione effettiva e semplificare
    # TODO le costanti non registrate (sia stringhe che numeri), a file
    # TODO i valori di default, metterli in un punto solo, ad esempio la classe MabExperiment
    # todo come questo int() che è più sotto, così applicare ovunque - sono numeri, non stringhe
    exp = MABExperiment(
        config,
        config["experiment"]["name"],
        config["strategies"]["strategies"].replace(' ', '').split(consts.DELIMITER_COMMA),
        reward_function_representation,
        config["experiment"][conf.CLOSE_DOOR_TIME] if conf.CLOSE_DOOR_TIME in config["experiment"] else 28800,
        int(config["experiment"][conf.STAT_PRINT_INTERVAL]) if conf.STAT_PRINT_INTERVAL in config[
            "experiment"] else consts.DEFAULT_STAT_PRINT_INTERVAL,
        config["experiment"][conf.MAB_UPDATE_INTERVAL] if conf.MAB_UPDATE_INTERVAL in config[
            "experiment"] else consts.DEFAULT_MAB_UPDATE_INTERVAL,
        config["experiment"][
            conf.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL] if confp.MAB_INTERMEDIATE_SAMPLING_UPDATE_INTERVAL in config[
            "experiment"] else None,
        config["experiment"][conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS].replace(' ', '').split(
            consts.DELIMITER_COMMA) if conf.MAB_INTERMEDIATE_SAMPLING_STATS_KEYS in config["experiment"] else None,
        config["parameters"][conf.MAB_RTK_CONTEXTUAL_SCENARIOS].replace(' ', '').split(
            consts.DELIMITER_COMMA) if conf.MAB_RTK_CONTEXTUAL_SCENARIOS in config["parameters"] else None,

        #axis_pre,
        #axis_post,  # if not is_single_axis else axis_pre,
        #reward_config,

        extract_iterable_params_from_config(config),
        [],
        config["output"]["run-duplicates"],
        config.getint("experiment", "max-parallel-execution"),
        config["parameters"]["seeds"].replace(' ', '').split(consts.DELIMITER_COMMA),
        config["parameters"]["specfiles"].replace(' ', '').split(consts.DELIMITER_COMMA) if 'specfiles' in config[
            "parameters"] else ["../../spec"],
        config["parameters"][conf.EXPIRATION_TIMEOUT].replace(' ', '').split(consts.DELIMITER_COMMA) if EXPIRATION_TIMEOUT in
                                                                                                        config[
                                                                                                       "parameters"] else [
            consts.DEFAULT_EXPIRATION_TIMEOUT],
        config["output"]["persist"].replace(' ', '').split(consts.DELIMITER_COMMA) if 'persist' in config[
            "output"] else "",
    )
    return exp
