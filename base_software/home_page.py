import streamlit as st
from PIL import Image
import base64
import os
import sys
import multiprocessing  # 添加多进程支持
from path_utils import get_app_base_path,get_cache_path,get_interface_path


# --- 新增：确保缓存目录存在 ---
def ensure_cache_dir():
    """确保缓存目录存在"""
    cache_dir = os.path.join(get_app_base_path(), "cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir

# 初始化缓存目录
ensure_cache_dir()

# --- 修改Streamlit配置 ---
st.set_page_config(
    page_title="首页",
    page_icon="🏠",
    initial_sidebar_state="expanded",
    # 添加以下配置确保打包后行为一致
    layout="centered",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "DeviScan-3D V1.0"
    }
)

# 多进程支持（必须添加）
multiprocessing.freeze_support()

# --- 修改后的页面内容 ---
st.sidebar.success("在上方选择一个功能")

col1, col2,col3 = st.columns([4,4, 1])
with col1:
    # 使用新的路径获取方式
    cmgc_path = os.path.join(get_interface_path(),"CMGC.png")
    st.image(Image.open(cmgc_path))
with col3:
    logo_path=os.path.join(get_interface_path(),"logo.png")
    st.image(Image.open(logo_path))

st.markdown("---")
st.markdown("""
           <b style="color:steelBlue ; font-size:50px; text-align: center; padding:150px;"> 
           三维扫描分析系统 
           """, unsafe_allow_html=True)
st.markdown("""
           <b style="color:LightSlateGray ; font-size:40px; text-align: center; padding:200px;">
            DeviScan-3D V1.0  
           """, unsafe_allow_html=True)

col9, col10, col11 = st.columns([1, 4, 1])
with col10:
    # 使用新的路径获取方式
    TJBridge_path = os.path.join(get_interface_path(),"TJBridge.png")
    st.image(Image.open(TJBridge_path), caption='')

st.markdown("""
           <n style="color:gray ; font-size:10px; text-align: center; padding:10px;"> 
           Updata on:2025/07/23
           """, unsafe_allow_html=True)

