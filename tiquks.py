import os
import pandas as pd


def extract_ks_to_excel():
    # 定义输入文件的根路径（使用原始字符串避免转义问题）
    input_dir = r"90的\三次\evolution_duoxulie\rate_0.2\ks"

    # 检查输入路径是否存在
    if not os.path.exists(input_dir):
        print(f"错误：输入路径不存在 -> {input_dir}")
        return

    # 用于存储提取到的数据: [(SpeciesA, SpeciesB, value), ...]
    extracted_data = []
    # 用于存储所有出现过的物种名称，以便生成表格的行和列
    all_species = set()

    print("开始扫描文件...")

    # 遍历指定路径下的所有文件
    files = os.listdir(input_dir)
    for filename in files:
        # 简单过滤：只处理以 .ks 结尾的文件
        if not filename.endswith('.ks'):
            continue

        # 2. 解析文件名获取物种名称
        # 假设文件名格式为: SpeciesA.SpeciesB.besthit.ks
        try:
            parts = filename.split('.')
            if len(parts) < 2:
                print(f"跳过格式不匹配的文件: {filename}")
                continue

            spec1 = parts[0]
            spec2 = parts[1]

            # 将物种名加入集合
            all_species.add(spec1)
            all_species.add(spec2)

        except Exception as e:
            print(f"解析文件名出错 {filename}: {e}")
            continue

        # 3. 读取文件内容提取数值（拼接完整文件路径）
        file_path = os.path.join(input_dir, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

                # 检查是否有第二行 (索引为1)
                if len(lines) < 2:
                    print(f"文件行数不足: {filename}")
                    continue

                # 获取第二行并按空格分割
                target_line = lines[1].strip()
                columns = target_line.split()

                # 检查是否有第四列 (索引为3)
                if len(columns) < 4:
                    print(f"第二行缺少第四列数据: {filename}")
                    continue

                # 提取数值
                ks_value = float(columns[3])

                # 存入列表
                extracted_data.append((spec1, spec2, ks_value))

        except ValueError:
            print(f"数据格式错误 (无法转换为数字): {filename}")
        except Exception as e:
            print(f"读取文件出错 {filename}: {e}")

    # 4. 构建 DataFrame (矩阵表格)
    # 将物种名排序，保证表格行列顺序一致
    sorted_species = sorted(list(all_species))

    # 创建一个全为 0 的矩阵
    df = pd.DataFrame(0.0, index=sorted_species, columns=sorted_species)

    # 5. 填充数据
    for sp1, sp2, val in extracted_data:
        # 填充对应的位置
        if sp1 in df.index and sp2 in df.columns:
            df.at[sp1, sp2] = val

        # 因为是对称矩阵，交换位置也要填 (Leaf2 vs Leaf1)
        if sp2 in df.index and sp1 in df.columns:
            df.at[sp2, sp1] = val

    # 6. 定义输出文件路径（保存在指定输入路径下）
    output_filename = os.path.join(input_dir, 'ks.xlsx')
    try:
        df.to_excel(output_filename)
        print(f"\n成功! 表格已生成: {output_filename}")
        print(f"共处理了 {len(extracted_data)} 个有效文件。")
    except PermissionError:
        print(f"\n错误: 无法写入 {output_filename}。请检查文件是否已在 Excel 中打开。")
    except Exception as e:
        print(f"\n保存文件出错: {e}")


if __name__ == "__main__":
    extract_ks_to_excel()