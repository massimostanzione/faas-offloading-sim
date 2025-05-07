import numpy as np
import scipy.stats as stats
import math

def generate():
    iat_times=100000

    mu = 0
    variance = 0.2
    sigma = math.sqrt(variance)
    x = np.linspace(mu - 3*sigma, mu + 3*sigma, iat_times)
    xinv=(1-stats.norm.pdf(x, mu, sigma))
    #plt.plot(x, stats.norm.pdf(x, mu, sigma))
    #plt.show()

    with open("trace-f1gauss.iat", "w") as file:
        for val in xinv:
            file.write(str(val))
            file.write("\n")

    with open("trace-f1linear.iat", "w") as file:
        for i in np.arange(iat_times/2, 0, -1):
            file.write(str(i/(iat_times/2)))
            file.write("\n")
        for i in np.arange(1, iat_times/2, 1):
            file.write(str(i/(iat_times/2)))
            file.write("\n")

if __name__=="__main__": generate()