import os

import conf
from _internal import consts
from _api.expgen import build_experiment_from_config


if __name__ == "__main__":
    # execute all the esperiments according to the pipeline file
    with open(consts.PIPELINE_FILE, "r") as pipeline_file:
        for experiment_name in pipeline_file:
            experiment_confpath = os.path.join(experiment_name.strip(), consts.EXPCONF_FILE)

            if os.path.exists(experiment_confpath):
                with open(experiment_confpath, "r") as expconf_file:
                    config = conf.parse_config_file(experiment_confpath)

                    if 'experiment' in config and 'mode-preprocessing' in config['experiment']:
                        mode_preprocessing = config['experiment']['mode-preprocessing']
                    else:
                        mode_preprocessing=consts.ExecMode.NONE.value

                    mode_simulations_expconf = config["experiment"]["mode-simulations"]

                    if 'experiment' in config and 'mode-postprocessing' in config['experiment']:
                        mode_postprocessing = config['experiment']['mode-postprocessing']
                    else:
                        mode_postprocessing=consts.ExecMode.NONE.value
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
                        exp=build_experiment_from_config(config)
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
