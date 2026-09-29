# 报告链路依赖与配置（Linux）

报告生成链路：pyvista 离屏截图 → Plotly + kaleido(Chromium) 出图 → pylatex 组装 → **latexmk + xelatex** 编译 PDF。

## 1. 安装（用户级，无需 root）

```bash
curl -sL https://yihui.org/tinytex/install-bin-unix.sh | sh   # 装到 ~/.TinyTeX，bin 链接到 ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"
tlmgr install ctex fandol ragged2e xecjk fontspec colortbl \
              lastpage fancyhdr textpos xcolor float caption \
              multirow booktabs geometry parskip enumitem \
              microtype hyperref amsmath amsfonts tools
```

依赖链会自动补装 zhnumber、zhmetrics、cjk、xetex 等宏包。

## 2. 平台适配说明（相对 base_software 的显式偏差）

1. **编译引擎 xelatex**：ctex 默认字体集 fandol 在 pdfTeX 下不可用，pdftex 可用的免费字体集不存在；
   故 `app/report/pdf.py` 使用 `compiler='latexmk', compiler_args=['-xelatex']`（保留多轮编译以解析页码引用）。
2. **图片单位 360pt**：基线用 `width='360px'`（5 处），`px` 非法，LaTeX 报错后按 pt 恢复；显式写成 `360pt` 与恢复结果完全一致。
3. **圈号字形**：`\xeCJKDeclareCharClass{CJK}{"2460 -> "24FF}` 将 ①-⑥ 等圈号映射到中文字体，避免缺字。

## 3. 其他运行依赖

- Chromium/Chrome：kaleido 导出直方图图片（`Error_Analysis.jpg`）；
- 离屏渲染：pyvista 截图需要可用显示（DISPLAY/EGL/OSMesa，或 xvfb-run）；
- 中文字体：随 ctex/fandol 宏包提供。

## 4. 验证

```bash
cd backend
PATH="$HOME/.local/bin:$PATH" uv run pytest tests/test_report_toolchain.py -q
```

期望：真机生成 PDF（含图表与中文），文件 > 20KB，`clean_tex=True` 清理 .tex。
