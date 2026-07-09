import os
import subprocess
import sys
from itertools import combinations

# ================= 配置区域 =================
# 1. 物种列表文件名
LIST_FILE = "species_list.txt"

# 2. 处理器配置文件名 (你目录下已有的那个文件)
PROC_FILENAME = "proc"

# 3. ParaAT.pl 的绝对路径 (根据你的报错日志填写的)
PARAAT_EXEC = "/data01/teachersHome/lyuxian/leitianyu/chenbiao/software/ParaAT2.0/ParaAT.pl"


# ===========================================

def run_command(cmd, description):
    """执行 Shell 命令并打印日志"""
    print(f"正在执行: {description}")
    try:
        # 使用 bash 执行，确保能识别通配符 * 和重定向 >
        subprocess.run(cmd, shell=True, check=True, executable='/bin/bash')
    except subprocess.CalledProcessError:
        print(f"ERROR: 命令执行失败 -> {cmd}")
        raise  # 抛出异常供主程序捕获


def main():
    # --- 1. 环境检查 ---
    if not os.path.exists(LIST_FILE):
        print(f"错误: 找不到列表文件 {LIST_FILE}")
        sys.exit(1)

    if not os.path.exists(PROC_FILENAME):
        print(f"错误: 找不到 proc 文件 -> {PROC_FILENAME}")
        print("请确保当前目录下有一个名为 proc 的文件，里面写着线程数(例如 10)。")
        sys.exit(1)

    if not os.path.exists(PARAAT_EXEC):
        print(f"错误: 找不到 ParaAT 程序 -> {PARAAT_EXEC}")
        sys.exit(1)

    # --- 2. 读取物种列表 ---
    with open(LIST_FILE, 'r') as f:
        content = f.read().strip()
        if not content:
            print("错误: 列表文件是空的")
            sys.exit(1)
        # 支持换行或空格分隔
        leaves = content.split()

    print(f"检测到 {len(leaves)} 个物种: {leaves}")

    # --- 3. 生成两两组合 ---
    # combinations 会自动生成不重复的组合
    pairs = list(combinations(leaves, 2))
    print(f"总共需要处理 {len(pairs)} 对组合。\n")

    # --- 4. 循环处理每一对 ---
    for leaf1, leaf2 in pairs:
        pair_name = f"{leaf1}.{leaf2}"

        print(f"\n{'=' * 50}")
        print(f"当前处理: {leaf1} vs {leaf2}")
        print(f"{'=' * 50}")

        # 检查关键输入文件
        missing = []
        required_files = [f"{leaf1}.cds", f"{leaf2}.cds", f"{leaf1}.pep", f"{leaf2}.pep", f"{pair_name}.pairs"]

        for f in required_files:
            if not os.path.exists(f):
                missing.append(f)

        if missing:
            print(f"跳过: 缺少必要文件 -> {missing}")
            continue

        try:
            # Step 1: 合并 CDS
            # cat Leaf1.cds Leaf2.cds > Leaf1.Leaf2.cds
            cmd1 = f"cat {leaf1}.cds {leaf2}.cds > {pair_name}.cds"
            run_command(cmd1, "Step 1: 合并 CDS")

            # Step 2: 合并 PEP
            # cat Leaf1.pep Leaf2.pep > Leaf1.Leaf2.pep
            cmd2 = f"cat {leaf1}.pep {leaf2}.pep > {pair_name}.pep"
            run_command(cmd2, "Step 2: 合并 PEP")

            # Step 3: 运行 ParaAT
            # 关键修改: -p 参数直接使用变量 PROC_FILENAME (即 "proc")
            cmd3 = (f"{PARAAT_EXEC} -h {pair_name}.pairs "
                    f"-a {pair_name}.pep "
                    f"-n {pair_name}.cds "
                    f"-p {PROC_FILENAME} "
                    f"-o {pair_name}.besthit "
                    f"-f axt -m mafft")
            run_command(cmd3, "Step 3: 运行 ParaAT")

            # Step 4: 合并 AXT
            # 查找 output 目录下的 *aln.axt 并合并
            output_dir = f"{pair_name}.besthit"
            output_axt = f"{output_dir}/{pair_name}.all.axt"

            if os.path.isdir(output_dir):
                # 使用 find 查找并合并
                cmd4 = f"find {output_dir}/ -name '*aln.axt' | xargs cat > {output_axt}"
                run_command(cmd4, "Step 4: 合并 AXT")
            else:
                print(f"错误: ParaAT 未生成输出目录 {output_dir}，可能是比对失败。")
                continue

            # Step 5: KaKs 计算
            if os.path.exists(output_axt) and os.path.getsize(output_axt) > 0:
                cmd5 = (f"KaKs_Calculator "
                        f"-i {output_axt} "
                        f"-o {pair_name}.besthit.ks "
                        f"-m NG")
                run_command(cmd5, "Step 5: KaKs_Calculator")
            else:
                print("错误: AXT 结果文件为空或不存在，无法计算 Ka/Ks")

        except subprocess.CalledProcessError:
            print(f"警告: 处理组合 {pair_name} 时发生错误，已跳过并继续下一对。")
            continue

    print("\n所有任务完成。")


if __name__ == "__main__":
    main()