import numpy as np
from sklearn.neighbors import  KDTree
import open3d as o3d

def fit_plane(points):
    """
    使用最小二乘法拟合空间平面
    输入：点云数据，形状为(N, 3)的numpy数组
    输出：平面方程参数A, B, C, D（满足Ax + By + Cz + D = 0）
    """
    # 计算质心
    centroid = np.mean(points, axis=0)

    # 去中心化
    points_centered = points - centroid

    # 计算奇异值分解
    U, S, Vt = np.linalg.svd(points_centered, full_matrices=False)
    # 法向量为最小奇异值对应的右奇异向量
    normal = Vt[2, :]

    # 平面方程参数
    A, B, C = normal
    D = -np.dot(normal, centroid)

    return np.array([A, B, C, D])

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
    """
    将三维点集投影到指定平面

    参数：
    points: numpy数组，形状为(N, 3)，表示N个三维点
    plane_normal: 平面法向量，形如[nx, ny, nz]
    plane_point: 平面上的一个点，形如[x0, y0, z0]

    返回：
    projected_points: numpy数组，形状为(N, 3)，投影后的点集
    """
    # 转换为numpy数组
    plane_normal = np.asarray(plane_normal, dtype=np.float64)
    plane_point = np.asarray(plane_point, dtype=np.float64)
    points = np.asarray(points, dtype=np.float64)

    # 验证平面法向量非零
    if np.allclose(plane_normal, 0):
        raise ValueError("平面法向量不能为零向量")

    # 计算每个点到平面点的向量与法向量的点积
    vector_to_point = points - plane_point
    dot_products = np.dot(vector_to_point, plane_normal)

    # 计算缩放系数
    t = dot_products / np.dot(plane_normal, plane_normal)

    # 计算投影坐标
    projection_vectors = np.outer(t, plane_normal)
    projected_points = points - projection_vectors

    return projected_points

def Error_caculate_Point2Plane(check_pt,pcd,r):
    tree=KDTree(pcd[:,:3])
    pcd_neat_distance=[]
    for i in range(len(check_pt)):
        pt_plane=[]
        dis, index = tree.query(check_pt[i].reshape(-1, 3), k=1)
        cp=pcd[index[0],:]
        index2 = tree.query_radius(cp.reshape(-1, 3), r)
        if len(index2[0])>2:
            pt_plane.append(pcd[index2[0],:])
            pt_plane=np.vstack(pt_plane)
            plane_model=fit_plane(pt_plane)
            plane_model /= np.linalg.norm(plane_model[:3])
            pt_project=project_points_to_plane(check_pt[i],plane_model[:3],[0,0,-(plane_model[3]/plane_model[2])])[0]
            error=np.linalg.norm(check_pt[i]-pt_project)
        else:
            error=0
        pcd_neat_distance.append(error)
    pcd_neat_distance=np.hstack(pcd_neat_distance)
    return pcd_neat_distance
