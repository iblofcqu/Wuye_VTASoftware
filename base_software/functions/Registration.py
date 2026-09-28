import time

from tqdm import tqdm
import pyransac3d as pyrsc
import open3d as o3d
import numpy as np
import itertools
import pyvista as pv
from sklearn.neighbors import NearestNeighbors,KDTree


# def show2(point_array, point_array1):
#     # 通过添加mesh的方法绘图
#     p = pv.Plotter()  ## 建一个画板
#     # 然后在画板上画图
#     p.add_mesh(pv.PolyData(point_array), color='red', render_points_as_spheres=True, point_size=10)
#     p.add_mesh(pv.PolyData(point_array1), color='blue', render_points_as_spheres=True, point_size=10)
#     p.set_background('w')
#     p.show()


def f_traverse(node, node_info):
    if isinstance(node, o3d.geometry.OctreePointColorLeafNode):  # 判断node是不是八叉树数据，是的话返回true，不是返回false
        if len(node.indices) > 50:  # 如果node.indices的长度大于50
            LEAF_INDICES.append(node.indices)  # 把node.indices加入至叶指数

def BallDetection(sphereRadius, pointsThres=50):
    '''
    检测标靶球的数据点
    :param sphereRadius: 标靶球的半径
    :param pointsThres: 点数量的最低阈值
    :return: 检测出可能是标靶球的数据点
    '''
    balls_all_points = []
    with tqdm(total=len(LEAF_INDICES), position=0, leave=True) as pbar: #进度条，总长度为叶片数，间隔行数默认，结束时保留进度条，with上下文调用无需关闭文件
        for i, indices in tqdm(enumerate(LEAF_INDICES), position=0, leave=True): #返回每片叶子的进度
            pbar.update() #进度条按默认间隔更新
            points = SCAN[indices] #SCAN_DOWN为下采样的点
            try:
                sphere = pyrsc.Sphere()
                center, radius, inliers = sphere.fit(points, thresh=0.002, maxIteration=1000) #在points中寻找球，阈值距离为0.002，最大迭代次数为1000
                #返回了球心，半径以及球点索引
            except ValueError:
                continue
            if sphereRadius * 1.1 >= radius >= sphereRadius * 0.9 and len(inliers) >= pointsThres: #如果检测出的球半径在预定义半径的0.9-1.1倍，并且球点超过了设定数量
                for j in range(len(inliers)):  # 便历了索引长度
                    balls_all_points.append(points[inliers[j], :3])  # 将每个求坐标加入列表
    pbar.close()  # 关闭进度条
    balls_all_points = np.array(balls_all_points)  # 得到所有标靶球的点
    return balls_all_points


def SphereLeastSquareFit(point):
    """
    最小二乘法拟合球体（矩阵求解）
        球体方程： （x-a)^2+(y-b)^2+(z-c)^2=r^2
        方程变形： x^2+y^2+z^2-2ax-2by-2cz+a^2+b^2+c^2=r^2
        改写为： x^2+y^2+z^2-Ax-By-Cz-D=0, a=A/2, b=B/2, c=C/2, r=sqrt(a^2+b^2+c^2-D)
    ----------
    Parameters
            point 待处理点云
    Returns
            r     球半径
            a,b,c 球心坐标
    ----------
    """
    M = []
    N = []
    for d in point:
        M.append([d[0], d[1], d[2], -1])
        N.append([d[0] ** 2 + d[1] ** 2 + d[2] ** 2])
    M = np.array(M)
    N = np.array(N)
    M_T = M.T
    S = M_T.dot(M) # x^2+y^2+z^2+1
    T = M_T.dot(N)

    try:
        result = np.linalg.inv(S).dot(T) # S的逆矩阵点乘T
    except:
        result = np.zeros(4)

    a = result[0]/2
    b = result[1]/2
    c = result[2]/2
    r = np.sqrt(a ** 2 + b ** 2 + c ** 2 - result[3])

    return a, b, c, r

def FitBall(ball_list):
    """
    球拟合
    ----------
    Parameters
            ball_list 球点列表
    Returns
            circle_points 球体的参数：球心坐标和半径
    ----------
    """
    circle_points = []
    for ball_data in ball_list:
        if len(ball_data):
            x, y, z, r = SphereLeastSquareFit(ball_data)
            point_data = np.zeros(4)  # 存储结果[x,y,z,r]
            if r:
                point_data[0] = x
                point_data[1] = y
                point_data[2] = z
                point_data[3] = r
                circle_points.append(point_data)
    return np.array(circle_points)

def Target(SCAN1):
    global LEAF_INDICES,SCAN
    LEAF_INDICES = []
    SCAN = SCAN1[:, 0:3]
    pcd = o3d.geometry.PointCloud()  # 定义这个函数的缩写为pcd
    N = SCAN.shape[0]  # N为下采样后点云数据的行数
    pcd.points = o3d.utility.Vector3dVector(SCAN[:, 0:3])  # 将下采样后返回的np数组前三列重新转化为o3d格式
    pcd.colors = o3d.utility.Vector3dVector(np.random.uniform(0, 1, size=(N, 3)))  # 按点的数量对体素着色
    octree = o3d.geometry.Octree(max_depth=5)  # 创建八叉树，深度为9
    octree.convert_from_point_cloud(pcd, size_expand=0.08)  # 从pcd中构建八叉树，适当扩展边界0.1m
    octree.traverse(f_traverse)  # 遍历
    balls_all_points = BallDetection(0.0725)  # 标靶球半径为0.0725m,检测出可能的标靶球点
    return balls_all_points

def transfer_matrix(source_data, target_data):
    """
    计算变换矩阵
    ----------
    Parameters
             target_data 目标点云数据
             source_data 源点云数据
    Returns
             r 旋转矩阵
             t 平移矩阵
    ----------
    """
    source_mean = np.mean(source_data, axis=0)
    target_mean = np.mean(target_data, axis=0)
    source_data2 = source_data - source_mean
    target_data2 = target_data - target_mean
    S = np.dot(target_data2.T,source_data2 )
    [u, _, vT] = np.linalg.svd(S)
    r = np.dot(vT.T, u.T)
    m,n =np.shape(vT)
    if np.linalg.det(r) < 0:
        vT[m - 1, :] *= -1
        r = np.dot(vT.T, u.T)
    s = np.dot(source_mean,r)
    t = target_mean - s
    return r, t

def SphereRegistration(sourceBall, targetBall):
    """
    基于球心配准
    ----------
    Parameters
            sourceBall 源点云的标靶球球心坐标
            targetBall 目标点云的标靶球球心坐标
    Returns
            R 旋转矩阵
            T 平移矩阵
    ----------
    """
    arrT = itertools.combinations(range(len(targetBall)), 3)   # 全排列：从目标点云标靶球球心中每次挑选3个
    R, T = [], []
    totalScore = float("inf")
    i = 0
    for indiceT in arrT:
        ballT = np.array([targetBall[indiceT[0], :3], targetBall[indiceT[1], :3], targetBall[indiceT[2], :3]])
        arrS = itertools.permutations(range(len(sourceBall)), 3)     # 全排列：从源点云标靶球球心中每次挑选3个
        for indiceS in arrS:
            ballS = np.array([sourceBall[indiceS[0], :3], sourceBall[indiceS[1], :3], sourceBall[indiceS[2], :3]])
            r, t = transfer_matrix(ballS, ballT)
            ballS_Trans = np.dot(ballS, r) + t
            score = np.sum(np.square(ballT - ballS_Trans))
            i += 1
            # print('indiceS=', indiceS)
            # print('score=', score)
            if score < totalScore:
                totalScore = score
                R, T = r, t
    # print('totalScore=', totalScore)
    # print('i=', i)
    return R, T

def Open3d_ICP(source_data, target_data,r1):
    """
    ICP 迭代最近邻配准（精配准）
    ----------
    Parameters
            source_data 源点云数据
            target_data 目标点云数据

    Returns
            配准后的源点云数据，矩阵形式
    ----------
    """
    src = o3d.geometry.PointCloud()
    src.points = o3d.utility.Vector3dVector(source_data[:, :3])
    dst = o3d.geometry.PointCloud()
    dst.points = o3d.utility.Vector3dVector(target_data[2:, :3])
    threshold = r1                     # 搜索邻域
    trans_init = np.identity(4)               # 如果两个点云已经很接近就用这个trans_init
    src.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(2, 8))
    dst.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(2, 8))
    reg_p2l = o3d.pipelines.registration.registration_icp(
        src, dst, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPlane())
    return np.asarray((src.transform(reg_p2l.transformation)).points)

def Registration_rough_ICP(source_ball, target_ball, ahead, targ_pcd, r1, r2, r3):
    """
    基于标靶球配准，迭代三次ICP
    :param source_ball: 源球心
    :param target_ball: 目标球心
    :param ahead: 第一站点云
    :param targ_pcd: 第二站点云
    :param r1: 第一次icp参数
    :param r2: 第二次icp参数
    :param r3: 第三次icp参数
    :return: whole_data: 配准后数据
    """
    source_ball2 = np.array(source_ball)
    target_ball2 = np.array(target_ball)

    R, T = SphereRegistration(source_ball2, target_ball2)

    convert_ahead = np.dot(ahead, R) + T
    sour_pcd = convert_ahead

    fr_sour_data = Open3d_ICP(sour_pcd, targ_pcd, r1)
    fr_sour_data2 = Open3d_ICP(fr_sour_data, targ_pcd, r2)
    fr_sour_data3 = Open3d_ICP(fr_sour_data2, targ_pcd, r3)
    combined_data = np.vstack((fr_sour_data3, targ_pcd))
    whole_data = np.unique(combined_data, axis=0)
    return whole_data

def Registration_rough_ICP2(source_ball, target_ball, ahead, targ_pcd, r1, r2, r3):
    """
    基于标靶球配准，迭代三次ICP
    :param source_ball: 源球心
    :param target_ball: 目标球心
    :param ahead: 第一站点云
    :param targ_pcd: 第二站点云
    :param r1: 第一次icp参数
    :param r2: 第二次icp参数
    :param r3: 第三次icp参数
    :return: whole_data: 配准后数据
    """
    source_ball2 = np.array(source_ball)
    target_ball2 = np.array(target_ball)

    R, T = SphereRegistration(source_ball2, target_ball2)

    convert_ahead = np.dot(ahead, R) + T
    sour_pcd = convert_ahead

    fr_sour_data = Open3d_ICP(sour_pcd, targ_pcd, r1)
    fr_sour_data2 = Open3d_ICP(fr_sour_data, targ_pcd, r2)
    fr_sour_data3 = Open3d_ICP(fr_sour_data2, targ_pcd, r3)
    return fr_sour_data3


def getCornerUsingOBB(data_o):
    #主成分分析并将数据摆正
    data=data_o-np.mean(data_o,axis=0)
    N=len(data)#数据数量
    C=np.dot(data.T,data)/N
    # print('C=',C)
    ei_value,ei_vector=np.linalg.eig(C)
    data_tr=np.dot(data,ei_vector)

    # show(data_tr,data)
    #根据点云数据xyz极值建立角点盒
    x_min,y_min,z_min=np.min(data_tr,axis=0)
    x_max,y_max,z_max=np.max(data_tr,axis=0)
    corner=np.zeros(shape=(8,3))
    corner[:4,2]=z_max
    corner[4:,2]=z_min
    x_max_ind=[0,3,4,7]
    x_min_ind=[1,2,5,6]
    y_max_ind=[0,1,4,5]
    y_min_ind=[2,3,6,7]
    corner[x_max_ind,0] = x_max
    corner[x_min_ind,0] = x_min
    corner[y_max_ind,1] = y_max
    corner[y_min_ind,1] = y_min
    #将点云数据恢复成主成分分析之前的坐标系中
    ei_vector_inv = np.linalg.inv(ei_vector)
    corner_tr = np.dot(corner,ei_vector_inv)
    corner_tr = corner_tr + np.mean(data_o,axis=0)
    return corner_tr

def getCornerUsingOBB_2d(data_o):
    x_min=min(data_o[:,0])
    x_max=max(data_o[:,0])
    y_min=min(data_o[:,1])
    y_max=max(data_o[:,1])
    corner_tr=np.array([[x_min,y_min,0],[x_min,y_max,0],[x_max,y_max,0],[x_min,y_max,0]])
    return corner_tr

def hua2(point_array0,point_array1):
    # 通过添加mesh的方法绘图
    p = pv.Plotter()  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array0), color='blue', render_points_as_spheres=True, point_size=10)
    p.add_mesh(pv.PolyData(point_array1), color='red', render_points_as_spheres=True, point_size=10)
    p.set_background('w')
    p.show()

def Corner_rough_ICP(pcd_real,pcd_design,error):
    corner_real=getCornerUsingOBB_2d(pcd_real)
    corner_design=getCornerUsingOBB_2d(pcd_design)
    R1,T1=SphereRegistration(corner_real[:4,:],corner_design[:4,:])

    convert_real2 = np.dot(pcd_real, R1) + T1#进行了粗配准

    pcd_cr2_Tree = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(convert_real2)#建立角点配准后真实孔的八叉树
    convert_real=[]#按设计点云排序的真实孔
    for i in range(len(pcd_design)):
        d0,index_pt0=pcd_cr2_Tree.kneighbors([pcd_design[i]])
        convert_real.append(convert_real2[index_pt0[0]])
    convert_real=np.vstack(convert_real)

    R, T = [], []
    Score = 0
    pcd_design_Tree=NearestNeighbors(n_neighbors=1,algorithm='ball_tree').fit(pcd_design)#建立标准点的KD树
    arrT=itertools.combinations(range(len(convert_real)),3)#真实孔心全排列
    for indiceT in arrT:#遍历每种全排列
        pt1=convert_real[indiceT[0],:3]#获得当前用于配准的真实孔心
        pt2=convert_real[indiceT[1],:3]
        pt3=convert_real[indiceT[2],:3]
        d1,dpt1_index=pcd_design_Tree.kneighbors([pt1])
        d2,dpt2_index=pcd_design_Tree.kneighbors([pt2])
        d3,dpt3_index = pcd_design_Tree.kneighbors([pt3])
        dpt=np.array([pcd_design[dpt1_index[0]],pcd_design[dpt2_index[0]],pcd_design[dpt3_index[0]]])#获得用于配准的设计顶点
        dpt=np.vstack(dpt)
        pt=np.array([pt1, pt2, pt3])
        r,t=transfer_matrix(pt,dpt)#计算坐标变换矩阵pt->dpt
        convert_real_T=np.dot(convert_real,r)+t#真实顶点进行变换
        n=0
        for i in range(len(convert_real_T)):#遍历变换后的真实孔心
            # d4,dpt4_index=pcd_design_Tree.kneighbors([convert_real_T[i]])#从设计点云中找到真实孔心的最近点
            distance=np.linalg.norm(convert_real_T[i]-pcd_design[i])
            if distance<=error:
                n+=1
        if Score<=n:
            Score=n
            R=r
            T=t
    fr_sour_data2=np.dot(convert_real, R) + T

    # sour_pcd = convert_real
    # fr_sour_data = Open3d_ICP(sour_pcd, pcd_design, 0.005)
    # fr_sour_data2=Open3d_ICP(fr_sour_data, pcd_design, 0.002)

    return fr_sour_data2

def ICP(target, source, threshold):
    # 利用open3d实现ICP算法
    # open3d读取数据
    processed_source = o3d.geometry.PointCloud()
    processed_source.points = o3d.utility.Vector3dVector(source[:, :3])
    processed_target = o3d.geometry.PointCloud()
    processed_target.points = o3d.utility.Vector3dVector(target[:, :3])

    trans_init = np.identity(4)  # 4x4 identity matrix，这个矩阵为初始变换

    # 运行icp
    reg_p2p = o3d.pipelines.registration.registration_icp(
        processed_source, processed_target, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-30,
                                                          relative_rmse=1e-30,
                                                          max_iteration=3000))
    print(reg_p2p)
    print(reg_p2p.transformation)
    processed_source.transform(reg_p2p.transformation)
    return np.array(processed_source.points), reg_p2p.transformation

def ICP2(target_points, source_points, scan_sample, threshold):
    # 利用open3d实现ICP算法，不同的是使用 scan_sample 去配准，最后转换全部的 source_points
    trans_init = np.identity(4)  # 4x4 identity matrix，这个矩阵为初始变换

    processed_target = o3d.geometry.PointCloud()
    processed_target.points = o3d.utility.Vector3dVector(target_points.reshape(-1, 3))
    processed_source_sample = o3d.geometry.PointCloud()
    processed_source_sample.points = o3d.utility.Vector3dVector(scan_sample.reshape(-1, 3))
    processed_source = o3d.geometry.PointCloud()
    processed_source.points = o3d.utility.Vector3dVector(source_points.reshape(-1, 3))
    # 运行icp
    reg_p2p = o3d.pipelines.registration.registration_icp(
        processed_source_sample, processed_target, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
        o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-30,
                                                          relative_rmse=1e-30,
                                                          max_iteration=960))
    print(reg_p2p)
    print(reg_p2p.transformation)
    processed_source.transform(reg_p2p.transformation)
    processed_source_sample.transform(reg_p2p.transformation)
    return np.array(processed_source.points), np.array(processed_source_sample.points)
