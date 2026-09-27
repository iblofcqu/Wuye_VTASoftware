import tkinter as tk
from tkinter import filedialog
from stpyvista import stpyvista as stpv
from functions.down_samples import *
from functions.Registration import *
from functions.FPFH import *
from functions.Poisson_Disk_Sampling import *
import streamlit as st
import os
import sys  # 新增
import multiprocessing  # 新增
from functions.load_data import *
from functions.draw_functions import *
import subprocess
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from path_utils import get_app_base_path, get_cache_path


# 多进程支持（必须添加）
multiprocessing.freeze_support()

# 配置Streamlit选项
st.config.set_option("server.maxUploadSize", 5000)
st.config.set_option("server.maxMessageSize", 5000)
st.config.set_option("server.enableWebsocketCompression", True)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    # 使用新的路径获取方式
    cache_path = get_cache_path()
    base_dir = get_app_base_path()

    # 确保缓存目录存在
    os.makedirs(cache_path, exist_ok=True)

    st.set_page_config(page_title="点云预处理", page_icon="🛠️")
    module = "点云预处理"
    pre_function = st.sidebar.radio("功能选择", ['说明书', '网格离散', '尺寸缩放','下采样', '配准' ])

    if pre_function == '说明书':
        st.markdown("""
                    <b style="color:black; 
                    font-family:KaiTi_GB2312; 
                    font-style:norm; font-size: 40px"> 
                    **{} - {}** :
                    """.format(module, pre_function), unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(
            """ 🏠简介：在计算点云偏差云图前进行的一系列点云预处理工作，首先进行BIM的点云离散以获取标准点云，其次对扫描点云进行下采样以实现轻量化加快数据处理速度，再次进行扫描点云和标准点云的配准，最后计算误差云图并输出报告 """)

    if pre_function == '网格离散':
        pre_function2 = st.sidebar.radio("模块", ['说明书', '网格离散'])

        if pre_function2 == "说明书":
            st.markdown("""<b style="color:black; 
                                       font-family:KaiTi_GB2312; 
                                       font-style:norm; font-size: 40px"> 
                                       **{} - {}** :
                                       """.format(pre_function, pre_function2), unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(""" 🏠简介：计算扫描点云和BIM模型的差异，对构件及结构整体尺寸质量进行评估，因此需进行BIM的格式转换。
                        本软件采用:red[泊松圆盘采样(Poisson-Disk Sampling)]来实现网格文件与点云文件的格式转换。
                               """)
            st.markdown("---")
            st.markdown("""<b style="color:gray; 
                                       font-style:norm; font-size: 20px"> 
                                       :cat2:**泊松圆盘采样**
                                    """, unsafe_allow_html=True)
            st.markdown("""在一个宽高分别为w,h的网格平面内平均生成一堆的点，且这些点之间的距离不能小于采样半径R""")
            st.markdown(":blue[输入参数：] ")
            st.markdown(""" 输入点云：网格文件，支持后缀：stl/ply/obj/off/gltf/glb""")
            st.markdown(""" 点云间距：离散后点云的平均间距""")
            st.markdown("---")

        if pre_function2 == "网格离散":
            inforA = 0
            st.markdown("""<b style="color:gray; 
                                       font-style:norm; font-size: 30px"> 
                                       :cat2:**网格离散**
                                    """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
                                   <b style="color:gray; 
                                   font-family:Times New Roman; 
                                   font-style:norm; 
                                   font-size: 25px"> 
                                    **步骤1：输入点云**
                                    """, unsafe_allow_html=True)

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button('选择网格文件'):
                    input_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    input_path_save = os.path.join(cache_path, "Tool_BIM2PCD_Input.txt")
                    with open(input_path_save, "w") as f:
                        f.write(input_path)
            with col2:
                if st.button('选择保存文件夹'):
                    output_path = filedialog.askdirectory(master=root)
                    output_path_save = os.path.join(cache_path, "Tool_BIM2PCD_Output.txt")
                    with open(output_path_save, "w") as f:
                        f.write(output_path)

            st.markdown("---")
            st.markdown("""
                                   <b style="color:gray; 
                                   font-family:Times New Roman; 
                                   font-style:norm; 
                                   font-size: 25px"> 
                                    **步骤2：输入点云间距**
                                    """, unsafe_allow_html=True)
            st.write('你正在使用网格离散功能!')
            distance_pcd = st.text_input("请输入点云间距：", '0.2')

            try:
                distance_pcd = float(distance_pcd)
                inforA = 1
            except:
                inforA = 0

            if st.button('开始离散'):
                # 读取输入和输出路径
                input_file = os.path.join(cache_path, "Tool_BIM2PCD_Input.txt")
                output_file = os.path.join(cache_path, "Tool_BIM2PCD_Output.txt")

                if not os.path.exists(input_file) or not os.path.exists(output_file):
                    st.error("请先选择网格文件和保存文件夹！")
                    st.stop()

                with open(input_file, "r") as f:
                    input_path = f.read()
                with open(output_file, "r") as f:
                    output_path = f.read()

                mesh_name_with_suffix = os.path.split(input_path)[-1]  # 获得带后缀的网格名称
                mesh_name = mesh_name_with_suffix.split('.')[0]
                st.write('当前点间距为：', distance_pcd)
                st.write('开始采样，请耐心等待....')

                # 执行网格离散
                pcd = Mesh_to_PCD(input_path, distance_pcd)

                st.write(f"采样完成,总点数为:red[{len(pcd)}]")
                vd = show(pcd, w=300, h=300, size=1, color='blue')
                stpv(vd)

                # 保存结果
                save_path = os.path.join(output_path, f"{mesh_name}.xyz")
                np.savetxt(save_path, pcd)
                st.success(f"结果已保存到: {save_path}")

            if st.button('打开输出文件夹'):
                try:
                    output_file = os.path.join(cache_path, "Tool_BIM2PCD_Output.txt")
                    if os.path.exists(output_file):
                        with open(output_file, "r") as f:
                            output_path = f.read()
                        if sys.platform == "win32":
                            os.startfile(output_path)
                        elif sys.platform == "darwin":  # macOS
                            subprocess.Popen(["open", output_path])
                        else:  # Linux
                            subprocess.Popen(["xdg-open", output_path])
                    else:
                        st.caption(':red[_无输出文件夹信息_]')
                except Exception as e:
                    st.error(f"无法打开文件夹: {e}")
    if pre_function == '尺寸缩放':
        pre_function2 = st.sidebar.radio("模块", ['说明书', '尺寸缩放'])
        st.sidebar.text('更多功能敬请期待')
        if pre_function2 == '说明书':
            st.markdown("""<b style="color:black; 
                                  font-family:KaiTi_GB2312; 
                                  font-style:norm; font-size: 40px"> 
                                  **{} - {}** 
                                  """.format(pre_function, pre_function2), unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(""" 🏠简介：\n
            \n 本软件默认单位为m,与常用扫描仪单位一致;\n
            \n 当采用手持扫描仪时，点云单位通常为mm;\n
            \n BIM模型单位亦存在为m的情况;\n
            \n可通过本模块将点云单位进行更改
                          """)
        if pre_function2== "尺寸缩放":
            st.markdown("""<b style="color:gray; 
                                       font-style:norm; font-size: 30px"> 
                                       :leopard:**尺寸缩放**
                                        """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""<b style="color:gray; 
                                       font-family:Times New Roman; 
                                       font-style:norm; 
                                       font-size: 25px"> 
                                        **步骤1：输入点云信息**
                                        """, unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button('选择待转换点云'):
                    input_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    input_path_save = os.path.join(cache_path, "Tool_Scale_Input.txt")
                    with open(input_path_save, "w") as f:
                        f.write(input_path)
            with col2:
                if st.button('选择输出文件夹'):
                    output_path = filedialog.askdirectory(master=root)
                    output_path_save = os.path.join(cache_path,"Tool_Scale_Output.txt")
                    with open(output_path_save, "w") as f:
                        f.write(output_path)
            st.markdown("---")
            st.markdown("""
                                  <b style="color:gray; 
                                  font-family:Times New Roman; 
                                  font-style:norm; 
                                  font-size: 25px"> 
                                   **步骤2：输入转换参数**
                                   """, unsafe_allow_html=True)
            Dictionary={'m':1,'dm':0.1,'cm':0.01,'mm':0.001}
            col3,col4=st.columns([1,1])
            with col3:
                origin=st.selectbox(label="原始单位",options=('m','dm','cm','mm'))
            with col4:
                target=st.selectbox(label="目标单位",options=('m','dm','cm','mm'))
            if st.button('开始转换'):
                Coefficient=float(Dictionary[origin]/Dictionary[target])
                st.write(f"原始单位为:red[{origin}],目标单位为:red[{target}],转换系数为:red[{Coefficient}]")
                with open(os.path.join(cache_path ,"Tool_Scale_Input.txt"), "r") as f:
                    input_path = f.read()
                with open(os.path.join(cache_path , "Tool_Scale_Output.txt"), "r") as f:
                    output_path = f.read()
                PCD_name_with_suffix = os.path.split(input_path)[-1]  # 获得带后缀的点云名称
                PCD_name = PCD_name_with_suffix.split('.')[0]
                pcd=data_load(input_path)*Coefficient
                output_path=os.path.join(output_path,PCD_name+"_"+target+".xyz")
                np.savetxt(output_path,pcd)
                st.write("转换完成！")
            if st.button('打开输出文件夹'):
                try:
                    with open(os.path.join(cache_path ,"Tool_Scale_Output.txt"), "r") as f:  # 读取该文件夹地址
                        output_path = f.read()
                    os.startfile(output_path)
                except:
                    st.caption(':red[_无输出文件夹信息_]')

    if pre_function == '下采样':
        pre_function2 = st.sidebar.radio("下采样方式", ['工具说明书', '体素下采样', '均匀下采样'])
        if pre_function2 == '工具说明书':
            st.markdown("""<b style="color:black; 
                           font-family:KaiTi_GB2312; 
                           font-style:norm; font-size: 40px"> 
                           **{} - {}** 
                           """.format(pre_function, pre_function2), unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(""" 🏠简介：点云数据通常数据量庞大,数据冗余度高。为了降低计算成本，需要从大量数据点中筛选出能够较好保留数据特征的点云，用来替代原点云数据进行相关操作。
            筛选的过程就是下采样 (也称降采样)，其本质就是将点云数据均匀化和轻量化的过程。本软件包含点云下采样的常用方法：:red[体素下采样、均匀下采样]。
                   """)
            st.markdown("---")
            st.markdown("""<b style="color:gray; 
                           font-style:norm; font-size: 20px"> 
                           :cat2:**体素下采样**
                        """, unsafe_allow_html=True)
            st.markdown("""将点云数据集所占据的三维空间划分成多个体素，以每个体素中所有点计算得到的重心作为采样点。""")
            st.markdown(":blue[输入参数：] ")
            st.markdown(""" 输入点云：文件路径（单个点云）""")
            st.markdown(""" 体素尺寸：体素尺寸越大，采样程度越高。""")
            st.markdown("---")

            st.markdown("""<b style="color:gray; 
                           font-style:norm; font-size: 20px"> 
                           :cat2:**均匀下采样**
                            """, unsafe_allow_html=True)
            st.markdown("""将点云数据按照索引顺序，从第一个点开始，以固定间隔进行采样。""")
            st.markdown(":blue[输入参数：] ")
            st.markdown(""" 输入点云：文件路径（单个点云）""")
            st.markdown(""" 采样间隔：采样间隔越大，采样程度越高。""")

        if pre_function2 == '体素下采样':
            inforA=0
            st.markdown("""<b style="color:gray; 
                           font-style:norm; font-size: 30px"> 
                           :cat2:**体素下采样**
                        """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
                       <b style="color:gray; 
                       font-family:Times New Roman; 
                       font-style:norm; 
                       font-size: 25px"> 
                        **步骤1：输入点云**
                        """, unsafe_allow_html=True)
            col1,col2=st.columns([1,1])
            with col1:
                if st.button('选择点云文件'):
                    input_path=filedialog.askopenfilename(master=root)#弹窗选择文件，返回文件绝对路径
                    input_path_save=os.path.join(cache_path,"Tool_Sampling_Voxel_Input.txt")
                    with open(input_path_save,"w") as f:
                        f.write(input_path)
            with col2:
                if st.button('选择保存文件夹'):
                    output_path=filedialog.askdirectory(master=root)
                    output_path_save=os.path.join(cache_path,"Tool_Sampling_Voxel_Output.txt")
                    with open(output_path_save,"w") as f:
                        f.write(output_path)
            st.markdown("---")
            st.markdown("""
                       <b style="color:gray; 
                       font-family:Times New Roman; 
                       font-style:norm; 
                       font-size: 25px"> 
                        **步骤2：输入采样的体素尺寸**
                        """, unsafe_allow_html=True)
            st.write('你正在使用体素下采样功能，体素尺寸越大，下采样程度越高!')
            voxel_size = st.text_input("请输入下采样的体素尺寸：", '0.01')
            try:
                voxel_size=float(voxel_size)
                inforA=1
            except:
                inforA = 0
            if inforA==1 and voxel_size > 0:
                st.write(f'当前体素尺寸为:red[{voxel_size}]!')
            if st.button('开始下采样'):
                with open(os.path.join(cache_path, "Tool_Sampling_Voxel_Input.txt"), "r") as f:
                    input_path=f.read()
                    PCD_name_with_suffix = os.path.split(input_path)[-1]  # 获得带后缀的点云名称
                    PCD_name = PCD_name_with_suffix.split('.')[0]
                    pcd=data_load(input_path)
                    v_down_pcd = voxel_downsample(pcd, voxel_size)
                    st.write('当前采样体素尺寸为：', voxel_size)
                    st.write(f"原始点云共有{len(pcd)}个点，体素下采样后点云共有{len(v_down_pcd)}个点!")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        vd = show(pcd, w=300,h=300,size=1, color='grey')
                        stpv(vd)
                    with col2:
                        vd1 = show(v_down_pcd, w=300,h=300,size=1, color='red')
                        stpv(vd1)
                    recommend_path = PCD_name+"_VD.xyz"
                    with open(os.path.join(cache_path ,"Tool_Sampling_Voxel_Output.txt")) as f:
                        output_path=f.read()
                    save_path=os.path.join(output_path,recommend_path)
                    np.savetxt(save_path, v_down_pcd)
            if st.button('打开输出文件夹'):
                try:
                    with open(os.path.join(cache_path, "Tool_Sampling_Voxel_Output.txt"), "r") as f:#读取该文件夹地址
                        output_path = f.read()
                    os.startfile(output_path)
                except:
                    st.caption(':red[_无输出文件夹信息_]')


        if pre_function2 == '均匀下采样':
            inforA = 0
            st.markdown("""<b style="color:gray; 
                                       font-style:norm; font-size: 30px"> 
                                       :cat2:**均匀下采样**
                                    """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
                                   <b style="color:gray; 
                                   font-family:Times New Roman; 
                                   font-style:norm; 
                                   font-size: 25px"> 
                                    **步骤1：输入点云**
                                    """, unsafe_allow_html=True)
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button('选择点云文件'):
                    input_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    input_path_save = os.path.join(cache_path , "Tool_Sampling_Uniform_Input.txt")
                    with open(input_path_save, "w") as f:
                        f.write(input_path)
            with col2:
                if st.button('选择保存文件夹'):
                    output_path = filedialog.askdirectory(master=root)
                    output_path_save = os.path.join(cache_path , "Tool_Sampling_Uniform_Output.txt")
                    with open(output_path_save, "w") as f:
                        f.write(output_path)
            st.markdown("---")
            st.markdown("""
                                       <b style="color:gray;
                                       font-family:Times New Roman;
                                       font-style:norm;
                                       font-size: 25px">
                                        **步骤2：输入采样间隔**
                                        """, unsafe_allow_html=True)
            st.write('你正在使用均匀下采样功能，采样比例越小，下采样程度越高!')
            k_num = st.text_input("请输入采样间隔:", '2')
            try:
                k_num = int(k_num)
                inforA = 1
            except:
                inforA = 0
            if inforA == 1 and k_num > 0:
                st.write(f'当前采样间隔为:red[{k_num}]!')
            if st.button('开始下采样'):
                with open(os.path.join(cache_path , "Tool_Sampling_Uniform_Input.txt"), "r") as f:
                    input_path = f.read()
                    PCD_name_with_suffix = os.path.split(input_path)[-1]  # 获得带后缀的点云名称
                    PCD_name = PCD_name_with_suffix.split('.')[0]
                    pcd = data_load(input_path)
                    u_down_pcd = uniform_downsample(pcd, k_num)
                    st.write(f'当前采样间隔为{k_num}!')
                    st.write(f"原始点云共有{len(pcd)}个点，均匀下采样后点云共有{len(u_down_pcd)}个点!")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        vd = show(pcd, w=300, h=300, size=1, color='grey')
                        stpv(vd)
                    with col2:
                        vd1 = show(u_down_pcd, w=300, h=300, size=1, color='red')
                        stpv(vd1)
                    recommend_path = PCD_name + "_UD.xyz"
                    with open(os.path.join(cache_path ,"Tool_Sampling_Uniform_Output.txt")) as f:
                        output_path = f.read()
                    save_path = os.path.join(output_path,recommend_path)
                    np.savetxt(save_path, u_down_pcd)
            if st.button('打开输出文件夹'):
                try:
                    with open(os.path.join(cache_path , "Tool_Sampling_Uniform_Output.txt"), "r") as f:  # 读取该文件夹地址
                        output_path = f.read()
                    os.startfile(output_path)
                except:
                    st.caption(':red[_无输出文件夹信息_]')

    if pre_function == '配准':
        pre_function2 = st.sidebar.radio("配准方式", ['说明书', '粗配准', '精配准'])
        if pre_function2 == '说明书':
            st.markdown("""<b style="color:black; 
                                  font-family:KaiTi_GB2312; 
                                  font-style:norm; font-size: 40px"> 
                                  **{} - {}** :book:
                                  """.format(pre_function, pre_function2), unsafe_allow_html=True)
            st.markdown("---")
            st.markdown(""" 🏠简介：
            \n 点云数据配准就是将不同坐标系中的数据点通过坐标变换的方式统一到同一坐标系中；
            变换过程中，通常将保持不动的点云数据称为目标点云数据，需要进行变换的数据称为源点云数据。
            点云配准实际上是寻找目标点云数据与源点云数据之间的刚性变换矩阵（旋转矩阵R和平移矩阵T），以实现二者之间的最优匹配。
            点云配准分为:red[粗配准（Coarse Registration）]和:red[精配准（Fine Registration）]两个阶段。\n
            \n :red[粗配准（Coarse Registration）]：在源点云与目标点云初始相对位置未知的情况下，进行粗略配准。
            该方法的主要目的是在初始条件未知的情况下，快速估算一个大致的点云配准矩阵。
            对于任意初始状态的两片点云，使得两片点云大致对齐，给旋转矩阵R和平移向量T提供初值。\n
            \n :red[精配准（Fine Registration）]：在粗配准的基础上，进行更精确、更细化的配准。
            精配准是利用已知的初始变换矩阵，通过迭代最近点算法（ICP算法）等计算得到较为精确的解。\n
            \n 本软件提供采用FPFH特征进行点云粗配准，ICP进行点云精配准的解决方案，用于扫描点云和BIM点云的对齐。\n
            \n 各站点云配准，请使用扫描仪自带软件 \n
                          """)

        if pre_function2 == '粗配准':
            st.markdown("""<b style="color:gray; 
                           font-style:norm; font-size: 30px"> 
                           :leopard:**基于FPFH特征的配准**
                            """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""
                       <b style="color:gray; 
                       font-family:Times New Roman; 
                       font-style:norm; 
                       font-size: 25px"> 
                        **步骤1：输入点云信息**
                        """, unsafe_allow_html=True)
            col1, col2,col3 = st.columns([1, 1, 1])
            with col1:
                if st.button('选择移动点云'):
                    SCENE_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    SCENE_path_save = os.path.join(cache_path , "Tool_Registration_FPFH_SCENE.txt")
                    with open(SCENE_path_save, "w") as f:
                        f.write(SCENE_path)
            with col2:
                if st.button('选择固定点云'):
                    BIM_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    BIM_path_save = os.path.join(cache_path , "Tool_Registration_FPFH_BIM.txt")
                    BIM_path_save2=os.path.join(cache_path,"Tool_Registration_ICP_BIM.txt")
                    with open(BIM_path_save, "w") as f:
                        f.write(BIM_path)
                    with open(BIM_path_save2,"w") as f:
                        f.write(BIM_path)
            with col3:
                if st.button('选择保存文件夹'):
                    output_path = filedialog.askdirectory(master=root)
                    output_path_save = os.path.join(cache_path , "Tool_Registration_FPFH_Output.txt")
                    output_path_save2=os.path.join(cache_path,"Tool_Registration_ICP_Output.txt")
                    with open(output_path_save, "w") as f:
                        f.write(output_path)
                    with open(output_path_save2,"w") as f:
                        f.write(output_path)
            st.markdown("---")

            st.markdown("""
                       <b style="color:gray; 
                       font-family:Times New Roman; 
                       font-style:norm; 
                       font-size: 25px"> 
                        **步骤2：输入体素大小**
                        """, unsafe_allow_html=True)
            voxel_size = st.text_input('体素大小', '0.3')
            voxel_size=float(voxel_size)
            st.markdown("---")
            if st.button('开始配准'):
                st.markdown(""" <b style="color:gray; 
                                   font-family:Times New Roman; 
                                   font-style:norm; 
                                   font-size: 20px"> 
                                    **正在配准，请勿操作界面直至配准结束！！！**
                                    """, unsafe_allow_html=True)
                with open(os.path.join(cache_path , "Tool_Registration_FPFH_SCENE.txt"), "r") as f:
                    SCENE_path = f.read()
                with open(os.path.join(cache_path , "Tool_Registration_FPFH_BIM.txt"), "r") as f:
                    BIM_path = f.read()
                with open(os.path.join(cache_path , "Tool_Registration_FPFH_Output.txt"), "r") as f:
                    output_path = f.read()
                PCD_name_with_suffix = os.path.split(SCENE_path)[-1]  # 获得带后缀的点云名称
                PCD_name = PCD_name_with_suffix.split('.')[0]
                pcd_scene=data_load(SCENE_path)
                pcd_bim=data_load(BIM_path)
                col4,col5=st.columns([1,1])
                st.write('读取点云文件')
                with col4:
                    st.write('待配准点云')
                    vd = show(pcd_scene, w=300, h=300, size=1, color='red')
                    stpv(vd)
                with col5:
                    st.write('固定点云')
                    vd1 = show(pcd_bim, w=300, h=300, size=1, color='blue')
                    stpv(vd1)
                st.write('执行配准程序')
                pcd_scene2bim=FPFH_Registration(SCENE_path,BIM_path,voxel_size)
                save_path=os.path.join(output_path,PCD_name+"_FPFH.xyz")
                np.savetxt(save_path,pcd_scene2bim)
                save_path_path=os.path.join(cache_path , "Tool_Registration_ICP_SCENE.txt")
                with open(save_path_path, "w") as f:
                    f.write(save_path)
                vd2=show2(pcd_scene2bim,pcd_bim,w=600,h=300,size1=1,size2=1,color1="red",color2="blue")
                stpv(vd2)
                st.markdown(""" <b style="color:gray; 
                                                   font-family:Times New Roman; 
                                                   font-style:norm; 
                                                   font-size: 20px"> 
                                                    **请检查粗配准效果，不理想时请重新运行程序**
                                                    """, unsafe_allow_html=True)
            if st.button('打开输出文件夹'):
                try:
                    with open(os.path.join(cache_path , "Tool_Registration_FPFH_Output.txt"), "r") as f:  # 读取该文件夹地址
                        output_path = f.read()
                    os.startfile(output_path)
                except:
                    st.caption(':red[_无输出文件夹信息_]')


        if pre_function2 == '精配准':
            st.markdown("""<b style="color:gray; 
                           font-style:norm; font-size: 30px"> 
                           :leopard:**基于ICP算法的精配准**
                            """, unsafe_allow_html=True)
            st.markdown("---")
            st.markdown("""<b style="color:gray; 
                           font-family:Times New Roman; 
                           font-style:norm; 
                           font-size: 25px"> 
                            **步骤1：输入点云信息**
                            """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button('选择移动点云'):
                    SCENE_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    SCENE_path_save = os.path.join(cache_path , "Tool_Registration_ICP_SCENE.txt")
                    with open(SCENE_path_save, "w") as f:
                        f.write(SCENE_path)
            with col2:
                if st.button('选择固定点云'):
                    BIM_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    BIM_path_save = os.path.join(cache_path , "Tool_Registration_ICP_BIM.txt")
                    with open(BIM_path_save, "w") as f:
                        f.write(BIM_path)
            with col3:
                if st.button('选择保存文件夹'):
                    output_path = filedialog.askdirectory(master=root)
                    output_path_save = os.path.join(cache_path , "Tool_Registration_ICP_Output.txt")
                    with open(output_path_save, "w") as f:
                        f.write(output_path)
            st.markdown("---")
            st.markdown("""
                      <b style="color:gray; 
                      font-family:Times New Roman; 
                      font-style:norm; 
                      font-size: 25px"> 
                       **步骤2：输入配准参数**
                       """, unsafe_allow_html=True)
            col4, col5, col6 = st.columns([1, 1, 1])
            with col4:
                Parameter1 = st.text_input('第一次精配阈值(m):', '0.05')
            with col5:
                Parameter2 = st.text_input('第二次精配阈值(m):', '0.03')
            with col6:
                Parameter3 = st.text_input('第三次精配阈值(m):', '0.005')
            st.write('______________________________')
            Parameter1 = float(Parameter1)
            Parameter2 = float(Parameter2)
            Parameter3 = float(Parameter3)
            if st.button('开始配准'):
                st.markdown(""" <b style="color:gray; 
                                   font-family:Times New Roman; 
                                   font-style:norm; 
                                   font-size: 20px"> 
                                    **正在配准，请勿操作界面直至配准结束！！！**
                                    """, unsafe_allow_html=True)
                with open(os.path.join(cache_path ,"Tool_Registration_ICP_SCENE.txt"), "r") as f:
                    SCENE_path = f.read()
                with open(os.path.join(cache_path ,"Tool_Registration_ICP_BIM.txt"), "r") as f:
                    BIM_path = f.read()
                with open(os.path.join(cache_path , "Tool_Registration_ICP_Output.txt"), "r") as f:
                    output_path = f.read()
                PCD_name_with_suffix = os.path.split(SCENE_path)[-1]  # 获得带后缀的点云名称
                PCD_name = PCD_name_with_suffix.split('.')[0]
                pcd_scene = data_load(SCENE_path)
                pcd_bim = data_load(BIM_path)
                col4, col5 = st.columns([1, 1])
                st.write('读取点云文件')
                vd = show2(pcd_scene, pcd_bim, w=600, h=300, size1=1, size2=1, color1="red", color2="blue")
                stpv(vd)
                st.write('执行配准程序')
                pcd_scene_ICP1=Open3d_ICP(pcd_scene,pcd_bim,Parameter1)
                st.write(f'阈值为:red[{Parameter1}]的ICP已完成')
                pcd_scene_ICP2=Open3d_ICP(pcd_scene_ICP1,pcd_bim,Parameter2)
                st.write(f'阈值为:red[{Parameter2}]的ICP已完成')
                pcd_scene_ICP = Open3d_ICP(pcd_scene_ICP2, pcd_bim, Parameter3)
                st.write(f'阈值为:red[{Parameter3}]的ICP已完成')
                vd2=show2(pcd_scene_ICP,pcd_bim,w=600,h=300,size1=1,size2=1,color1="red",color2="blue")
                stpv(vd2)
                save_path=os.path.join(output_path,PCD_name+"_ICP.xyz")
                np.savetxt(save_path,pcd_scene_ICP)
            if st.button('打开输出文件夹'):
                try:
                    with open(os.path.join(cache_path,"/Tool_Registration_FPFH_Output.txt"), "r") as f:  # 读取该文件夹地址
                        output_path = f.read()
                    os.startfile(output_path)
                except:
                    st.caption(':red[_无输出文件夹信息_]')




