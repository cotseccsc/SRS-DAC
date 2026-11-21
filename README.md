**简体中文** | [English](README-EN.md)

# 卵母细胞 SRS 成像深度衰减校正工具

[![Download Windows EXE](https://img.shields.io/badge/📥_Download-Windows_EXE_v1.0.0-4CAF50?style=for-the-badge&logo=windows)](https://github.com/cotseccsc/SRS-DAC/releases/tag/v1.0.0)
无需配置 Python 环境，解压即用。

一个用于**卵母细胞受激拉曼散射（SRS）成像**的深度衰减校正工具。通过 3D 细胞/脂滴分割与逐层强度归一化，补偿 SRS 成像中随深度增加而出现的信号衰减，使不同深度层的图像强度具有可比性。

---

## 安装

### 环境要求

- Python **3.10 及以上**（推荐 3.11 / 3.12；使用 3.13 时请确保 `scikit-image >= 0.26.0`）
- 操作系统：作者目前仅保证其在Windows操作系统下的可用性。

### 步骤

```bash
# 1. 克隆仓库
git clone https://github.com/cotseccsc/SRS-DAC.git
cd SRS-DAC

# 2. 创建并激活虚拟环境
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (CMD)
.venv\Scripts\activate.bat

# 3. 安装依赖
pip install -r requirements.txt
```

### Hint

如果 PowerShell 提示 **"无法加载文件 Activate.ps1，因为在此系统上禁止运行脚本"**，执行一次以下命令即可（仅对当前用户生效，无需管理员权限）：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 使用方式

### 图形界面

```bash
python SRS-DAC.py
```

界面操作：

1. 分别选择 **2850 cm⁻¹**、**2930 cm⁻¹**、**2980 cm⁻¹** 三个 TIFF 文件
2. 选择**输出根目录**
3. 点击 **开始校正**，观察下方日志
4. 处理完成后会弹出提示，结果保存在输出目录下以输入文件名命名的子文件夹中

界面支持中英文切换。

---

## 输入要求

- **三个 TIFF 文件**，分别对应 2850、2930、2980 cm⁻¹ 波数
- 三者必须具有**完全相同的空间尺寸** `(z, y, x)` 和数据类型

---

## 输出结构

```
<输出根目录>/
└── <2850文件名（无扩展名）>/
    ├── CellExtraction/
    │   ├── diff_2930_minus_2980.tif    # 用于细胞分割的差值图
    │   ├── cell_mask.tif               # 细胞二值掩膜 (uint8)
    │   └── cell_segmented.tif          # 差值图 × 细胞掩膜
    ├── LDExtraction/
    │   ├── diff_2850_minus_2980.tif    # 用于脂滴分割的差值图
    │   ├── lipid_mask.tif              # 脂滴二值掩膜 (uint8)
    │   └── lipid_segmented.tif         # 差值图 × 脂滴掩膜
    ├── Result/
    │   ├── cell_normalized.tiff        # 归一化后的细胞全图 (float32)
    │   └── cytoplasm_normalized.tiff   # 归一化后的细胞质图 (float32)
    └── Analysis/
        ├── slice_means.png             # 每层细胞质平均强度曲线
        └── normalization_info.txt      # 逐层均值与缩放系数
```

`normalization_info.txt` 格式：

```
# Maximum intensity slice index: <int>
# Maximum mean intensity value: <float>
# Format: slice_index, mean_intensity, scale_factor
0, <mean_0>, <scale_0>
1, <mean_1>, <scale_1>
...
```

---

## 参数说明

如需针对不同样本调整分割效果，可修改 `process.py` 中的默认参数：

### 细胞分割 `get_cell_mask_3d`

| 参数 | 默认值 | 说明 |
|---|---|---|
| `median_size` | 3 | 3D 中值滤波核大小，去噪用 |
| `ball_radius_close` | 5 | 3D 闭运算球半径，填补细胞内部小孔 |
| `ball_radius_open` | 2 | 3D 开运算球半径，去除外部毛刺 |
| `extra_fill_iterations` | 2 | 额外填洞迭代次数 |

### 脂滴分割 `segment_lipid_global_threshold`

| 参数 | 默认值 | 说明 |
|---|---|---|
| `threshold` | `None` | `None` 表示 Otsu 自动阈值；也可传入手动阈值 |
| `median_filter_size` | 3（调用处传 0） | 中值滤波核，0 表示不滤波 |
| `min_size` | 3（调用处传 0） | 最小连通域体素数，0 表示不过滤 |
| `close_radius` | 1 | 3D 闭运算球半径 |

---

## 专利与许可

本项目采用 **Apache License 2.0** 许可，详见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。

**专利声明**

本项目相关方法已提交专利申请。根据 Apache License 2.0 第 3 条，版权所有者和贡献者向所有遵守本许可的用户授予实施贡献代码中所包含的相关专利的许可。该专利授权以用户遵守本许可为前提条件，并受该许可中规定的防御性终止条款约束。即：若任何用户就本项目向贡献者发起专利诉讼，其依据本许可获得的专利授权将自动终止。

---

## 致谢

本工具基于以下开源项目构建：[NumPy](https://numpy.org/)、[SciPy](https://scipy.org/)、[scikit-image](https://scikit-image.org/)、[tifffile](https://github.com/cgohlke/tifffile)、[Matplotlib](https://matplotlib.org/)。

---
