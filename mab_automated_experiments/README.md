# mab-automated-experiments
This directory contains some tools to run (semi-) automated experiments
(_i.e._, series of simulations appropriately driven according to specific parameters) with MAB.

In order to create and run an experiment:
1. clone the `_archetype` directory
2. fill the `expconf.ini` file with the desired parameters, according to the instructions contained therein
3. add the experiment name in a new line of `PIPELINE`
4. go back to the `faas-offloading-sim`
4. run `python3 autorun.py`