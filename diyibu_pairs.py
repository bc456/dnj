import os
import itertools
import subprocess


def main():
    list_file = "species_list.txt"

    # 1. 检查文件是否存在
    if not os.path.exists(list_file):
        print(f"错误: 找不到文件 {list_file}")
        return

    # 2. 读取物种列表
    with open(list_file, 'r') as f:
        species_list = f.read().split()

    num_species = len(species_list)
    print(f"共检测到 {num_species} 个物种。")
    print("==================================================")
    print("第一阶段：正在为所有物种统一建立数据库...")
    print("==================================================")

    # 【优化核心 1】: 先用一个独立的单循环，把所有数据库建好
    for species in species_list:
        db_cmd = f"diamond makedb --in {species}.pep --db {species}"
        print(f">>> 正在为 {species} 建库: {db_cmd}")
        try:
            subprocess.run(db_cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"🚨 {species} 建库失败，错误代码: {e.returncode}")
            # 如果建库失败，后续比对肯定会错，建议直接退出排查
            exit(1)

    print("\n==================================================")
    print("第二阶段：开始进行两两组合比对及后续分析...")
    print("==================================================")

    # 【优化核心 2】: 双层循环内只保留比对和处理逻辑，删除了 makedb
    for X, Y in itertools.combinations(species_list, 2):
        print("-" * 40)
        print(f"正在处理组合: {X} 和 {Y}")
        print("-" * 40)

        commands = [
            # X 比对到 Y 库
            f"diamond blastp --db {Y}.dmnd -q {X}.pep -o {X}.{Y}.diamond --sensitive --max-target-seqs 10",
            # Y 比对到 X 库
            f"diamond blastp --db {X}.dmnd -q {Y}.pep -o {Y}.{X}.diamond --sensitive --max-target-seqs 10",
            # 合并双向比对结果
            f"cat {X}.{Y}.diamond {Y}.{X}.diamond > {X}.{Y}.two.diamond",
            # 运行 Perl 脚本过滤 Best Hit
            f"perl 2.3.filter.besthit.blast.pl dir ./ two.diamond",
            # 提取第1和第2列
            f"cut -f 1,2 {X}.{Y}.two.diamond.besthits > {X}.{Y}.pairs"
        ]

        # 依次执行流程
        for cmd in commands:
            print(f">>> 运行: {cmd}")
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"🚨 命令执行失败: {cmd}，错误代码: {e.returncode}")
                # 可根据需要决定是 continue 还是 exit(1)

        print(f"✅ 组合 {X} 和 {Y} 处理完成！\n")

    print("🎉 所有物种的数据库构建与两两比对流程已全部高效完成！")


if __name__ == "__main__":
    main()