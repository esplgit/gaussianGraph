# %%
# from numpy import random
# import matplotlib.pyplot as plt
# import seaborn as sns

# sns.distplot(random.normal(size=1000), hist=False)

# plt.show()

# fig, ax = plt.subplots()  # Create a figure containing a single axes.
# ax.plot([1, 2, 3, 4], [1, 4, 2, 3])  # Plot some data on the axes.

# %%
import matplotlib.pylab as plt
import numpy as np

# %% 
plt.figure()
plt.plot(np.sin(np.linspace(-np.pi, np.pi, 1001)))
plt.show()