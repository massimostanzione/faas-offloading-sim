import os
import subprocess

import conf
from mab_automated_experiments._api.expgen import build_experiment_from_config
from mab_automated_experiments._internal import consts
from mab_automated_experiments._internal.consts import get_expconf_path, METASIM_DIR


def run():
    print("Starting MAB Automated experiment...")

    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.abspath(os.path.join(METASIM_DIR, '..'))

    # execute all the esperiments according to the pipeline file
    with open(consts.PIPELINE_FILE, "r") as pipeline_file:
        for experiment_name in pipeline_file:
            print("> Starting experiment", experiment_name)
            experiment_confpath = get_expconf_path(experiment_name)

            if os.path.exists(experiment_confpath):
                with open(experiment_confpath, "r") as expconf_file:
                    config = conf.parse_config_file(experiment_confpath)

                    if 'experiment' in config and 'mode-preprocessing' in config['experiment']:
                        mode_preprocessing = config['experiment']['mode-preprocessing']
                    else:
                        mode_preprocessing = consts.ExecMode.NONE.value

                    mode_simulations_expconf = config["experiment"]["mode-simulations"]

                    if 'experiment' in config and 'mode-postprocessing' in config['experiment']:
                        mode_postprocessing = config['experiment']['mode-postprocessing']
                    else:
                        mode_postprocessing = consts.ExecMode.NONE.value
                    # =========================================================
                    # 1. Pre-processing
                    # ---------------------------------------------------------
                    print()
                    print("=============================")
                    print("| P r e p r o c e s s i n g |")
                    print("+---------------------------+")
                    if mode_preprocessing == consts.ExecMode.NONE.value:
                        print("Preprocessing skipped")

                    elif mode_preprocessing == consts.ExecMode.AUTOMATED.value:
                        print("No automated preprocessing defined")

                    else:
                        name = config["experiment"]["name"]
                        # os.system("python3 " + os.path.join(METASIM_DIR, name, mode_preprocessing))

                        # Costruisci il comando da eseguire
                        command = ['python3', os.path.join(METASIM_DIR, name, mode_preprocessing)]

                        # Esegui il comando con il nuovo ambiente
                        try:
                            subprocess.run(command, check=True, env=env)
                        except subprocess.CalledProcessError as e:
                            print(f"Errore durante l'esecuzione del sottoprocesso: {e}")

                    # =========================================================
                    # 2. Simulations
                    # ---------------------------------------------------------

                    print()
                    print("=========================")
                    print("| S i m u l a t i o n s |")
                    print("+-----------------------+")
                    if mode_simulations_expconf == consts.ExecMode.NONE.value:
                        print(f"Simulations skipped (as specified in {consts.EXPCONF_FILE})")

                    elif mode_simulations_expconf == consts.ExecMode.AUTOMATED.value:
                        exp = build_experiment_from_config(config)
                        exp.run()

                    else:
                        name = config["experiment"]["name"]
                        print()
                        print("============================================")
                        print(f"Running experiment \"{name}\"")
                        print(f"with custom simulations")
                        print("--------------------------------------------")
                        os.system("python3 " + os.path.join(METASIM_DIR, name, mode_simulations_expconf))

                    # =========================================================
                    # 3. Post-processing
                    # ---------------------------------------------------------

                    print()
                    print("===============================")
                    print("| P o s t p r o c e s s i n g |")
                    print("+-----------------------------+")
                    if mode_postprocessing == consts.ExecMode.NONE.value:
                        print("Postprocessing skipped")

                    elif mode_postprocessing == consts.ExecMode.AUTOMATED.value:
                        print("No automated postprocessing defined")

                    else:
                        name = config["experiment"]["name"]
                        command = ['python3', os.path.join(METASIM_DIR, name, mode_postprocessing)]

                        try:
                            subprocess.run(command, check=True, env=env)
                        except subprocess.CalledProcessError as e:
                            print(f"Errore durante l'esecuzione del sottoprocesso: {e}")
            else:
                raise RuntimeError(f"Expconf INI file not found for experiment {experiment_name}")
    print("Done, bye.")
