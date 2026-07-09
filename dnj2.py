import pandas as pd
import numpy as np
import os
import re


class DRC_DNJ_Algorithm:
    def __init__(self, excel_path):
        """
        初始化 DRC-DNJ 算法类，读取距离矩阵并计算异方差权重。
        """
        print(f"正在加载数据: {excel_path} ...")
        df = pd.read_excel(excel_path, index_col=0)
        self.names = [str(name).strip() for name in df.index.tolist()]
        self.D_orig = df.values.astype(float)
        self.N = len(self.names)

        # 强制矩阵严格对称，并将对角线置为0，消除潜在的浮点数误差
        self.D_orig = (self.D_orig + self.D_orig.T) / 2
        np.fill_diagonal(self.D_orig, 0)

        # === [核心修正 1] 计算残差权重因子 (基于 1/D^2 的 WLS 机制) ===
        # 添加微小常数 1e-6 防止对角线或极近物种除以 0 报错
        W_raw = 1.0 / (self.D_orig ** 2 + 1e-6)
        np.fill_diagonal(W_raw, 0)
        # 归一化权重矩阵，使得其非零均值维持在 1 左右，确保不破坏初始学习率的标度
        self.W_norm = W_raw / np.mean(W_raw[W_raw > 0])

        print(f"成功加载 {self.N} x {self.N} 的距离矩阵，并完成加权最小二乘(WLS)矩阵初始化。")

    def build_standard_nj(self, D_input):
        """
        构建单次 NJ 树，返回树的边和节点连接关系。
        """
        D = D_input.copy()
        active_nodes = list(range(self.N))
        edges = []
        next_node_id = self.N

        while len(active_nodes) > 2:
            n = len(active_nodes)
            r = np.sum(D, axis=1)

            Q = np.zeros((n, n))
            for i in range(n):
                for j in range(n):
                    if i != j:
                        Q[i, j] = (n - 2) * D[i, j] - r[i] - r[j]
            np.fill_diagonal(Q, np.inf)

            min_idx = np.unravel_index(np.argmin(Q), Q.shape)
            i, j = min_idx[0], min_idx[1]

            u = active_nodes[i]
            v = active_nodes[j]
            w = next_node_id
            next_node_id += 1

            L_uw = 0.5 * D[i, j] + 0.5 * (r[i] - r[j]) / (n - 2)
            L_vw = D[i, j] - L_uw

            edges.append((w, u, L_uw))
            edges.append((w, v, L_vw))

            D_w = 0.5 * (D[i, :] + D[j, :] - D[i, j])

            keep = [k for k in range(n) if k not in (i, j)]
            new_D = np.zeros((n - 1, n - 1))

            for new_idx_1, old_idx_1 in enumerate(keep):
                for new_idx_2, old_idx_2 in enumerate(keep):
                    new_D[new_idx_1, new_idx_2] = D[old_idx_1, old_idx_2]

            for new_idx, old_idx in enumerate(keep):
                new_D[-1, new_idx] = D_w[old_idx]
                new_D[new_idx, -1] = D_w[old_idx]

            D = new_D
            active_nodes = [active_nodes[k] for k in keep] + [w]

        u = active_nodes[0]
        v = active_nodes[1]
        super_root = next_node_id
        L_ur = D[0, 1] / 2.0
        L_vr = D[0, 1] / 2.0
        edges.append((super_root, u, L_ur))
        edges.append((super_root, v, L_vr))

        tree_adj = {}
        for parent, child, length in edges:
            if parent not in tree_adj:
                tree_adj[parent] = []
            tree_adj[parent].append((child, length))

        return tree_adj, super_root

    def calculate_cophenetic_matrix(self, tree_adj, root):
        """
        利用广度优先搜索 (BFS)，根据生成的树反推“理论预测距离”矩阵。
        """
        undirected_adj = {k: [] for k in range(self.N * 2)}
        for p, children in tree_adj.items():
            for c, dist in children:
                undirected_adj[p].append((c, dist))
                undirected_adj[c].append((p, dist))

        P = np.zeros((self.N, self.N))
        for i in range(self.N):
            visited = {i}
            queue = [(i, 0.0)]
            while queue:
                curr, curr_dist = queue.pop(0)
                if curr < self.N and curr != i:
                    P[i, curr] = curr_dist
                for neighbor, dist in undirected_adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, curr_dist + dist))
        return P

    def to_newick(self, node, tree_adj, strict_positive=False):
        """
        递归生成 Newick 格式字符串。
        加入 strict_positive 参数控制是否截断负分支。
        """
        if node < self.N:
            return self.names[node]
        else:
            children_strs = []
            for child, dist in tree_adj.get(node, []):
                # 最终输出树时强制非负，以满足 MEGA 软件的生物学解析要求
                final_dist = max(dist, 0.000001) if strict_positive else dist
                child_str = self.to_newick(child, tree_adj, strict_positive)
                children_strs.append(f"{child_str}:{final_dist:.6f}")
            return "(" + ",".join(children_strs) + ")"

    def get_topology_string(self, newick_str):
        """正则去除分支长度，仅保留纯拓扑结构字符串，用于判定结构收敛"""
        return re.sub(r':[0-9\.\-]+', '', newick_str)

    def fit_and_generate_auto(self, initial_lr=1, tolerance=1e-5, min_lr=1e-6, output_file="DRC_DNJ_tree.nwk"):
        """
        DRC-DNJ 的全自动自适应优化闭环。
        """
        print("\n=== 开始 DRC-DNJ 距离残差修正迭代 (加权优化增强版) ===")
        D_curr = self.D_orig.copy()
        best_loss = float('inf')
        best_newick = ""
        best_D = D_curr.copy()

        lr = initial_lr
        max_safe_iter = 500
        patience = 8
        patience_counter = 0

        # 记录上一轮的纯拓扑结构
        prev_topology = ""
        stable_topology_count = 0

        i = 0
        while i < max_safe_iter:
            tree_adj, root = self.build_standard_nj(D_curr)
            P_matrix = self.calculate_cophenetic_matrix(tree_adj, root)

            Residuals = P_matrix - self.D_orig

            # === [核心修正 1 延续] 计算加权 Loss ===
            loss = np.sum(self.W_norm * (Residuals ** 2))

            # 监控拓扑结构是否稳定
            current_newick = self.to_newick(root, tree_adj, strict_positive=False)
            current_topology = self.get_topology_string(current_newick)

            if current_topology == prev_topology:
                stable_topology_count += 1
            else:
                stable_topology_count = 0
            prev_topology = current_topology

            # === [核心修正 3 的平替实现] 拓扑稳定后，平滑进入分支长度微调期 ===
            if stable_topology_count > 3:
                # 拓扑已经不再变化，降低学习率，仅做残差枝长逼近
                current_lr = lr * 0.5
            else:
                current_lr = lr

            print(
                f"迭代 [{i + 1:03d}] | Loss: {loss:.6f} | 学习率: {current_lr:.6f} | 拓扑稳定: {stable_topology_count}轮")

            if loss > best_loss and best_loss != float('inf'):
                print(f"  -> ⚠️ Loss 发散，学习率衰减 ({lr:.6f} -> {lr * 0.5:.6f})")
                lr *= 0.5
                if lr < min_lr:
                    print(">> 学习率已达下限，算法终止。")
                    break
                D_curr = best_D.copy()
                continue

            if abs(best_loss - loss) < tolerance:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f">> 连续 {patience} 次 Loss 变化极小，模型已收敛！")
                    break
            else:
                patience_counter = 0

            best_loss = loss
            # 记录时暂不硬截断，但在最终输出时会截断
            best_newick = self.to_newick(root, tree_adj, strict_positive=True) + ";"
            best_D = D_curr.copy()

            # === [核心修正 1 与 2] 加权修正矩阵，并放宽负距截断 (软截断) ===
            D_curr = D_curr - current_lr * (self.W_norm * Residuals)

            # 软截断：在探索期允许矩阵出现微小的负距，以维持梯度的流动性，不硬卡 0.0001
            D_curr[D_curr < -0.05] = -0.05
            np.fill_diagonal(D_curr, 0)

            i += 1

        with open(output_file, 'w') as f:
            f.write(best_newick)

        print("\n=== 自适应算法执行完毕 ===")
        print(f"最终输出文件已保存至: {os.path.abspath(output_file)}")
        print("该 .nwk 文件可以直接拖入 MEGA 软件中打开预览。")


if __name__ == "__main__":
    input_file = "ks_filled_processed.xlsx"
    output_filename = "DRC_DNJ_Result2.nwk"

    if os.path.exists(input_file):
        algorithm = DRC_DNJ_Algorithm(input_file)
        algorithm.fit_and_generate_auto(initial_lr=1, output_file=output_filename)
    else:
        print(f"错误：找不到文件 '{input_file}'，请确保输入文件放在此代码同一目录下！")