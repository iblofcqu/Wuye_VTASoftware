import numpy as np
import pyvista as pv
import streamlit as st
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors
from matplotlib.colors import ListedColormap
import stpyvista
import plotly.graph_objects as go
# 方法一： 使用Mesh画图 1）只展示点  2）既展示点又展示中心轴线（或者其他线）

def draw1(save_path, point_array,size=1,color='red'):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array), color=color, render_points_as_spheres=True, point_size=size)
    p.set_background('w')
    p.screenshot(save_path)
    # p.show(title="输入点云")

# def show(point_array,title):
#
#     plotter = pv.Plotter(window_size=[700, 700])
#     plotter.add_mesh(pv.PolyData(point_array), color='red', render_points_as_spheres=True, point_size=1)
#     plotter.background_color = 'white'
#     plotter.view_isometric()
#     plotter.add_title(title,font_size=18, color=None, font=None, shadow=False)
#     return plotter

def stpv_usage_example(dummy:str = "cube"):
    ## Initialize a plotter object
    plotter = pv.Plotter(window_size=[400, 400])
    ## Create a mesh with a cube
    mesh = pv.Cube(center=(0, 0, 0))
    ## Add some scalar field associated to the mesh
    mesh["myscalar"] = mesh.points[:, 2] * mesh.points[:, 1] * mesh.points[:, 0]
    ## Add mesh to the plotter
    plotter.add_mesh(
        mesh,
        scalars="myscalar",
        cmap="bwr",
        show_edges=True,
        edge_color="#001100")
    ## Final touches
    plotter.background_color = "grey"
    plotter.view_isometric()
    return plotter

def drawtest(point_array):
    # 通过添加mesh的方法绘图
    p = pv.Plotter()  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array), color='red', render_points_as_spheres=True, point_size=1)
    p.set_background('w')
    p.show()

def draw1big2(point_array,point_array1):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array), color='red', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array1), color='blue', render_points_as_spheres=True, point_size=5)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def draw2(save_path,point_array1,point_array2,size1=1,size2=1,color1='red',color2='blue'):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array1[:,:3]), color=color1, render_points_as_spheres=True, point_size=size1)
    p.add_mesh(pv.PolyData(point_array2[:,:3]), color=color2, render_points_as_spheres=True, point_size=size2)
    p.set_background('w')
    p.screenshot(save_path)
    # return save_path

def draw3(point_array,point_array1,point_array2):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array[:,:3]), color='red', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array1[:,:3]), color='blue', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array2[:, :3]), color='blue', render_points_as_spheres=True, point_size=2)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def draw2bigsmall(point_array,point_array1):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array[:,:3]), color='red', render_points_as_spheres=True, point_size=10)
    p.add_mesh(pv.PolyData(point_array1[:,:3]), color='blue', render_points_as_spheres=True, point_size=2)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def draw2big(point_array,point_array1):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array[:,:3]), color='red', render_points_as_spheres=True, point_size=10)
    p.add_mesh(pv.PolyData(point_array1[:,:3]), color='blue', render_points_as_spheres=True, point_size=10)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def draw3small1big(point_array,point_array1,point_array2,point_array3):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array[:,:3]), color='red', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array1[:,:3]), color='blue', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array2[:, :3]), color='blue', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array3[:, :3]), color='black', render_points_as_spheres=True, point_size=10)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def draw2small2big(point_array,point_array1,point_array2,point_array3):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array[:,:3]), color='red', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array1[:,:3]), color='blue', render_points_as_spheres=True, point_size=2)
    p.add_mesh(pv.PolyData(point_array2), color='red', render_points_as_spheres=True, point_size=10)
    p.add_mesh(pv.PolyData(point_array3), color='blue', render_points_as_spheres=True, point_size=10)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def show_centralaxis(point_array, centralaxis):
    # 通过添加mesh的方法绘图
    p = pv.Plotter()  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array), color='red', render_points_as_spheres=True, point_size=4)
    p.add_mesh(pv.PolyData(centralaxis), color='yellow', render_points_as_spheres=True, point_size=10)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

# 方法二：误差彩色编码图

def Show_dimensional_error(point_array_1, point_array_2):
    '''
    :param point_array_1: 源点云数据
    :param point_array_2: 目标点云数据
    :return: 误差彩色编码图
    '''
    point_tree = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(point_array_2)
    label = np.zeros((len(point_array_1),1),dtype= int)
    for i in range(len(point_array_1)):
        dis, _ = point_tree.kneighbors([point_array_1[i]])
        label[i] = dis
    label = np.clip(label, 0, 100)
    print(label)
    p = pv.Plotter(off_screen=True)
    color_map = ['forestgreen', 'lime', 'greenyellow', 'palegreen', 'lightgreen', 'lightskyblue', 'cyan', 'deepskyblue',
                 'dodgerblue', 'purple', 'blueviolet', 'mediumpurple', 'violet', 'pink', 'lightcoral', 'tomato',
                 'orangered',
                 'red', 'maroon']
    sargs = dict(interactive=True,vertical=False,n_labels=10, label_font_size=20, color='black')
    p.add_mesh(point_array_1, scalars=label, point_size=10, show_scalar_bar=True,scalar_bar_args=sargs,
                      render_points_as_spheres=True, cmap=color_map)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def show(point_array,w,h,size,color):

    plotter = pv.Plotter(window_size=[int(w), int(h)])
    plotter.add_mesh(pv.PolyData(point_array), color=color, render_points_as_spheres=True, point_size=int(size))
    plotter.background_color = 'white'
    plotter.view_isometric()
    # plotter.add_title(title,font_size=18, color="black", font=None, shadow=False)
    return plotter
def show2(point_array1,point_array2,w,h,size1,size2,color1,color2):

    plotter = pv.Plotter(window_size=[int(w), int(h)])
    plotter.add_mesh(pv.PolyData(point_array1), color=color1, render_points_as_spheres=True, point_size=int(size1))
    plotter.add_mesh(pv.PolyData(point_array2), color=color2, render_points_as_spheres=True, point_size=int(size2))
    plotter.background_color = 'white'
    plotter.view_isometric()
    # plotter.add_title(title,font_size=18, color="black", font=None, shadow=False)
    return plotter

def show_point_line(points1,points2,line_begin,line_end,w,h,size_pt,size_lpt,line_width,color_pt,color_lpt):
    plotter = pv.Plotter(window_size=[int(w), int(h)])#创建画板
    plotter.add_mesh(pv.PolyData(points1), color=color_pt, render_points_as_spheres=True, point_size=int(size_pt))#角铁点云
    plotter.add_mesh(pv.PolyData(points2), color=color_pt, render_points_as_spheres=True, point_size=int(size_pt))#法兰点云
    plotter.add_mesh(pv.PolyData(line_begin), color=color_lpt, render_points_as_spheres=True,
                     point_size=int(size_lpt))  # 角铁角点
    plotter.add_mesh(pv.PolyData(line_end), color=color_lpt, render_points_as_spheres=True,
                     point_size=int(size_lpt))  # 法兰控制点
    for i in range(len(line_begin)):
        A=[np.random.random(), np.random.random(), np.random.random()]
        for j in range(len(line_end)):
            plotter.add_mesh(pv.Line(line_begin[i],line_end[j]),color=A,line_width=line_width)
    plotter.background_color = 'white'
    plotter.view_isometric()
    return plotter

def showall(point_array,w,h):
    plotter = pv.Plotter(window_size=[int(w), int(h)])
    for i in range(len(point_array)):
        plotter.add_mesh(pv.PolyData(np.array(point_array[i])),color=[np.random.random(),np.random.random(),np.random.random()],render_points_as_spheres=True,point_size=1)
    plotter.background_color = 'white'
    plotter.view_isometric()
    return plotter

def showall1(point_array_set,point_array,w,h,size_set=1,size_array=1,color='red'):
    p = pv.Plotter(window_size=[int(w), int(h)])
    for i in range(len(point_array_set)):
        p.add_mesh(pv.PolyData(np.array(point_array_set[i])),
                   color=[np.random.random(), np.random.random(), np.random.random()], render_points_as_spheres=True,
                   point_size=size_set)
    p.add_mesh(pv.PolyData(point_array),color=color,point_size=size_array)
    p.set_background('w')
    p.view_isometric()
    return p
def drawall(save_path,point_array,size):
    p = pv.Plotter(off_screen=True)
    for i in range(len(point_array)):
        p.add_mesh(pv.PolyData(np.array(point_array[i])),color=[np.random.random(),np.random.random(),np.random.random()],render_points_as_spheres=True,point_size=size)
        p.set_background('w')
    p.screenshot(save_path)
    return save_path
def drawall1(save_path,point_array_set,point_array,size_set=5,size_array=1,color='red'):
    p = pv.Plotter(off_screen=True)
    for i in range(len(point_array_set)):
        p.add_mesh(pv.PolyData(np.array(point_array_set[i])),
                   color=[np.random.random(), np.random.random(), np.random.random()], render_points_as_spheres=True,
                   point_size=size_set)
    p.add_mesh(pv.PolyData(point_array),color=color,point_size=size_array)
    p.set_background('w')
    p.screenshot(save_path)


def draw_point_line(save_path,points1,points2,line_begin,line_end,size_pt,size_lpt,line_width,color_pt,color_lpt):
    p = pv.Plotter(off_screen=True)#创建画板
    p.add_mesh(pv.PolyData(points1), color=color_pt, render_points_as_spheres=True, point_size=int(size_pt))#角铁点云
    p.add_mesh(pv.PolyData(points2), color=color_pt, render_points_as_spheres=True, point_size=int(size_pt))#法兰点云
    p.add_mesh(pv.PolyData(line_begin), color=color_lpt, render_points_as_spheres=True,
                     point_size=int(size_lpt))  # 角铁角点
    p.add_mesh(pv.PolyData(line_end), color=color_lpt, render_points_as_spheres=True,
                     point_size=int(size_lpt))  # 法兰控制点
    for i in range(len(line_begin)):
        A=[np.random.random(), np.random.random(), np.random.random()]
        for j in range(len(line_end)):
            p.add_mesh(pv.Line(line_begin[i],line_end[j]),color=A,line_width=line_width)
    p.set_background('w')
    p.screenshot(save_path)

def drawall2(point_array):
    p = pv.Plotter()
    for i in range(len(point_array)):
        p.add_mesh(pv.PolyData(np.array(point_array[i])),color=[np.random.random(),np.random.random(),np.random.random()],render_points_as_spheres=True,point_size=5)
        p.set_background('w')
    p.show()


def show_clum(data,step,ratio,cut_line,IS=50):
    # 计算统计量
    mean_val = np.mean(data)
    median_val = np.median(data)
    max_val = np.max(data)
    min_val = np.min(data)

    # # 用户输入：竖线位置和标注文字
    # st.sidebar.header("竖线设置")
    # vline_pos = st.sidebar.slider(
    #     "竖线位置",
    #     min_value=float(min_val),
    #     max_value=float(max_val),
    #     value=float(mean_val),
    #     step=0.5
    # )
    # annotation_text = st.sidebar.text_input("标注文字", f"偏差比例{ratio}")
    # annotation_position = st.sidebar.selectbox(
    #     "标注位置",
    #     ["top", "bottom", "top left", "top right", "bottom left", "bottom right"],
    #     index=0
    # )

    # 计算最大值并向上取整
    max_ceil = np.ceil(max_val)

    # 创建区间边界（1.5为步长）
    bins = np.arange(0, max_ceil + step, step)

    # 计算频数
    freq, _ = np.histogram(data, bins=bins)

    # 计算每个子区间的中值
    bin_midpoints = [(bins[i] + bins[i+1]) / 2 for i in range(len(bins)-1)]

    # 创建Plotly图形
    fig = go.Figure()

    # 添加柱状图
    fig.add_trace(go.Bar(
        x=bin_midpoints,
        y=freq,
        name='频数分布',
        marker_color='skyblue',
        width=1.0,  # 控制柱子宽度
        hovertemplate="区间: [%{customdata[0]:.1f}-%{customdata[1]:.1f})<br>" +
                      "中值: %{x:.1f}<br>" +
                      "频数: %{y}<extra></extra>",
        customdata=np.array([[bins[i], bins[i+1]] for i in range(len(bins)-1)])
    ))

    # 添加竖线
    fig.add_vline(
        x=cut_line,
        line_width=3,
        line_dash="dash",
        line_color="red",
        annotation_text=f"偏差比例{ratio}",
        annotation_position='top',
        annotation_font_size=14,
        annotation_font_color="red"
    )

    # 设置每50个区间显示一个标签
    visible_ticks = [i for i in range(len(bin_midpoints)) if i % IS == 0]
    fig.update_layout(
        xaxis=dict(
            title='偏差大小(mm)',
            tickvals=[bin_midpoints[i] for i in visible_ticks],
            ticktext=[f"{bin_midpoints[i]:.1f}" for i in visible_ticks],
            tickangle=-45
        ),
        yaxis=dict(
            title='频数'
        ),
        title='偏差频数直方图',
        hovermode="x",
        showlegend=False
    )

    # 添加统计信息标注
    fig.add_annotation(
        x=0.98,
        y=0.98,
        xref="paper",
        yref="paper",
        text=f"检测点数: {len(data)}<br>剔除{ratio}最大值{cut_line:.2f}<br>最大值: {max_val:.2f}<br>平均值: {mean_val:.2f}<br>中位数: {median_val:.2f}",
        showarrow=False,
        align="right",
        bgcolor="white",
        bordercolor="black",
        borderwidth=1,
        borderpad=4
    )
    return fig
def show_error(pcd,error,w,h,size,ratio):
    data=np.zeros([len(pcd),4])
    data[:,:3]=pcd[:,:3]
    for i in range(len(data)):
        data[i,-1]=error[i]
    data_sorted=sorted(data,key=lambda x:x[-1],reverse=True)
    data_sorted=np.vstack(data_sorted)
    zero_num=int(len(data)*ratio)
    data_sorted[0:zero_num,-1]=0
    p = pv.Plotter(window_size=[int(w),int(h)])
    boring_cmap = plt.cm.get_cmap("seismic", 5)
    sargs = dict(interactive=True, vertical=False, n_labels=5, label_font_size=20, color='black')
    p.add_mesh(data_sorted[:,:3], scalars=data_sorted[:,-1], point_size=int(size), show_scalar_bar=True, scalar_bar_args=sargs,
               render_points_as_spheres=True, cmap=boring_cmap)
    p.set_background('w')
    p.view_isometric()
    return p

def draw_error2(save_path,pcd,error,size,ratio):
    data=np.zeros([len(pcd),4])
    data[:,:3]=pcd[:,:3]
    for i in range(len(data)):
        data[i,-1]=error[i]
    data_sorted=sorted(data,key=lambda x:x[-1],reverse=True)
    data_sorted=np.vstack(data_sorted)
    zero_num=int(len(data)*ratio)
    data_sorted[0:zero_num,-1]=0

    p = pv.Plotter(off_screen=True)
    boring_cmap = plt.cm.get_cmap("seismic", 5)
    sargs = dict(interactive=True, vertical=False, n_labels=10, label_font_size=20, color='black')
    p.add_mesh(data_sorted[:,:3], scalars=data_sorted[:,-1], point_size=int(size), show_scalar_bar=True, scalar_bar_args=sargs,
               render_points_as_spheres=True, cmap=boring_cmap)
    p.set_background('w')
    p.screenshot(save_path)


def draw_error(save_path, pcd, error, size, ratio):
    # 确保输入是numpy数组
    pcd = np.asarray(pcd)
    error = np.asarray(error)

    # 创建包含点和误差值的数据结构
    data = np.zeros((len(pcd), 4))
    data[:, :3] = pcd[:, :3]
    data[:, 3] = error

    # 按误差值排序
    data_sorted = data[data[:, 3].argsort()[::-1]]

    # 将前ratio比例的误差值设为0
    zero_num = int(len(data_sorted) * ratio)
    data_sorted[:zero_num, 3] = 0

    # 创建PyVista点云对象
    point_cloud = pv.PolyData(data_sorted[:, :3])
    point_cloud['error'] = data_sorted[:, 3]  # 添加标量数据

    # 创建绘图器
    p = pv.Plotter(off_screen=True)

    # 获取颜色映射
    try:
        # 新版本matplotlib的用法
        boring_cmap = plt.colormaps["seismic"].resampled(256)
    except AttributeError:
        # 旧版本matplotlib的用法
        boring_cmap = plt.cm.get_cmap("seismic", 256)

    # 标量条参数
    sargs = {
        'title': 'Error',
        'interactive': False,
        'vertical': False,
        'n_labels': 5,
        'label_font_size': 12,
        'color': 'black'
    }

    # 添加点云到绘图器
    p.add_mesh(
        point_cloud,
        scalars='error',  # 使用添加的标量数据
        point_size=int(size),
        show_scalar_bar=True,
        scalar_bar_args=sargs,
        render_points_as_spheres=True,
        cmap=boring_cmap
    )

    # 设置背景并保存截图
    p.set_background('white')
    p.screenshot(save_path)

    # 确保资源释放
    p.close()

def draw_and_save(point_array, pcd_name, save_dir, pcd_type):
    p = pv.Plotter(off_screen=True)  # 建一个画板, 不跳出弹窗
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array), color='red', render_points_as_spheres=True, point_size=1)
    p.set_background('w')
    if pcd_type == 'scan':
        path = save_dir + "\\scan_figure\\" + pcd_name + ".png"
    if pcd_type == 'bim':
        path = save_dir + "\\bim_figure\\" + pcd_name + ".png"
    if pcd_type == 'before':
        path = save_dir + "\\before_figure\\" + pcd_name + ".png"
    if pcd_type == 'after':
        path = save_dir + "\\after_figure\\" + pcd_name + ".png"
    if pcd_type == 'process':
        path = save_dir + "\\process_figure\\" + pcd_name + ".png"
    # print(path)
    p.screenshot(path)
    return path

def Show_arch_dimensional_error(point_array_1, point_array_2):
    '''
    :param point_array_1: 源点云数据
    :param point_array_2: 目标点云数据
    :return: 误差彩色编码图
    '''
    point_tree = NearestNeighbors(n_neighbors=1, algorithm='ball_tree').fit(point_array_2)
    label = np.zeros((len(point_array_1), 1), dtype=int)
    for i in range(len(point_array_1)):
        dis, _ = point_tree.kneighbors([point_array_1[i]])
        if dis <= 500:#设置了最大距离阈值，避免噪点影响
            label[i] = dis
        else:
            label[i]=0
    label = np.clip(label, 0, 100)
    print(label)
    p = pv.Plotter(off_screen=True)
    # color_map = ['forestgreen', 'lime', 'greenyellow', 'palegreen', 'lightgreen', 'lightskyblue', 'cyan', 'deepskyblue',
    #              'dodgerblue', 'purple', 'blueviolet', 'mediumpurple', 'violet', 'pink', 'lightcoral', 'tomato',
    #              'orangered', 'red', 'maroon']
    sargs = dict(interactive=True, vertical=False, n_labels=5, label_font_size=20, color='black')
    p.add_mesh(point_array_1, scalars=label, point_size=1, show_scalar_bar=True, scalar_bar_args=sargs,
                      render_points_as_spheres=True)
    p.set_background('w')
    p.screenshot("jietu.png")
    return "jietu.png"

def draw2_and_save(point_array1, point_array2, pcd_name, save_dir, pcd_type):
    p = pv.Plotter(off_screen=True)  # 建一个画板, 不跳出弹窗
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array1), color='red', render_points_as_spheres=True, point_size=1)
    p.add_mesh(pv.PolyData(point_array2), color='blue', render_points_as_spheres=True, point_size=1)
    p.set_background('w')
    if pcd_type == 'scan':
        path = save_dir + "\\scan_figure\\" + pcd_name + ".png"
    if pcd_type == 'bim':
        path = save_dir + "\\bim_figure\\" + pcd_name + ".png"
    if pcd_type == 'before':
        path = save_dir + "\\before_figure\\" + pcd_name + ".png"
    if pcd_type == 'after':
        path = save_dir + "\\after_figure\\" + pcd_name + ".png"
    if pcd_type == 'process':
        path = save_dir + "\\process_figure\\" + pcd_name + ".png"
    # print(path)
    p.screenshot(path)
    return path

# 展示提升变形误差，并保存截图
def draw_error_and_save(point_array, label, save_dir):
    p = pv.Plotter(off_screen=True)  # 建一个画板, 不跳出弹窗
    p.add_mesh(point_array, scalars=label, point_size=5., show_scalar_bar=True,
                     render_points_as_spheres=True,
                     clim=[-100, 0], colormap='gist_rainbow', interpolate_before_map=False)
    p.add_scalar_bar("Deformation (mm)", interactive=True, vertical=True, outline=False, fmt='%10.1f',
                           color='black', font_family='times', width=0.7, title_font_size=32, n_labels=11,
                           label_font_size=28)
    p.background_color = [255, 255, 255]
    path = save_dir + "\\process_figure\\deformation_error.png"
    p.screenshot(path)
    return path

def draw_and_save1(point_array, save_dir, k=1, color='red'):
    p = pv.Plotter(off_screen=True)  # 建一个画板, 不跳出弹窗
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array), color=color, render_points_as_spheres=True, point_size=k)
    p.set_background('w')
    p.screenshot(save_dir)

def draw3_and_save(point_array1, point_array2, point_array3, save_dir, color=['red', 'blue', 'yellow'], k = [1, 1, 1]):
    p = pv.Plotter(off_screen=True)  # 建一个画板, 不跳出弹窗
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array1), color=color[0], render_points_as_spheres=True, point_size=k[0])
    p.add_mesh(pv.PolyData(point_array2), color=color[1], render_points_as_spheres=True, point_size=k[1])
    p.add_mesh(pv.PolyData(point_array3), color=color[2], render_points_as_spheres=True, point_size=k[2])
    p.set_background('w')
    # print(path)
    p.screenshot(save_dir)

def draw2_and_save2(point_array1, point_array2, save_dir, color=['red', 'blue'], k = [1, 1]):
    p = pv.Plotter(off_screen=True)  # 建一个画板, 不跳出弹窗
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array1), color=color[0], render_points_as_spheres=True, point_size=k[0])
    p.add_mesh(pv.PolyData(point_array2), color=color[1], render_points_as_spheres=True, point_size=k[1])
    p.set_background('w')
    # print(path)
    p.screenshot(save_dir)

def draw4_and_save(point_array1, point_array2, point_array3, point_array4,
                   save_dir, color=['red', 'blue', 'yellow', 'green'], k=[1, 1, 1, 1]):
    p = pv.Plotter(off_screen=True)  # 建一个画板, 不跳出弹窗
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array1), color=color[0], render_points_as_spheres=True, point_size=k[0])
    p.add_mesh(pv.PolyData(point_array2), color=color[1], render_points_as_spheres=True, point_size=k[1])
    p.add_mesh(pv.PolyData(point_array3), color=color[2], render_points_as_spheres=True, point_size=k[2])
    p.add_mesh(pv.PolyData(point_array4), color=color[3], render_points_as_spheres=True, point_size=k[3])
    p.set_background('w')
    # print(path)
    p.screenshot(save_dir)
