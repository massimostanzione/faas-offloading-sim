import json
import os
import sys
from datetime import datetime


import matplotlib.pyplot as plt

import conf
from conf import MAB_UCB_EXPLORATION_FACTOR, MAB_UCB2_ALPHA

timestamp = datetime.now().replace(microsecond=0)

graphs_ctr=-1
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from _internal import consts

EXPNAME = "bayesopt-params-tuning"
EXPCONF_PATH = os.path.join(EXPNAME, consts.EXPCONF_FILE)
expconfig = conf.parse_config_file(EXPCONF_PATH)

axis_pre = expconfig["reward_fn"]["axis_pre"].split(consts.DELIMITER_COMMA)
axis_post = expconfig["reward_fn"]["axis_post"].split(consts.DELIMITER_COMMA)
strategies = expconfig["strategies"]["strategies"].split(consts.DELIMITER_COMMA)

output_seed="123"

with open(EXPNAME+"/results/output.json", 'r') as f:
    data = json.load(f)
plots = {
    "stat":{
    "ef":[], "alpha":[]
}
}

for item in consts.RewardFnAxis:
    val = item.value
    plots[val]={
    "ef":[], "alpha":[]
    }
xstat=[]
ystat=[]
xnstat=[]
ynstat=[]

for entry in data:
    strategy = entry["strategy"]
    ax_pre = entry["axis_pre"]
    ax_post = entry["axis_post"]
    seed = entry["seed"]
    parameters = entry["parameters"]
    if seed==output_seed and strategy=="UCB2":
        if ax_pre==ax_post:
            plots["stat"]["ef"].append(parameters["ef"])
            plots["stat"]["alpha"].append(parameters["alpha"])

        else:

            for item in consts.RewardFnAxis:
                val=item.value
                if ax_post==val:
                    plots[val]["ef"].append(parameters["ef"])
                    plots[val]["alpha"].append(parameters["alpha"])

print(plots)
plt.scatter(plots["stat"]["ef"], plots["stat"]["alpha"], label="strategy", marker="s")

for item in consts.RewardFnAxis:
    val = item.value
    plt.scatter(plots[val]["ef"], plots[val]["alpha"], label=val)

plt.xlabel('ef')
plt.ylabel('alpha')
plt.title('Punti per ogni strategia')


plt.legend()
graphs_ctr+=1
plt.savefig(os.path.join(SCRIPT_DIR, "results",
                                         consts.DELIMITER_HYPHEN.join([str(timestamp), str(graphs_ctr)]).replace(' ',
                                                                                                                 consts.DELIMITER_HYPHEN) + consts.SUFFIX_GRAPHFILE))
plt.clf()