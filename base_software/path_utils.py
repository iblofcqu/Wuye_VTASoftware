# path_utils.py
import os
import sys

def get_app_base_path():
    """获取应用根目录路径（兼容打包环境）"""
    if getattr(sys, 'frozen', False):
        # 打包后环境
        return sys._MEIPASS
    
    # 开发环境 - 获取项目根目录
    # 方法1: 检查当前目录是否包含关键目录/文件
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检查是否存在关键目录
    key_dirs = ['pages', 'functions', 'interface']
    if all(os.path.exists(os.path.join(current_dir, d)) for d in key_dirs):
        return current_dir
    
    # 方法2: 向上查找直到找到包含关键目录的根目录
    parent_dir = os.path.dirname(current_dir)
    while parent_dir != current_dir:
        if all(os.path.exists(os.path.join(parent_dir, d)) for d in key_dirs):
            return parent_dir
        current_dir = parent_dir
        parent_dir = os.path.dirname(current_dir)
    
    # 方法3: 如果以上都不行，返回当前文件所在目录
    return os.path.dirname(os.path.abspath(__file__))

def get_cache_path():
    """获取缓存目录路径"""
    base_path = get_app_base_path()
    cache_dir = os.path.join(base_path, "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

def get_interface_path():
    """获取界面资源目录路径"""
    return os.path.join(get_app_base_path(), "interface")

def get_functions_path():
    """获取功能模块目录路径"""
    return os.path.join(get_app_base_path(), "functions")

def get_pages_path():
    """获取页面目录路径"""
    return os.path.join(get_app_base_path(), "pages")