import os
import re


def get_ids_from_cds(filepath):
    """
    从CDS文件中提取序列ID（去掉>号）。
    注意：这里的参数改为了 filepath，接收完整的文件路径。
    """
    ids = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    ids.append(line[1:])
    except Exception as e:
        print(f"读取文件 {filepath} 时出错: {e}")
    return ids


def natural_sort_key(s):
    """
    实现自然排序的关键函数。
    将字符串分解为数字和非数字部分，例如 'Leaf10' -> ['Leaf', 10]
    这样 'Leaf2' -> ['Leaf', 2] 就会排在 'Leaf10' 前面。
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]


def main():
    # 【修改点1】定义目标文件夹路径 (使用 os.path.join 保证跨平台兼容性)
    target_dir = os.path.join("30（补）", "四次", "evolution_duoxulie", "rate_0.2", "leaf_cds_files")

    # 检查目录是否存在，防止报错
    if not os.path.exists(target_dir):
        print(f"错误：找不到指定的目录 '{target_dir}'。请确认该文件夹是否存在于当前目录下。")
        return

    # 【修改点2】检索目标目录下所有的 .cds 文件
    cds_files = [f for f in os.listdir(target_dir) if f.endswith('.cds')]

    # 使用自然排序
    cds_files.sort(key=natural_sort_key)

    file_count = len(cds_files)
    if file_count < 2:
        print(f"错误：目录 '{target_dir}' 下 .cds 文件少于2个，无法进行配对。")
        return

    print(f"在 '{target_dir}' 中找到 {file_count} 个CDS文件 (已按自然序排列)，开始生成配对文件...")
    print(f"文件处理顺序: {cds_files}")
    print("-" * 30)

    # 双重循环实现“不放回”的两两组合
    for i in range(file_count):
        for j in range(i + 1, file_count):
            file1_name = cds_files[i]
            file2_name = cds_files[j]

            # 【修改点3】拼接完整的文件路径用于读取
            file1_path = os.path.join(target_dir, file1_name)
            file2_path = os.path.join(target_dir, file2_name)

            stem1 = os.path.splitext(file1_name)[0]
            stem2 = os.path.splitext(file2_name)[0]

            # 输出的 .pairs 文件名。
            # 注：这里会默认生成在运行该脚本的“当前目录”。
            output_filename = os.path.join(target_dir, f"{stem1}.{stem2}.pairs")

            # 提取两个文件中的ID (传入完整路径)
            ids1 = get_ids_from_cds(file1_path)
            ids2 = get_ids_from_cds(file2_path)

            if len(ids1) != len(ids2):
                print(f"警告: {file1_name} ({len(ids1)}) 与 {file2_name} ({len(ids2)}) 序列数不一致。")

            # 写入配对文件
            with open(output_filename, 'w', encoding='utf-8') as out_f:
                for id_a, id_b in zip(ids1, ids2):
                    out_f.write(f"{id_a}\t{id_b}\n")

            print(f"已生成: {output_filename}")


if __name__ == "__main__":
    main()