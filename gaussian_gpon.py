"""
    Code by Tae-Hwan Hung(@graykode)
    https://en.wikipedia.org/wiki/Normal_distribution
"""
import numpy as np
from matplotlib import pyplot as plt


class Gaussian(object):
    def __init__(self, *args, **kwargs):
        pass

    def gaussian(self, x, n):
        u = x.mean()
        s = x.std()

        # divide [x.min(), x.max()] by n
        x = np.linspace(x.min(), x.max(), n)

        a = ((x - u) ** 2) / (2 * (s ** 2))
        y = 1 / (s * np.sqrt(2 * np.pi)) * np.exp(-a)

        return x, y, x.mean(), x.std()

    def gaussian_main(self):
        x = np.arange(-100, 100)  # define range of x
        x, y, u, s = self.gaussian(x, 10000)

        plt.plot(x, y, label=r'$\mu=%.2f,\ \sigma=%.2f$' % (u, s))
        plt.legend()
        plt.savefig('graph/gaussian.png')
        plt.show()


if __name__ == '__main__':
    gs = Gaussian()
    gs.gaussian_main()
