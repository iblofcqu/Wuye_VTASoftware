import numpy as np
import open3d as o3d
import pandas as pd
import os


#方法一：读取二进制文件，并将pcd数据输出为numpy数组open3d
def data_load(bin_path):
    """
    Read point cloud in bin format
    Parameters
    ----------
    bin_path: str
        Input path of Oxford point cloud bin
    Returns
    ----------
    """
    pcd = o3d.io.read_point_cloud(bin_path, format='xyz')
    point_cloud = np.asarray(pcd.points)  # 将pcd数据转化为numpy数组
    return point_cloud

#方法二：从文件名读取点云数据，根据不同后缀打开
def data_read(filename):
    '''
    数据读取
    :param filename: 文件名
    :return:点云数据
    '''
    name = filename.split('/')[-1]
    after = name.split('.')[-1]
    if after == 'xls':
        point = pd.read_excel(filename, header=None).values
    elif (after == 'xyz') or (after == 'asc') or (after == 'txt'):
        point = pd.read_csv(filename, sep=' ', header=None, low_memory=False, index_col=None).values
    return point

def mkdir(path):
    """
    创建文件夹
    ----------
    Parameters
            path 带创建文件夹的地址（含名称）
    Returns
            创建好的空文件夹
    ----------
    """
    # 去除首位空格
    path = path.strip()
    # 去除尾部 \ 符号
    path = path.rstrip("\\")
    # 判断路径是否存在
    isExists = os.path.exists(path)
    # 判断结果
    if not isExists:
        # 如果不存在则创建目录,创建目录操作函数
        '''
        os.mkdir(path)与os.makedirs(path)的区别是,当父目录不存在的时候os.mkdir(path)不会创建，os.makedirs(path)则会创建父目录
        '''
        os.makedirs(path)
        print(path+' 创建成功')
        return True
    else:
        # 如果目录存在则不创建，并提示目录已存在
        print(path+' 目录已存在')
        return False


def get_file_list(file_path):
    """
    按照时间升序获取文件名
    :param file_path:
    :return:
    """
    dir_list = os.listdir(file_path)
    if not dir_list:
        return 0
    else:
        dir_list = sorted(dir_list, key=lambda x: os.path.getmtime(os.path.join(file_path, x)))
        return dir_list
