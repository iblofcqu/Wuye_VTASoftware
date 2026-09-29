# 报告图片生成：与 base_software/functions/draw_functions.py 的报告用函数保持一致（仅移除 streamlit/stpyvista 耦合）。
import numpy as np
import pyvista as pv
import matplotlib.pyplot as plt
import plotly.graph_objects as go


def draw1(save_path, point_array,size=1,color='red'):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array), color=color, render_points_as_spheres=True, point_size=size)
    p.set_background('w')
    p.screenshot(save_path)


def draw2(save_path,point_array1,point_array2,size1=1,size2=1,color1='red',color2='blue'):
    # 通过添加mesh的方法绘图
    p = pv.Plotter(off_screen=True)  ## 建一个画板
    # 然后在画板上画图
    p.add_mesh(pv.PolyData(point_array1[:,:3]), color=color1, render_points_as_spheres=True, point_size=size1)
    p.add_mesh(pv.PolyData(point_array2[:,:3]), color=color2, render_points_as_spheres=True, point_size=size2)
    p.set_background('w')
    p.screenshot(save_path)


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
