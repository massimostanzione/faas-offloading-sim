import matplotlib.pyplot as plt
import pandas as pd

INPUT="results_policies.csv"

df = pd.read_csv(INPUT)
print(df)


policies = df.Policy

fig, (ax1, ax2) = plt.subplots(2, 1)


ax1.set_ylabel('Utility')
ax1.bar(policies, df.UtilityMean, yerr=df.UtilityStd)
ax2.set_ylabel('Cost')
ax2.bar(policies, df.CostMean, yerr=df.CostStd)

plt.show()
