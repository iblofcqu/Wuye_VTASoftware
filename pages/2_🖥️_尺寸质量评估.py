import numpy as np
import streamlit as st
from PIL import Image
from functions.load_data import *
from functions.draw_functions import *
from stpyvista import stpyvista
from functions.draw_functions import *
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
from functions.PDF import *
from PIL import Image
from stpyvista import stpyvista as stpv
from functions.knn import *
from functions.down_samples import *
import kaleido
import sys
import multiprocessing
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


    st.set_page_config(page_title="几何质量评估", page_icon="📏")
    pre_function = st.sidebar.radio("功能选择", ['模块简介', '几何质量评估'])
    if pre_function == '模块简介':
        st.subheader('几何质量评估-说明书🔩')
        st.markdown(""" 🏠简介：
                    \n 对比扫描点云和设计模型之间的偏差 \n
                    \n 本模块使用前，请首先完成扫描点云和BIM离散点云的配准 \n
                    \n 具体功能，参见:red[点云预处理]
                                  """)

    if pre_function == '几何质量评估':
        st.markdown("""<b style="color:gray; 
                                       font-style:norm; font-size: 30px"> 
                                       :leopard:**几何质量评估**
                                        """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("""<b style="color:gray; 
                                       font-family:Times New Roman; 
                                       font-style:norm; 
                                       font-size: 25px"> 
                                        **步骤1：预处理信息确认**
                                        """, unsafe_allow_html=True)
        one = st.checkbox('我已获取:red[离散点云]')
        two = st.checkbox('我已完成:red[下采样]（可忽略）')
        three = st.checkbox('我已检查离散点云和扫描点云:red[单位一致]')
        four = st.checkbox('我已进行扫描点云和离散点云的:red[匹配]')
        if one and two and three and four:
            st.markdown("---")
            st.markdown("""<b style="color:gray; 
                                                   font-family:Times New Roman; 
                                                   font-style:norm; 
                                                   font-size: 25px"> 
                                                    **步骤2：数据信息输入**
                                                    """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button('选择扫描点云'):
                    SCENE_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    SCENE_path_save = os.path.join(cache_path ,"QA_pcd.txt")
                    with open(SCENE_path_save, "w") as f:
                        f.write(SCENE_path)
            with col2:
                if st.button('选择BIM点云'):
                    BIM_path = filedialog.askopenfilename(master=root)  # 弹窗选择文件，返回文件绝对路径
                    BIM_path_save = os.path.join(cache_path ,"QA_BIM.txt")
                    with open(BIM_path_save, "w") as f:
                        f.write(BIM_path)
            with col3:
                if st.button('选择报告保存文件夹'):
                    output_path = filedialog.askdirectory(master=root)
                    output_path_save = os.path.join(cache_path , "QA_Report.txt")
                    with open(output_path_save, "w") as f:
                        f.write(output_path)
            st.markdown("---")
            st.markdown("""<b style="color:gray; 
                                                               font-family:Times New Roman; 
                                                               font-style:norm; 
                                                               font-size: 25px"> 
                                                                **步骤3：参数信息**
                                                                """, unsafe_allow_html=True)
            col4,col5,col6=st.columns([1,1,1])
            with col4:
                unit = st.selectbox(label="点云单位", options=('m', 'dm', 'cm', 'mm'))
            with col5:
                method = st.selectbox(label="偏差计算方法", options=('Point2Point', 'Point2Plane'))
            with col6:
                distance=st.text_input('平面邻域大小(Point2Plane有效)', '0.01')
            ratio=st.text_input('需剔除的点数比例(即考虑缺失点云剔除的偏差最大的点数与总检测点数量的比值)',"0.05")
            st.write('______________________________')
            distance=float(distance)
            ratio=float(ratio)
            if st.button('计算偏差并生成报告'):
                st.markdown(""" <b style="color:gray; 
                                                   font-family:Times New Roman; 
                                                   font-style:norm; 
                                                   font-size: 20px"> 
                                                    **正在计算偏差，请勿操作界面直至报告输出！！！**
                                                    """, unsafe_allow_html=True)
                with open(os.path.join(cache_path,"QA_pcd.txt"), "r") as f:
                    SCENE_path = f.read()
                PCD_name_with_suffix = os.path.split(SCENE_path)[-1]  # 获得带后缀的点云名称
                PCD_name = PCD_name_with_suffix.split('.')[0]
                with open(os.path.join(cache_path , "QA_BIM.txt"), "r") as f:
                    BIM_path = f.read()
                with open(os.path.join(cache_path,"QA_Report.txt"), "r") as f:
                    output_path = f.read()
                col7,col8=st.columns([1,1])
                with col7:
                    step1 = st.empty()
                    step1.write("🏃‍♂️正在进行第1/4步，文件读取")
                    pcd_scene=data_load(SCENE_path)
                    draw1(os.path.join(cache_path,"fig1a.jpg"),pcd_scene,1,'red')
                    pcd_bim=data_load(BIM_path)
                    draw1(os.path.join(cache_path ,"fig1b.jpg"), pcd_bim, 1, 'blue')
                    step1.write("✔️第1/4步-文件读取完成")
                    vd1=show2(pcd_scene,pcd_bim,300,300,1,1,'red','blue')
                    stpv(vd1)
                    draw2(os.path.join(cache_path,"fig2.jpg"),pcd_scene,pcd_bim,1,1,'red','blue')
                with col8:
                    step2=st.empty()
                    step2.write("🏃‍♂️正在进行第2/4步，环境点云及缺失点云剔除")
                    pcd_bim_down=voxel_downsample(pcd_bim,0.1)
                    pcd_scene_clean=find_r(pcd_bim_down,pcd_scene,r=distance*10)#找BIM在SCEN中的最近点，剔除环境点云
                    draw1(os.path.join(cache_path,"fig3.jpg"),pcd_scene_clean,1,'red')
                    check_pt=find_k(pcd_scene_clean,pcd_bim,k=1)#找无环境信息的SCEN点云在BIM中的最近点，排除缺失部分
                    draw1(os.path.join(cache_path,"fig4.jpg"),check_pt,1,'blue')
                    vd2=show2(pcd_scene_clean,check_pt,300,300,1,2,'red','blue')
                    stpv(vd2)
                    step2.write("✔️第2/4步-环境点云及缺失点云剔除完成")

                step3 = st.empty()
                step3.write(f"🏃‍♂️正在进行第3/4步，偏差计算,使用的方法为{method}")
                if method=='Point2Point':
                    error=Error_caculate_Point2Point(check_pt,pcd_scene_clean,k=1)
                    vd3=show_error(check_pt,error*1000,300,300,2,ratio)
                    draw_error2(os.path.join(cache_path, 'fig5.jpg'), check_pt, error * 1000, 2, ratio)
                    stpv(vd3)
                    step3.write("✔️第3/4步-偏差计算完成")
                if method=="Point2Plane":
                    error=Error_caculate_Point2Plane(check_pt,pcd_scene_clean,r=distance)
                    vd3 = show_error(check_pt, error * 1000, 300, 300, 2,ratio)
                    draw_error2(os.path.join(cache_path,'fig5.jpg'),check_pt, error * 1000, 2,ratio)
                    stpv(vd3)
                    step3.write("✔️第3/4步-偏差计算完成")
                step4=st.empty()
                step4.write(f"🏃‍♂️正在进行第4/4步，偏差统计并生成报告")
                error_sorted=sorted(error*1000,reverse=True)
                line_number=int(len(error_sorted)*ratio)
                line=error_sorted[line_number]
                fig=show_clum(error_sorted,step=1,ratio=ratio,cut_line=line,IS=4)
                fig.write_image(os.path.join(cache_path,"Error_Analysis.jpg"),format="png",scale=2)
                step4.write("✔️第4/4步-偏差统计完成")
                st.title('偏差分布直方图')
                st.plotly_chart(fig, use_container_width=True)
                st.subheader("偏差统计指标")
                mean_val = np.mean(error_sorted)
                max_val = np.max(error_sorted)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("检测点数", len(error_sorted))
                col2.metric(f"剔除{ratio}后最大值", f"{line:.2f}")
                col3.metric("最大值", f"{max_val:.2f}")
                col4.metric("平均值", f"{mean_val:.2f}")
                basic_information = {'PCD_name':str(PCD_name),'SCENE_path':str(SCENE_path),'BIM_path':str(BIM_path),'unit':str(unit),'method':str(method),'distance':float(distance),'ratio':float(ratio),'len_pcd_scene':int(len(pcd_scene)),'len_pcd_bim':int(len(pcd_bim)),'check_num':int(len(error_sorted)),'error_max_cut':float(f"{line:.2f}"),'error_max':float(f"{max_val:.2f}"),'error_mean':float(f"{mean_val:.2f}")}
                QA_Report(cache_path,output_path,basic_information)
            if st.button('打开输出文件夹'):
                try:
                    with open(os.path.join(cache_path, "QA_Report.txt"), "r") as f:  # 读取该文件夹地址
                        output_path = f.read()
                    os.startfile(output_path)
                except:
                    st.caption(':red[_无输出文件夹信息_]')
        else:
            st.write(':red[当前数据尚未满足检测条件]')




