import numpy as np
from sklearn.neighbors import  KDTree
import open3d as o3d

def fit_plane(points):
    """
    使用SVD拟合空间平面
    输入：点云数据，形状为(N, 3)的numpy数组
    输出：(plane_model, centroid) 或 None
         plane_model: [A, B, C, D]，满足 Ax + By + Cz + D = 0
         centroid:    拟合用点的质心（一定在平面上）
         若点近似共线/退化，返回 None
    """
    centroid = np.mean(points, axis=0)
    points_centered = points - centroid

    U, S, Vt = np.linalg.svd(points_centered, full_matrices=False)

    # S 降序，S[2] 是"垂直于平面"方向的散度
    # S[2] 太小 → 点近似共线，平面不可信
    if S[2] < 1e-10 * max(S[0], 1e-30):
        return None

    normal = Vt[2, :]
    A, B, C = normal
    D = -np.dot(normal, centroid)

    return np.array([A, B, C, D]), centroid

def knn_find(data, data_orignal, k=10000):
    """
    knn最近邻算法
    ----------
    Parameters
            data 待处理点云
            data_orignal  原始点云
            k 点数
    Returns
            Neighbors 邻域点云
            NeighborId 邻域点云对应索引
    ----------
    """
    # a = ratio * len(data)  # 一定比例的数量，做为knn算法中的k
    tree = KDTree(data_orignal[:, :3])   # 点云结构化：对原始点云创建Kdtree
    Neighbors = []
    NeighborId = []
    for i, each in enumerate(data):
        # neghborId1 = tree.query_radius(each.reshape(1, 3),r=ratia)
        # neighbors1 = data_orignal[neghborId1[0], :3]
        # Neighbors.append(neighbors1)
        neghborId1 = tree.query(each.reshape(1, 3), k)
        neighbors1 = data_orignal[neghborId1[1], :3]
        # draw(neighbors1[0])
        neighbors = np.concatenate((each.reshape(1, 3), neighbors1[0]), axis=0)
        Neighbors.append(neighbors)
        NeighborId.append(neghborId1[1][0])  # data[column][row] 两个方括号相当于先取列，再取行。此操作是仅保留邻域点索引
    return Neighbors, NeighborId

def find_k(data, data_orignal, k):
    tree=KDTree(data_orignal[:,:3])
    pcd_neat_index = []
    for i in range(len(data)):
        dis,index=tree.query(data[i].reshape(-1,3),k)
        pcd_neat_index.append(index[0])
    pcd_neat_index=np.hstack(pcd_neat_index)
    pcd_neat_index_unique = np.unique(pcd_neat_index)
    pcd_neat=data_orignal[pcd_neat_index_unique,:]
    return pcd_neat


def find_r(data,data_orignal,r):
    tree=KDTree(data_orignal[:,:3])
    pcd_neat_index=[]
    for i in range(len(data)):
        index=tree.query_radius(data[i].reshape(-1,3),r)
        if len(index[0])>10:
            pcd_neat_index.append(index[0])
    pcd_neat_index=np.hstack(pcd_neat_index)
    pcd_neat_index_unique=np.unique(pcd_neat_index)
    pcd_neat=data_orignal[pcd_neat_index_unique,:]
    return pcd_neat

def Error_caculate_Point2Point(check_pt,pcd,k):
    tree=KDTree(pcd[:,:3])
    pcd_neat_distance=[]
    for i in range(len(check_pt)):
        dis, index = tree.query(check_pt[i].reshape(-1, 3), k)
        pcd_neat_distance.append(dis[0])
    pcd_neat_distance=np.hstack(pcd_neat_distance)
    return pcd_neat_distance

def project_points_to_plane(points, plane_normal, plane_point):
    plane_normal = np.asarray(plane_normal, dtype=np.float64)
    plane_point = np.asarray(plane_point, dtype=np.float64)
    points = np.asarray(points, dtype=np.float64)

    if np.allclose(plane_normal, 0):
        raise ValueError("平面法向量不能为零向量")

    vector_to_point = points - plane_point
    dot_products = np.dot(vector_to_point, plane_normal)
    t = dot_products / np.dot(plane_normal, plane_normal)
    projection_vectors = np.outer(t, plane_normal)
    projected_points = points - projection_vectors
    return projected_points

def Error_caculate_Point2Plane(check_pt, pcd, r):
    tree = KDTree(pcd[:, :3])
    pcd_neat_distance = []

    for i in range(len(check_pt)):
        dis, index = tree.query(check_pt[i].reshape(-1, 3), k=1)
        cp = pcd[index[0], :]
        index2 = tree.query_radius(cp.reshape(-1, 3), r)

        if len(index2[0]) > 2:
            pt_plane = pcd[index2[0], :]

            result = fit_plane(pt_plane)
            if result is None:
                # 点近似共线，平面退化，跳过
                pcd_neat_distance.append(0.0)
                continue

            plane_model, plane_centroid = result

            # 归一化法向量（保持原逻辑）
            norm = np.linalg.norm(plane_model[:3])
            if norm < 1e-12 or not np.isfinite(norm):
                pcd_neat_distance.append(0.0)
                continue
            normal = plane_model[:3] / norm

            # 用质心当平面上一点，避免 [0,0,-(D/C)] 在 C=0 时出 inf/nan
            pt_project = project_points_to_plane(
                check_pt[i], normal, plane_centroid
            )[0]

            error = np.linalg.norm(check_pt[i] - pt_project)

            # 兜底：万一还有 nan/inf
            if not np.isfinite(error):
                error = 0.0
        else:
            error = 0.0

        pcd_neat_distance.append(error)

    pcd_neat_distance = np.hstack(pcd_neat_distance)
    return pcd_neat_distance

