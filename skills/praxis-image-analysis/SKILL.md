---
name: praxis-image-analysis
description: 图像分析与测量：二值掩码连通区域、像素面积、ROI与空间标定、阈值分割验证、图像识别的数据划分。用于“图像里有几个区域/颗粒、连通域怎么量、显微图怎么分析、阈值如何定、图像数据集怎么防泄漏”。Image analysis, image measurement, connected components, microscopy, segmentation validation and source-family split. 区分给定掩码几何测量与需要独立验证的真实图像推断。
license: MIT
---

# Praxis · 图像分析与测量

BUNDLE=`praxis` 技能目录；脚本 `BUNDLE/scripts/`；Python 3.12、uv（`uv run --locked`）；无终端仅设计。执行见 [automation.md](../../references/automation.md)。

## 做什么

- 按 [image-analysis.md](../../references/image-analysis.md) 区分给定掩码几何、真实图像测量与监督识别，裁剪到实际任务。
- `binary_components` 仅测二维二值掩码：声明4／8连通、触边、最小像素数与返回上限，分别报原始、过滤和返回统计。
- `pixel_size=[xsize, ysize]` 与 unit 是调用方声明标定，标未核状态；比例溢出／下溢为零保留拒绝，缺标定只报像素。
- 真实图像保原图、采集条件、预处理及 ROI／阈值，同设置用可追溯标尺和独立参考核分割与测量误差。
- 涉训练／监督识别时先按标本、个体、会话或批次 source family 划分再调参／增强，来源切片留同一侧。
- 用已知小掩码核计数、面积和过滤；按模态选实际可用成熟库，分割、语义对象计数与几何结果分别表述。

## 交接

监督预测交 [machine-learning](../praxis-machine-learning/SKILL.md)，独立主张交 [verify](../praxis-verify/SKILL.md)，实际运行交 [compute](../praxis-compute/SKILL.md)，图形与论文交 [visualization](../praxis-visualization/SKILL.md)／[report](../praxis-report/SKILL.md)。
