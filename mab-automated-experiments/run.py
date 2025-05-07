import os

import conf
from _internal import consts
from _internal.experiment import MABExperiment, extract_iterable_params_from_config

if __name__ == "__main__":
    # execute all the esperiments according to the pipeline file
    with open(consts.PIPELINE_FILE, "r") as pipeline_file:
        for experiment_name in pipeline_file:
            experiment_confpath = os.path.join(experiment_name.strip(), consts.EXPCONF_FILE)

            if os.path.exists(experiment_confpath):
                with open(experiment_confpath, "r") as expconf_file:
                    config = conf.parse_config_file(experiment_confpath)

                    mode_preprocessing = config["experiment"]["mode-preprocessing"]
                    mode_simulations_expconf = config["experiment"]["mode-simulations"]
                    mode_postprocessing = config["experiment"]["mode-postprocessing"]

                    # =========================================================
                    # 1. Pre-processing
                    # ---------------------------------------------------------

                    if mode_preprocessing == consts.ExecMode.NONE.value:
                        print("Preprocessing skipped")

                    elif mode_preprocessing == consts.ExecMode.AUTOMATED.value:
                        print("No automated preprocessing defined")

                    else:
                        name = config["experiment"]["name"]
                        os.system("python3 " + os.path.join(name, mode_preprocessing))

                    # =========================================================
                    # 2. Simulations
                    # ---------------------------------------------------------

                    if mode_simulations_expconf == consts.ExecMode.NONE.value:
                        print(f"Simulations skipped (as specified in {consts.EXPCONF_FILE})")

                    elif mode_simulations_expconf == consts.ExecMode.AUTOMATED.value:
                        # TODO questa parte è in api
                        axis_pre = config["reward_fn"]["axis_pre"].replace(' ', '').split(consts.DELIMITER_COMMA)
                        axis_post = config["reward_fn"]["axis_post"].replace(' ', '').split(consts.DELIMITER_COMMA)
                        is_single_axis = axis_post == ['']
                        exp = MABExperiment(
                            config,
                            config["experiment"]["name"],
                            config["strategies"]["strategies"].replace(' ', '').split(consts.DELIMITER_COMMA),
                            config["experiment"]["close-door-time"],
                            config["experiment"]["mab-update-interval"],
                            axis_pre,
                            axis_post, # if not is_single_axis else axis_pre,
                            extract_iterable_params_from_config(config),
                            [],
                            config["output"]["run-duplicates"],
                            config.getint("experiment", "max-parallel-execution"),
                            config["parameters"]["seeds"].replace(' ', '').split(consts.DELIMITER_COMMA),
                            config["parameters"]["specfiles"].replace(' ', '').split(consts.DELIMITER_COMMA),
                            config["output"]["persist"].replace(' ', '').split(consts.DELIMITER_COMMA)
                        )
                        exp.run()

                    else:
                        name = config["experiment"]["name"]
                        print()
                        print("============================================")
                        print(f"Running experiment \"{name}\"")
                        print(f"with custom simulations")
                        print("--------------------------------------------")
                        os.system("python3 " + os.path.join(name, mode_simulations_expconf))

                    # =========================================================
                    # 3. Post-processing
                    # ---------------------------------------------------------

                    if mode_postprocessing == consts.ExecMode.NONE.value:
                        print("Postprocessing skipped")

                    elif mode_postprocessing == consts.ExecMode.AUTOMATED.value:
                        print("No automated postprocessing defined")

                    else:
                        name = config["experiment"]["name"]
                        os.system("python3 " + os.path.join(name, mode_postprocessing))
