import numpy as np
from scipy.stats import norm
import matplotlib.pyplot as plt
import glob
import csv
import  operator
import  traceback
from utils import jsonfile_load

"""
0/1/0,  1,  -14.88
0/1/0,  1,  -14.86
0/1/0,  1  -14.86
0/1/0,  1  -14.86
0/1/0  1  -14.86
0/1/0  1  -14.86
...
0/1/0  11  -14.88
0/1/0  11  -14.86
0/1/0  11  -14.86
0/1/0  11  -14.86
0/1/0  11  -14.86
0/1/0  11  -14.86

1. read all the json files in the files
2. get the value of RX
3. generate a list 
4. write ithe list nto a file onts.csv
5  use the list as follow
for ont in onts:
    generate gaussian graph for all ONTs
    save to graph directory
"""
ont_list_header = ['port', 'ont', 'date', 'rx']
path = 'files/'
json_files = glob.glob(path + 'olts20*.json')
# load the json file
ont_list = []
ont_temp = []
aerage_value_list = []

output_lines = []
date_list = []

for f in json_files:
    # olt = []
    try:
        ontjson = jsonfile_load(f)
    except:
        continue
    try:
        olts = ontjson['olt']
    except:
        continue

    olt_ont_list = []
    average_list = []

    output_lines_header = ['datetime,port,ontid,rx, count']  # the csv line with header
    output_lines = []
    average_value = []
    onts0 = olts[0].get('ont')
    onts0 = [x for x in onts0 if x.get('status') == 'online']
    onts1 = olts[1].get('ont')
    onts1 = [x for x in onts1 if x.get('status') == 'online']
    onts = onts0 + onts1

    """
    # 1. the first time parsing: normalize the datetime field
    # 2. calculate the average value
    # 3. the 3nd parsing will generate output of rx gaussian graphs
    """

    for ont in onts:
        assert float(ont.get('rx'))
        # rx = ont.get('rx')
        date = ont['datetime'].split(' ')[0]
        if date not in date_list:
            ont['datetime'] = date
            date_list.append(date)
            output_lines.append((date, ont.get('port'), ont.get('ind'), ont.get('rx'), 1))
        else:
            # find the line in output_lines with the same date
            for line in output_lines:
                if line[0] == date:
                    va = line[3]
                    rx = ont.get('rx')
                    cnt = ont.get('count')
                    va += rx
                    line = (date, ont.get('port'), ont.get('ind'), va, cnt)
                    break
            index = date_list.index(ont)
            item = on(index)
            value = item[3]
            value += ont.get('rx')

        ont['datetime'] = date  # normalize datetime

    for ont in onts:
        date = ont.date.get('datetime')
        if ont.get('date') not in date_list:
            date_list.append(date)


        # get the all the ont with the same date
        # output_onts.append({"date":ont})

            #
            # average_value.append([date, ont['rx']])
            # onts.append([ont['port'], ont['id']])

    if len(onts) > 0:
        olt_ont_list.append(onts)
        average_list.append(average_value)
    ont_list.append(olt_ont_list)
    aerage_value_list.append(average_list)

aerage_value_list.sort()
total_avg_date_list = []
for dt in date_list:
    value = 0
    avg_date_list = []
    for avglt in aerage_value_list:
        for avg in avglt:
            for av in avg:
                if av[0] == dt:
                    value += av[1]
                    avg_date_list.append(av)
    avg_val = 0
    if value :
        avg_val = value/len(avg_date_list)
    total_avg_date_list.append([dt, avg_val])
# if find valid one ont_list.apeend(ont)
all_ont_list =[]
if len(ont_list) > 0:
    for olt in ont_list:
        for onts in olt:
            for ont in onts:
                all_ont_list.append(ont)
# analysis the ontjson to get the fsp and ontid and rx value
# fsp, ontid, rx
all_ont_list.sort()
with open('onts.csv', 'w') as csvfile:
    csvwriter = csv.writer(csvfile, delimiter=',')
    csvwriter.writerow(ont_list_header)
    # 00   0 0cs0vwriter.writerows(all_ont_list, total_avg_date_list)
    all_ont_lists = []
    for i, j in zip( all_ont_list, total_avg_date_list):
        i.extend(j)
        all_ont_lists.append(i)
    for ontlt in range(len(all_ont_lists), len(all_ont_list)):
        all_ont_lists.append(all_ont_list[ontlt])
    csv_output_list = []
    for cdata in all_ont_lists:
        if len(cdata) >=4:
            csv_output_list.append(cdata)
    for row in sorted(csv_output_list, key=operator.itemgetter(2)):
        csvwriter.writerow(row)

# Generate some data for this demonstration.
# print(all_ont_lists)
# data = []
# for all in all_ont_lists:
#     if '0/1/0' in all and '1' in all:
#         if len(all) >= 4:
#             data.append(all[3])
# jsonobj = jsonfile_load(())
#
# data = np.random.normal(170, 10, 250)
#[170,180,190,200,.....]
# out data is [-17.04, -16.65,-17.00]
data = []
port = ''
ont=''
with open("onts.csv", 'r') as file:
    csvreader = csv.reader(file)
    header = next(csvreader)
    for row in csvreader:
        if len(row) >= 4:
            port = row[0]
            ont = row[1]
            val = "{:.2f}".format(float(row[3]))
            data.append(val)
data = np.array(data, dtype=float)
# Fit a normal distribution to
# the data:
# mean and standard deviation
mu, std = norm.fit(data)


# Plot the histogram.
plt.hist(data, bins=25, density=True, alpha=0.6, color='b')

# Plot the PDF.
xmin, xmax = plt.xlim()
x = np.linspace(xmin, xmax, 100)
p = norm.pdf(x, mu, std)

plt.plot(x, p, 'k', linewidth=2)
# title = "Fit Values: {:.2f} and {:.2f}".format(mu, std)
title = "port={}, ont={} (\u03BC= {:.2f}, \u03C3= {:.2f})".format(port,ont,mu, std)
plt.title(title)

plt.show()
