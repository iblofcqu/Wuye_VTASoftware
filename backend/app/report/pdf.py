#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os.path
import time
import numpy as np
from pylatex import *
# HFill, TextColor,Tabularx,MiniPage, Foot, simple_page_number, Head,PageStyle, Document, Section, Subsection, LargeText,TextBlock,HugeText,NewLine,Figure,LongTable, MultiColumn,NewPage
from pylatex.utils import italic, NoEscape,bold
from pylatex.package import Package

def QA_Report(cache_path,output_path,basic_information):
    geometry_options = {"tmargin": "3cm", "lmargin": "3cm", "rmargin": "3cm"}  # tmargin上边距，lmargin左边距
    doc = Document(geometry_options=geometry_options)
    doc.packages.add(Package('ctex'))
    doc.packages.add(Package('indentfirst'))
    doc.packages.add(Package('float'))
    # 平台适配：①-⑥ 等圈号映射到中文字体（xeCJK），避免 Latin Modern 缺字形
    doc.preamble.append(NoEscape(r'\xeCJKDeclareCharClass{CJK}{"2460 -> "24FF}'))
    # 封面
    t = time.localtime()
    doc.change_length("\TPHorizModule", "1mm")
    doc.change_length("\TPVertModule", "1mm")
    doc.change_length("\parindent","2em")

    with doc.create(MiniPage(width=r"\textwidth")) as page:
        with page.create(TextBlock(100, 40, 60)):  # 报告名称
            page.append(HugeText(italic("{}".format(basic_information['PCD_name']))))
        with page.create(TextBlock(100, 40, 80)):  # 报告名称
            page.append(HugeText(bold("\n几何质量评估报告")))

        with page.create(TextBlock(80, 100, 180)):  # 报告出具方和时间
            page.append(LargeText("三维扫描分析系统"))
            page.append(LargeText("\nDeviScan 3D V1.0"))
            page.append(LargeText("\n\n{}年{}月{}日".format(t[0], t[1], t[2])))

    # 另起一页
    doc.append(NewPage())

    # 创建页眉页脚
    header = PageStyle("header")
    # 页眉页脚版式1
    with header.create(Head("C")) as topheader:
        with topheader.create(Tabularx("X X X X X X X", width_argument=NoEscape(r"\textwidth"))) as topheader_table:
            topheader_table.add_row(
                [MultiColumn(1, align='l', data=TextColor("gray", "三维扫描分析系统")), "", "",
                 MultiColumn(1, align='c', data=TextColor("gray", "几何质量评估报告")), "", "",
                 MultiColumn(1, align='r', data=TextColor("gray", "DeviScan 3D-V1.0"))])
            topheader_table.add_hline(color="gray")
    with header.create(Foot("C")) as supheader:
        with supheader.create(Tabularx("X X X X X X X", width_argument=NoEscape(r"\textwidth"))) as supheader_table:
            supheader_table.add_hline(color="gray")
            supheader_table.add_row(
                [MultiColumn(1, align='l', data=TextColor("gray", "Updata on 2025/07/23")),
                 "", "", "", "", "",
                 MultiColumn(1, align='r', data=TextColor("gray", simple_page_number()))])
    # 添加页眉页脚
    doc.preamble.append(header)
    doc.change_document_style("header")

    # 1.基本信息(用户输入参数和基本点云信息)
    with doc.create(Section('基本信息')):
        doc.append(TextColor('red', bold("以下要求在检测前均已确认:")))
        with doc.create(Itemize()) as itemize:
            itemize.add_item("已通过BIM获取离散点云;")
            itemize.add_item("进行了必要的下采样;")
            itemize.add_item("已对扫描点云和离散点云单位一致性进行检查;")
            itemize.add_item("已完成扫描点云和离散点云的匹配;")
            itemize.add_item("扫描点云路径：")
            itemize.add_item("{}".format(basic_information['SCENE_path']))
            itemize.add_item("离散点云路径：")
            itemize.add_item("{}".format(basic_information['BIM_path']))
        doc.append(NoEscape(r"\hspace{0.5cm} 本报告所涉参数及算法信息如表1所示。"))
        with doc.create(LongTable("l l l l")) as data_table:
            data_table.add_row(
                [MultiColumn(4, align='l', data=TextColor("black", '本报告所涉参数及算法信息如表1所示。'))])  # 表名，合并单元格
            data_table.add_row(
                [MultiColumn(4, align='c', data=TextColor("black", '表1 参数及算法信息'))])  # 表名，合并单元格
            data_table.add_hline()
            data_table.add_hline()
            data_table.add_row([" 点云单位", "偏差计算方法", "平面邻域大小", "剔除比例"])
            data_table.add_hline()
            row = ["{}".format(basic_information['unit']), "{}".format(basic_information['method']), "{}{}".format(basic_information['distance'],basic_information['unit']),
                   "{}%".format(basic_information['ratio']*100)]
            data_table.add_row(row)
            data_table.add_hline()
            data_table.add_hline()
        doc.append(NoEscape(r"\hspace{0.5cm} 输入点云如图1所示，"))
        doc.append("扫描点云包含{}个点,离散点云包含{}个点。".format(basic_information['len_pcd_scene'],basic_information['len_pcd_bim']))
        with doc.create(Figure(position='H')) as fig1:
            with doc.create(SubFigure(position='b',width=NoEscape(r'0.5\linewidth'))) as left_fig1:
                left_fig1.add_image(os.path.join(cache_path,"fig1a.jpg"),width=NoEscape(r'\linewidth'))
                left_fig1.add_caption('扫描点云')
            with doc.create(SubFigure(position='b',width=NoEscape(r'0.5\linewidth'))) as right_fig1:
                right_fig1.add_image(os.path.join(cache_path,"fig1b.jpg"),width=NoEscape(r'\linewidth'))
                right_fig1.add_caption('离散点云')
            fig1.add_caption('输入点云')
    # 2.方法流程(技术路线，主要流程)
    with doc.create(Section('方法流程')):
        # 2.1整体技术路线
        with doc.create(Subsection('整体技术路线')):
            doc.append("为检测钢结构表面几何偏差：①采用泊松圆盘采样算法，将BIM中网格文件离散为点云文件，该步骤由本软件'点云预处理>>网格离散'功能完成;②基于FPFH特征和随机采样一致性算法，实现扫描点云和离散点云的全局注册，该步骤由本软件'配准>>粗配准'功能完成，该过程受算法鲁棒性影响，可选择采用手动配准的方式进行；③采用迭代最近邻算法进行位姿调整，该步骤由本软件'配准>>精配准'功能完成；④基于离散点云进行扫描点云中目标构件的提取；⑤基于扫描的目标构件，从离散点云中进行缺失部分的剔除，获得检测点；⑥进行偏差计算，其中可选用方法Point2Point或Point2Plane,前者计算检测点与扫描点云中最近点的距离，后者获取检测点在扫描点云中的最近点后，获取最近点在扫描点云中的邻域点并采用最小二乘法拟合平面，计算检测点至拟合平面的距离作为偏差值。其中当采用Point2Point方法计算几何偏差时，易受扫描点云间距影响从而引入额外偏差,因此尽量不对扫描点云进行下采样;当采用Point2Plane方法计算偏差时，在表面曲率剧烈变化区域，出现奇异值。两类方法均不可避免引入额外偏差，因此在统计偏差信息时，特意剔除了一定比例的最大偏差点。")
        # 2.2数据读取
        with doc.create(Subsection('数据读取')):
            doc.append('读取扫描点云和离散点云如图2所示')
            with doc.create(Figure(position='H')) as fig2:  # 创建一个图片
                fig2.add_image(os.path.join(cache_path, "fig2.jpg"),
                               width='360pt')  # 图片内容
                fig2.add_caption('输入点云（红：扫描点云；蓝：离散点云）')
        # 2.3检测点获取
        with doc.create(Subsection('检测点获取')):
            doc.append("进行环境点云剔除后，扫描点云如图3所示；进一步获取检测点如图4所示")
            with doc.create(Figure(position='H')) as fig3:  # 创建一个图片
                fig3.add_image(os.path.join(cache_path, "fig3.jpg"),
                               width='360pt')  # 图片内容
                fig3.add_caption('剔除环境信息后的扫描点云')
            with doc.create(Figure(position='H')) as fig4:  # 创建一个图片
                fig4.add_image(os.path.join(cache_path, "fig4.jpg"),
                               width='360pt')  # 图片内容
                fig4.add_caption('从离散点云中获取的偏差检测点')

    # 3.尺寸评估结果
    with doc.create(Section('尺寸评估结果')):
        with doc.create(Subsection('偏差云图')):
            doc.append('按一定比例剔除最大偏差点后，在离散点云中显示偏差云图如图5所示。')
            with doc.create(Figure(position='H')) as fig5:  # 创建一个图片
                fig5.add_image(os.path.join(cache_path,"fig5.jpg"),
                               width='360pt')  # 图片内容
                fig5.add_caption('偏差云图')
        with doc.create(Subsection('偏差统计')):
            doc.append('统计检测点偏差在各区间的点数如图6所示，其中保留了所有偏差并标注了剔除线。')
            with doc.create(Figure(position='H')) as fig6:
                fig6.add_image(os.path.join(cache_path,"Error_Analysis.jpg"),width='360pt')
                fig6.add_caption('偏差柱状图')
            with doc.create(LongTable("l l l l")) as data_table:
                data_table.add_row(
                    [MultiColumn(4, align='l',
                                 data=TextColor("black", '记录基本偏差信息如表2所示。'))])  # 表名，合并单元格
                data_table.add_row(
                    [MultiColumn(4, align='c', data=TextColor("black", '表2 偏差信息(单位:mm)'))])  # 表名，合并单元格
                data_table.add_hline()
                data_table.add_hline()
                data_table.add_row(["检测点数", "剔除部分点后的最大偏差", "偏差最大值", "平均偏差"])
                data_table.add_hline()
                row = ["{}".format(basic_information['check_num']), "{}".format(basic_information['error_max_cut']),
                       "{}".format(basic_information['error_max']),
                       "{}".format(basic_information['error_mean'] )]
                data_table.add_row(row)
                data_table.add_hline()
                data_table.add_hline()

    doc.generate_pdf(os.path.join(output_path,"{}".format(basic_information['PCD_name'])+'几何质量评估报告{}{}{}'.format(t[0], t[1], t[2])), clean_tex=True, compiler='latexmk', compiler_args=['-xelatex'])
