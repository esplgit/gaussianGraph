# #Library
# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# import scipy.stats as stats

# #Generating data frame
# x = np.random.normal(50, 3, 1000)
# source = {"Genotype": ["CV1"]*1000, "AGW": x}
# df = pd.DataFrame(source)
#
# # Calculating mean and Stdev of AGW
# df_mean = np.mean(df["AGW"])
# df_std = np.std(df["AGW"])
#
# # Calculating probability density function (PDF)
# pdf = stats.norm.pdf(df["AGW"].sort_values(), df_mean, df_std)
#
# # Drawing a graph
# plt.plot(df["AGW"].sort_values(), pdf)
# plt.xlim([30,70])
# plt.xlabel("Grain weight (mg)", size=12)
# plt.ylabel("Frequency", size=12)
# plt.grid(True, alpha=0.3, linestyle="--")
# plt.show()

import matplotlib.pyplot as plt
plt.plot([1, 2, 3, 4])
plt.ylabel('some numbers')
plt.show()
