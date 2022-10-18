import math
import numpy as np
import matplotlib.pyplot as plt

def create_cdf (Z):
    N = len(Z)
    X2 = np.sort(Z)
    F2 = np.array(range(N))/float(N)

    return X2,F2

def plot_rt_cdf (samples):
    columns = 2
    rows = int(math.ceil(len(samples) / columns))
    fig, axs = plt.subplots(rows, columns, sharex=True)


    for fc,axis in zip(samples, axs):
        f,c=fc
        x,y = create_cdf(samples[(f,c)])

        axis.set_title(f"{f} - {c}")
        axis.plot(x, y)
    plt.show()
