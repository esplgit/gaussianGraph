# %%
from numpy import random
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme()
df = sns.load_dataset("penguins")
# sns.distplot (random.normal(size=1000), hist=False)

sns.histplot(
    df["flipper_length_mm"], kde=True,
    stat="density", kde_kws=dict(cut=3),
    alpha=.4, edgecolor=(1, 1, 1, .4),
)
plt.show()

# fig, ax = plt.subplots()  # Create a figure containing a single axes.
# ax.plot([1, 2, 3, 4], [1, 4, 2, 3])  # Plot some data on the axes.

# %%
import matplotlib.pylab as plt
import numpy as np

# # %%
# plt.figure()
# plt.plot(np.sin(np.linspace(-np.pi, np.pi, 1001)))
# plt.show()
