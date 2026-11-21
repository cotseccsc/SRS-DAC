
# Copyright 2026 Jikang Zhang, Zhengyan Wu

import numpy as np
import tifffile
import matplotlib
matplotlib.use('Agg')  # 无界面后端，避免在子线程中创建 GUI 窗口
import matplotlib.pyplot as plt
from scipy import ndimage as ndi
from skimage import filters, morphology, measure
import os
import sys

# ==================== 细胞分割模块 ====================
def fill_holes_2d(mask_3d):
    """对每个z切片独立进行2D孔洞填充"""
    filled = np.zeros_like(mask_3d)
    for z in range(mask_3d.shape[0]):
        filled[z] = ndi.binary_fill_holes(mask_3d[z])
    return filled

def get_cell_mask_3d(img, median_size=3, ball_radius_close=5, ball_radius_open=2,
                     extra_fill_iterations=2):
    """从3D图像中分割出最大的连通物体（卵母细胞）"""
    print("Step 1: Median filtering...")
    img_denoised = ndi.median_filter(img, size=median_size)

    print("Step 2: Otsu thresholding...")
    thresh = filters.threshold_otsu(img_denoised)
    binary = img_denoised > thresh
    print(f"    Threshold: {thresh:.2f}")

    print("Step 3: Morphological operations...")
    se_close = morphology.ball(ball_radius_close)
    se_open = morphology.ball(ball_radius_open)
    closed = morphology.binary_closing(binary, se_close)
    cleaned = morphology.binary_opening(closed, se_open)

    print("Step 4: Extracting largest component...")
    labels = measure.label(cleaned, connectivity=2)
    regions = measure.regionprops(labels)
    if not regions:
        raise ValueError("No components found!")
    largest = max(regions, key=lambda r: r.area)
    mask = (labels == largest.label)

    print("Step 5: Basic hole filling (2D per slice)...")
    mask = fill_holes_2d(mask)

    for i in range(extra_fill_iterations):
        print(f"Step 6.{i+1}: Extra hole filling iteration...")
        mask = morphology.binary_closing(mask, morphology.ball(2))
        mask = fill_holes_2d(mask)

    mask = morphology.binary_closing(mask, morphology.ball(1))
    return mask

# ==================== 脂滴分割模块 ====================
def segment_lipid_global_threshold(img, threshold=None, median_filter_size=3,
                                   min_size=3, close_radius=1):
    """使用全局阈值法提取脂滴掩膜"""
    if median_filter_size > 0:
        print(f"  中值滤波 (size={median_filter_size})...")
        img_denoised = ndi.median_filter(img, size=median_filter_size)
    else:
        img_denoised = img

    if threshold is None:
        print("  使用Otsu自动计算全局阈值...")
        threshold = filters.threshold_otsu(img_denoised)
        print(f"  Otsu阈值 = {threshold:.2f}")
    else:
        print(f"  使用手动阈值 = {threshold}")
    binary = img_denoised > threshold

    if close_radius > 0:
        print(f"  3D闭运算 (半径={close_radius})...")
        se = morphology.ball(close_radius)
        binary = morphology.binary_closing(binary, se)

    print(f"  移除小于 {min_size} 体素的区域...")
    labels = measure.label(binary, connectivity=2)
    regions = measure.regionprops(labels)
    mask = np.zeros_like(binary, dtype=bool)
    for region in regions:
        if region.area >= min_size:
            mask[labels == region.label] = True
    return mask


def process_image(image, cell_mask, lipid_mask, result_dir, analysis_dir):
    """
    完整处理流程：
    - 计算每层细胞质平均强度、缩放因子
    - 保存归一化后的细胞全图和细胞质图到 result_dir
    - 保存平均强度曲线图、详细分析txt到 analysis_dir
    """
    # 维度处理
    if image.ndim == 2:
        image = image[np.newaxis, ...]
    if cell_mask.ndim == 2:
        cell_mask = cell_mask[np.newaxis, ...]
    if lipid_mask.ndim == 2:
        lipid_mask = lipid_mask[np.newaxis, ...]
    cell_mask = cell_mask.astype(bool)
    lipid_mask = lipid_mask.astype(bool)

    image_float = image.astype(np.float32)
    cell_image = image_float * cell_mask

    # 计算每层细胞质平均强度
    z_slices = image.shape[0]
    slice_means = []
    for z in range(z_slices):
        cytoplasm_region = cell_mask[z] & (~lipid_mask[z])
        pixels = cell_image[z][cytoplasm_region]
        if len(pixels) > 0:
            slice_means.append(np.mean(pixels))
        else:
            slice_means.append(np.nan)
    slice_means = np.array(slice_means)

    max_mean_idx = np.nanargmax(slice_means)
    max_mean_value = slice_means[max_mean_idx]
    print(f"Slice index with maximum cytoplasmic mean intensity: {max_mean_idx}")
    print(f"Maximum mean intensity value: {max_mean_value:.4f}")

    # 绘制并保存平均强度曲线
    plt.figure(figsize=(10, 4))
    plt.plot(slice_means, marker='o', linestyle='-')
    plt.xlabel('Slice index')
    plt.ylabel('Mean intensity of non-lipid region')
    plt.title('Mean cytoplasmic intensity per slice')
    plt.grid(True)
    curve_path = os.path.join(analysis_dir, 'slice_means.png')
    plt.savefig(curve_path)
    plt.close()
    print(f"Slice means plot saved to {curve_path}")

    # 逐切片归一化，同时记录每层缩放系数
    max_mean = np.nanmax(slice_means)
    scales = np.full(z_slices, np.nan)
    if max_mean > 0:
        cell_image_normalized = np.zeros_like(cell_image)
        for z in range(z_slices):
            if not np.isnan(slice_means[z]) and slice_means[z] > 0:
                scale = max_mean / slice_means[z]
                scales[z] = scale
                cell_image_normalized[z] = cell_image[z] * scale
            else:
                cell_image_normalized[z] = cell_image[z]
                scales[z] = 1.0
        print(f"Per-slice normalization applied. Target max mean intensity: {max_mean:.4f}")
    else:
        print("Maximum mean is zero or negative, normalization skipped.")
        cell_image_normalized = cell_image
        scales[:] = 1.0

    # 保存归一化结果到 Result 文件夹
    cell_norm_path = os.path.join(result_dir, 'cell_normalized.tiff')
    tifffile.imwrite(cell_norm_path, cell_image_normalized.astype(np.float32))
    cytoplasm_image = cell_image_normalized * (~lipid_mask)
    cyto_norm_path = os.path.join(result_dir, 'cytoplasm_normalized.tiff')
    tifffile.imwrite(cyto_norm_path, cytoplasm_image.astype(np.float32))
    print(f"Normalized images saved to {result_dir}")

    # 保存详细分析数据到 Analysis 文件夹
    info_path = os.path.join(analysis_dir, 'normalization_info.txt')
    with open(info_path, 'w') as f:
        f.write(f"# Maximum intensity slice index: {max_mean_idx}\n")
        f.write(f"# Maximum mean intensity value: {max_mean_value:.6f}\n")
        f.write("# Format: slice_index, mean_intensity, scale_factor\n")
        for z in range(z_slices):
            mean_val = slice_means[z] if not np.isnan(slice_means[z]) else -1
            scale_val = scales[z] if not np.isnan(scales[z]) else 1.0
            f.write(f"{z}, {mean_val:.6f}, {scale_val:.6f}\n")
    print(f"Normalization info saved to {info_path}")

    return cell_image_normalized, slice_means, scales

# ==================== 主程序 ====================
def main():
    # 获取输入文件路径
    if len(sys.argv) == 4:
        path_2850 = sys.argv[1]
        path_2930 = sys.argv[2]
        path_2980 = sys.argv[3]
    else:
        path_2850 = "tif_2850_4w_RAW_1.tif"
        path_2930 = "tif_2930_4w_RAW_1.tif"
        path_2980 = "tif_2980_4w_RAW_1.tif"
        print("Using default filenames.")
        print("Usage: python script.py 2850.tif 2930.tif 2980.tif")

    for p in [path_2850, path_2930, path_2980]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"File not found: {p}")

    print("Loading images...")
    img_2850 = tifffile.imread(path_2850)
    img_2930 = tifffile.imread(path_2930)
    img_2980 = tifffile.imread(path_2980)

    # 统一为3D (z, y, x)
    def to_3d(arr):
        if arr.ndim == 2:
            return arr[np.newaxis, ...]
        elif arr.ndim == 4:
            return arr[..., 0]
        return arr

    img_2850 = to_3d(img_2850)
    img_2930 = to_3d(img_2930)
    img_2980 = to_3d(img_2980)

    if not (img_2850.shape == img_2930.shape == img_2980.shape):
        raise ValueError("Input images must have the same dimensions")

    # 计算差值（保留负值）
    print("Computing difference images...")
    diff_cell = img_2930.astype(np.float32) - img_2980.astype(np.float32)
    diff_lipid = img_2850.astype(np.float32) - img_2980.astype(np.float32)

    # 创建根目录（基于2850文件名）
    base_name = os.path.splitext(os.path.basename(path_2850))[0]
    root_dir = base_name
    os.makedirs(root_dir, exist_ok=True)

    # 创建子目录
    cell_dir = os.path.join(root_dir, "CellExtraction")
    lipid_dir = os.path.join(root_dir, "LDExtraction")
    result_dir = os.path.join(root_dir, "Result")
    analysis_dir = os.path.join(root_dir, "Analysis")
    for d in [cell_dir, lipid_dir, result_dir, analysis_dir]:
        os.makedirs(d, exist_ok=True)

    # 保存差值图像
    tifffile.imwrite(os.path.join(cell_dir, "diff_2930_minus_2980.tif"), diff_cell.astype(np.float32))
    tifffile.imwrite(os.path.join(lipid_dir, "diff_2850_minus_2980.tif"), diff_lipid.astype(np.float32))

    # 细胞分割
    print("\n--- Cell segmentation ---")
    cell_mask = get_cell_mask_3d(diff_cell,
                                 median_size=3,
                                 ball_radius_close=5,
                                 ball_radius_open=2,
                                 extra_fill_iterations=2)
    # 保存细胞掩膜和分割结果
    tifffile.imwrite(os.path.join(cell_dir, "cell_mask.tif"), cell_mask.astype(np.uint8))
    cell_segmented = diff_cell * cell_mask
    tifffile.imwrite(os.path.join(cell_dir, "cell_segmented.tif"), cell_segmented.astype(np.float32))

    # 脂滴分割
    print("\n--- Lipid droplet segmentation ---")
    lipid_mask = segment_lipid_global_threshold(diff_lipid,
                                                 threshold=None,
                                                 median_filter_size=0,
                                                 min_size=0,
                                                 close_radius=1)
    tifffile.imwrite(os.path.join(lipid_dir, "lipid_mask.tif"), lipid_mask.astype(np.uint8))
    lipid_segmented = diff_lipid * lipid_mask
    tifffile.imwrite(os.path.join(lipid_dir, "lipid_segmented.tif"), lipid_segmented.astype(np.float32))

    # 归一化处理（使用原始图像 img_2850）
    print("\n--- Normalization and output ---")
    process_image(img_2850, cell_mask, lipid_mask, result_dir, analysis_dir)

    print(f"\nAll done! Results saved in folder: {root_dir}")

if __name__ == "__main__":
    main()