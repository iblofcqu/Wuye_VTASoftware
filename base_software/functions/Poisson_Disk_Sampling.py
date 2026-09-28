"""
@Describe: 
@File:    Poisson_Disk_Sampling.py
@ENV:     
@Author:  Hill_Liao
@Date:    2025年07月21日
"""

import open3d as o3d
import numpy as np
def Mesh_to_PCD(mesh_path,distance_points):
    mesh=o3d.io.read_triangle_mesh(mesh_path)#读取网格文件
    mesh.compute_vertex_normals()#计算网格法向量
    area = mesh.get_surface_area()#计算网格总面积
    pcd_num = int(area / (distance_points ** 2))#根据点距离计算点数
    pcd=mesh.sample_points_poisson_disk(number_of_points=pcd_num)
    pcd_xyz=np.asarray(pcd.points)
    return pcd_xyz