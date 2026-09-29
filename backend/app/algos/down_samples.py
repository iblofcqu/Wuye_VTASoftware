import open3d as o3d
import numpy as np

def voxel_downsample(point_cloud, voxel_size):
    """
    体素下采样
    ----------
    Parameters
            point_cloud 待处理点云
            num  下采样的倍数，每n个点采样为一个点
    Returns
            sample_point_array 体素像采样后点云，numpy.array形式
    ----------
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(point_cloud)
    voxel_down_pcd = pcd.voxel_down_sample(voxel_size=voxel_size)
    sample_point_array = np.array(voxel_down_pcd.points)
    return sample_point_array

def uniform_downsample(point_cloud,num):
    """
    均匀下采样
    ----------
    Parameters
            point_cloud 待处理点云
            num  下采样的倍数，每n个点采样为一个点
    Returns
            sample_point_array 体素像采样后点云，numpy.array形式
    ----------
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(point_cloud)
    uniform_down_pcd = pcd.uniform_down_sample(every_k_points=num)
    sample_point_array = np.array(uniform_down_pcd.points)
    return sample_point_array

def farthest_point_down_sample(point_cloud, num):
    """
   最远点下采样
   ----------
   Parameters
           point_cloud 待处理点云
           num  降采样后的点数
   Returns
           sample_point_array 体素像采样后点云，numpy.array形式
   ----------
   """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(point_cloud)
    FP_down_pcd = pcd.farthest_point_down_sample(num_samples=num)
    sample_point_array = np.array(FP_down_pcd.points)
    return sample_point_array

def random_down_sample(point_cloud, sampling_ratio):
    """
    随机下采样
    ----------
    Parameters
           point_cloud 待处理点云
           sampling_ratio  降采样的比例
    Returns
           sample_point_array 体素像采样后点云，numpy.array形式
    ----------
   """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(point_cloud)
    random_down_pcd = pcd.random_down_sample(sampling_ratio=sampling_ratio)
    sample_point_array = np.array(random_down_pcd.points)
    return sample_point_array
