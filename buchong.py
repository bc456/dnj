import pandas as pd
import numpy as np
import os

def symmetrize_matrix_with_diag_protection(matrix):
    """
    核心功能：矩阵对称化 + 仅非对角线空白填0（对角线空白保留）
    参数: matrix - 输入的numpy矩阵（从Excel读取的数据）
    返回: processed_matrix - 处理后的矩阵
    """
    # 步骤1：先处理非方阵（自动截取为最小维度的方阵，避免对称化报错）
    rows, cols = matrix.shape
    if rows != cols:
        min_dim = min(rows, cols)
        matrix = matrix[:min_dim, :min_dim]
        print(f"⚠️  检测到非方阵（{rows}行×{cols}列），已截取为{min_dim}×{min_dim}方阵")
    rows, cols = matrix.shape  # 更新为方阵维度

    # 步骤2：矩阵对称化（下三角复制上三角的值，覆盖原下三角空白）
    symmetric_matrix = matrix.copy()
    for i in range(rows):
        for j in range(i + 1, cols):  # 仅处理上三角区域（j > i，避免重复处理对角线）
            if not pd.isna(symmetric_matrix[i, j]):  # 上三角有值时，下三角同步
                symmetric_matrix[j, i] = symmetric_matrix[i, j]

    # 步骤3：定向填0（仅非对角线的空白处填0，对角线空白保留）
    processed_matrix = symmetric_matrix.copy()
    for i in range(rows):
        for j in range(cols):
            # 条件：非对角线（i≠j）且当前为空白（NaN）
            if i != j and pd.isna(processed_matrix[i, j]):
                processed_matrix[i, j] = 0

    return processed_matrix

def process_excel_file(input_path, output_path=None):
    """
    完整流程：读取Excel → 矩阵处理 → 保存结果
    参数: input_path - 原始Excel文件路径；output_path - 结果保存路径（默认自动生成）
    """
    # 自动生成输出路径（避免覆盖原始文件）
    if output_path is None:
        file_dir, file_name = os.path.split(input_path)
        file_base = os.path.splitext(file_name)[0]
        output_path = os.path.join(file_dir, f"{file_base}_processed.xlsx")

    try:
        # 读取Excel（不使用表头，适配纯矩阵数据；自动兼容.xlsx/.xls格式）
        print(f"📂 正在读取文件：{input_path}")
        try:
            df_raw = pd.read_excel(input_path, header=None, engine='openpyxl')  # 优先.xlsx
        except:
            df_raw = pd.read_excel(input_path, header=None, engine='xlrd')  # 兼容.xls

        # 显示原始数据信息
        print(f"✅ 原始数据尺寸：{df_raw.shape}")
        print("\n🔍 原始数据预览（前5行5列，NaN代表空白）：")
        print(df_raw.iloc[:5, :5].fillna("空白"))  # 替换NaN为“空白”便于查看

        # 执行核心处理（对称化 + 定向填0）
        print("\n⚙️  开始矩阵处理（对称化+非对角线空白填0）...")
        matrix_raw = df_raw.values  # 转为numpy矩阵
        matrix_processed = symmetrize_matrix_with_diag_protection(matrix_raw)

        # 转换为DataFrame并保存
        df_processed = pd.DataFrame(matrix_processed)
        df_processed.to_excel(output_path, index=False, header=False, engine='openpyxl')

        # 显示处理结果
        print(f"✅ 处理完成！结果已保存至：{output_path}")
        print("\n🔍 处理后数据预览（前5行5列，对角线空白保留）：")
        print(df_processed.iloc[:5, :5].fillna("空白"))  # 替换NaN为“空白”便于查看

        return output_path

    except Exception as e:
        print(f"❌ 处理失败：{str(e)}")
        print("💡 请检查：1. 文件路径是否正确 2. Excel是否为纯矩阵格式（无多余表头）")

# ------------------- 执行入口（修改文件路径即可运行） -------------------
if __name__ == "__main__":
    # 请替换为你的ks_filled.xlsx实际路径（示例路径需根据系统调整）
    # Windows示例：input_file = "C:\\Users\\你的名字\\桌面\\ks_filled.xlsx"
    # Mac/Linux示例：input_file = "/Users/你的名字/Desktop/ks_filled.xlsx"
    input_file = "ks_filled.xlsx"  # 若文件与代码在同一文件夹，直接用此句

    # 启动处理
    process_excel_file(input_file)