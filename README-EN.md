[简体中文](README.md) | **English**

# Oocyte SRS Imaging Depth Correction Tool

[![Download Windows EXE](https://img.shields.io/badge/📥_Download-Windows_EXE_v1.0.0-4CAF50?style=for-the-badge&logo=windows)](https://github.com/cotseccsc/SRS-DAC/releases/tag/v1.0.0)

*No Python environment required. Just unzip and run.*

A depth-attenuation correction tool for **oocyte Stimulated Raman Scattering (SRS) imaging**. It performs 3D cell / lipid-droplet segmentation and per-slice intensity normalization to compensate for depth-dependent signal loss, making images from different depths quantitatively comparable.

---

## Installation

### Requirements

- Python **3.10 or higher** (3.11 / 3.12 recommended; if using 3.13, ensure `scikit-image >= 0.26.0`)
- OS: The author currently guarantees its availability on Windows only.

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/cotseccsc/SRS-DAC.git
cd SRS-DAC

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Windows (CMD)
.venv\Scripts\activate.bat

# 3. Install dependencies
pip install -r requirements.txt
```

### Hint

If PowerShell throws **"cannot be loaded because running scripts is disabled on this system"**, run the following command once (applies to the current user only, no admin rights required):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## Usage

### Graphical User Interface

```bash
python SRS-DAC.py
```

**GUI Operations:**

1. Select the three TIFF files for **2850 cm⁻¹**, **2930 cm⁻¹**, and **2980 cm⁻¹** respectively.
2. Select the **Output Root Directory**.
3. Click **Start Correction** and monitor the log below.
4. A prompt will appear upon completion. Results are saved in a subfolder named after the input file within the output directory.

The interface supports Chinese / English language switching.

---

## Input Requirements

- **Three TIFF files** corresponding to wavenumbers 2850, 2930, and 2980 cm⁻¹.
- All three files must have **exactly the same spatial dimensions** `(z, y, x)` and data type.

---

## Output Structure

```
<Output Root Directory>/
└── <2850 filename (without extension)>/
    ├── CellExtraction/
    │   ├── diff_2930_minus_2980.tif    # Difference image for cell segmentation
    │   ├── cell_mask.tif               # Cell binary mask (uint8)
    │   └── cell_segmented.tif          # Segmented Cell
    ├── LDExtraction/
    │   ├── diff_2850_minus_2980.tif    # Difference image for lipid droplet segmentation
    │   ├── lipid_mask.tif              # Lipid droplet binary mask (uint8)
    │   └── lipid_segmented.tif         # Segmented Lipid Droplets
    ├── Result/
    │   ├── cell_normalized.tiff        # Normalized whole cell image
    │   └── cytoplasm_normalized.tiff   # Normalized cytoplasm image
    └── Analysis/
        ├── slice_means.png             # Mean cytoplasmic intensity curve per slice
        └── normalization_info.txt      # Slice-wise mean intensity and scaling factors
```

`normalization_info.txt` format:

```
# Maximum intensity slice index: <int>
# Maximum mean intensity value: <float>
# Format: slice_index, mean_intensity, scale_factor
0, <mean_0>, <scale_0>
1, <mean_1>, <scale_1>
...
```

---

## Parameter Description

To adjust segmentation results for different samples, you can modify the default parameters in `process.py`:

### Cell Segmentation `get_cell_mask_3d`

| Parameter | Default | Description |
|---|---|---|
| `median_size` | 3 | 3D median filter kernel size for denoising |
| `ball_radius_close` | 5 | 3D closing ball radius to fill small internal holes |
| `ball_radius_open` | 2 | 3D opening ball radius to remove external burrs |
| `extra_fill_iterations` | 2 | Number of extra hole-filling iterations |

### Lipid Droplet Segmentation `segment_lipid_global_threshold`

| Parameter | Default | Description |
|---|---|---|
| `threshold` | `None` | `None` means automatic Otsu threshold; a manual threshold can also be passed |
| `median_filter_size` | 3 (passed as 0) | Median filter kernel size; 0 means no filtering |
| `min_size` | 3 (passed as 0) | Minimum connected component voxel size; 0 means no filtering |
| `close_radius` | 1 | 3D closing ball radius |

---

## Patent and Licensing

This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE) for details.

**Patent Notice**

The methods implemented in this project are subject to a pending patent application. In accordance with Section 3 of the Apache License 2.0, the copyright holders and contributors grant a patent license to all users who comply with this license to practice the relevant patents embodied in the contributed code. This patent grant is conditional upon compliance with the license and is subject to the defensive termination clause described therein. Specifically, if any user initiates patent litigation against the contributors regarding this project, their patent grant obtained under this license will automatically terminate.

---

## Acknowledgments

This tool is built upon the following open-source projects: [NumPy](https://numpy.org/), [SciPy](https://scipy.org/), [scikit-image](https://scikit-image.org/), [tifffile](https://github.com/cgohlke/tifffile), [Matplotlib](https://matplotlib.org/).

---
