import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

INPUT="results_edge_memory.csv"

df = pd.read_csv(INPUT)

fig, (ax1, ax2) = plt.subplots(2, 1)
width = 0.2

ax1.set_ylabel('Utility')
ax2.set_ylabel('Cost')

policies = df.Policy.unique()
memory_confs = [str(m) for m in df.Memory.unique()]
m = np.arange(len(memory_confs))

for i,policy in enumerate(policies):
    _df = df[df.Policy == policy] 
    ax1.bar(m + (-len(policies)/2+i)*width, _df.UtilityMean, width, yerr=_df.UtilityStd, label=policy)
    ax2.bar(m + (-len(policies)/2+i)*width, _df.CostMean, width, yerr=_df.CostStd)

ax1.set_xticks(m, memory_confs)
ax2.set_xticks(m, memory_confs)

#ax1.set_yscale("log")
#ax2.set_yscale("log")

ax1.legend(loc="lower left")


plt.show()
