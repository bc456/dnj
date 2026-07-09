# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns
import statsmodels.nonparametric.api as smnp
import os, sys

# ================= 配置部分 =================
INPUT_EXCEL = 'ks.xlsx'  # 输入的模板文件
OUTPUT_EXCEL = 'ks_filled.xlsx'  # 输出的结果文件 (建议另存，防止把原文件搞坏)

# 全局列表，用于存储计算结果
results_data = []

# Matplotlib 设置
plt.rcParams.update({'figure.max_open_warning': 0})  # 防止打开太多图报警
large = 32;
med = 20;
small = 12
params = {'axes.titlesize': large, 'legend.fontsize': med, 'figure.figsize': (16, 10),
          'axes.labelsize': med, 'xtick.labelsize': med, 'ytick.labelsize': med,
          'figure.titlesize': large}
plt.rcParams.update(params)
plt.style.use('seaborn-whitegrid')
sns.set_style("white")
plt.rcParams['axes.unicode_minus'] = False


# ================= 工具函数 =================

def kde_test(data, kernel, bw, gridsize, cut):
    fft = kernel == "gau"
    kde = smnp.KDEUnivariate(data)
    kde.fit(kernel, bw, fft, gridsize=gridsize, cut=cut)
    return kde.support, kde.density


def strToFloat(number):
    try:
        return float(number)
    except:
        return -2.0


def kde_point(data, kernel, bw, gridsize, cut):
    _x, _y = kde_test(data, "gau", "scott", gridsize=100, cut=3)
    point = np.where(_y == np.max(_y))
    return _x[point]


def norm_comparision_plot(data, filename, peak_value, figsize=(12, 8), surround=True, grid=False):
    plt.figure(figsize=figsize)
    sns.distplot(data, bins=50, hist=True, kde=True)

    # 标题格式: Leaf1Leaf2[PeakValue]
    title_str = filename.split(".")[0] + filename.split(".")[1] + "[" + str(peak_value) + "]"
    plt.title(title_str, fontdict={'weight': 'normal', 'size': 40})

    if surround:
        sns.despine(trim=True, left=True, offset=5)
    if grid:
        plt.grid(True)


def ks_kde(filename, maxks):
    ksdata = []
    try:
        with open("ks/" + filename, 'r') as f:
            for line in f.readlines():
                array = line.split('\t')
                if len(array) > 3:
                    val = strToFloat(array[3])
                    if 0 <= val < maxks:
                        ksdata.append(val)
    except Exception as e:
        print(f"Error reading file {filename}: {e}")
        return

    if len(ksdata) == 0:
        return

    peak_array = kde_point(ksdata, "gau", "scott", gridsize=100, cut=3)
    if len(peak_array) > 0:
        peak_value = float(peak_array[0])
    else:
        peak_value = 0.0

    # 提取物种名
    leaf1 = filename.split(".")[0]
    leaf2 = filename.split(".")[1]

    # 将结果存入列表，稍后统一填入表格
    results_data.append({
        'Leaf1': leaf1,
        'Leaf2': leaf2,
        'Peak': peak_value
    })

    norm_comparision_plot(data=ksdata, filename=filename, peak_value=peak_value)
    plt.savefig("ks/" + filename + ".svg")
    plt.cla()
    plt.close("all")


# ================= 主程序执行 =================

# 1. 检查输入表格是否存在
if not os.path.exists(INPUT_EXCEL):
    print(f"Error: {INPUT_EXCEL} not found! Please check file name.")
    sys.exit()

print(f"Loading template matrix: {INPUT_EXCEL} ...")
try:
    # index_col=0 意味着第一列是行名（Row Headers）
    df_matrix = pd.read_excel(INPUT_EXCEL, index_col=0)
    print("Template loaded successfully.")
except Exception as e:
    print(f"Error loading Excel: {e}")
    sys.exit()

print("Start processing ks files...")

# 2. 遍历处理文件
for i, j, k in os.walk('ks'):
    for file in k:
        if file.endswith('.besthit.ks'):
            print(f"Processing: {file}")
            mk = 1.5
            if file.split(".")[0] == file.split(".")[1]:
                mk = 3
            ks_kde(file, mk)

print("Processing finished. Filling data into the matrix...")

# ================= 填入数据到表格 =================

fill_count = 0
error_count = 0

for item in results_data:
    row_name = item['Leaf1']
    col_name = item['Leaf2']
    val = item['Peak']

    # 检查 行名 和 列名 是否都在 Excel 表格中
    if row_name in df_matrix.index and col_name in df_matrix.columns:
        # 使用 at 定位并赋值
        df_matrix.at[row_name, col_name] = val
        fill_count += 1
    else:
        # 尝试反向查找 (因为矩阵可能是对称的，或者文件名顺序与表格相反)
        if col_name in df_matrix.index and row_name in df_matrix.columns:
            df_matrix.at[col_name, row_name] = val
            fill_count += 1
            print(f"Info: Swapped axes for {row_name}-{col_name}")
        else:
            print(f"Warning: {row_name} or {col_name} not found in Excel headers. Skipping.")
            error_count += 1

# 3. 保存结果
print(f"\nSummary: Filled {fill_count} cells. Skipped {error_count} items.")

try:
    df_matrix.to_excel(OUTPUT_EXCEL)
    print(f"Success! Result saved to '{OUTPUT_EXCEL}'.")
    # 打印预览
    print(df_matrix.iloc[:5, :5])
except Exception as e:
    print(f"Error saving file: {e}")