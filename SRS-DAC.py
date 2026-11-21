
# Copyright 2026 Jikang Zhang, Zhengyan Wu

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import numpy as np
import tifffile

# 导入原处理脚本中的核心函数
from process import (
    get_cell_mask_3d,
    segment_lipid_global_threshold,
    process_image
)

# 原脚本中定义的辅助函数，由于是局部函数无法导入，在此重新定义
def to_3d(arr):
    """将输入数组统一转换为 3D (z, y, x) 形状"""
    if arr.ndim == 2:
        return arr[np.newaxis, ...]
    elif arr.ndim == 4:
        return arr[..., 0]
    return arr


class RedirectText:
    """将 print 输出重定向到 tkinter 文本框控件"""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.after(0, lambda: (
        self.text_widget.insert(tk.END, string),
        self.text_widget.see(tk.END),
        self.text_widget.update(),
    ))

    def flush(self):
        pass


class LipidCellProcessorUI:
    def __init__(self, root):
        self.root = root
        self.lang = 'zh'  # 默认语言：中文

        # 所有界面文本（中英文对照）
        self.strings = {
            'zh': {
                'window_title': '卵母细胞SRS成像深度校正工具',
                'input_frame': '输入图像',
                'label_2850': '2856 cm⁻¹ 图像:',
                'label_2930': '2930 cm⁻¹ 图像:',
                'label_2980': '2980 cm⁻¹ 图像:',
                'output_frame': '输出设置',
                'label_output': '输出文件夹:',
                'btn_run': '开始校正',
                'btn_clear': '清空日志',
                'btn_help': '帮助',
                'btn_lang': '切换语言',
                'browse_btn': '浏览...',
                'browse_title': '选择文件',
                'log_frame': '运行信息（日志）',
                'help_title': '帮助',
                'help_text': (
                    "【方法简介】\n"
                    "本工具用于处理卵母细胞SRS（受激拉曼散射）成像数据，实现深度衰减校正、"
                    "【使用步骤】\n"
                    "1. 分别选择三个波数（2856、2930、2980 cm⁻¹）的TIFF堆栈文件；\n"
                    "2. 选择一个输出根目录，程序将在此目录下以输入文件名创建子文件夹保存结果；\n"
                    "3. 点击“开始校正”按钮，处理过程将自动进行（请观察下方日志）；\n"
                    "4. 处理完成后会弹出提示，结果包含：细胞掩膜、脂滴掩膜、输出结果、校正系数等。\n\n"
                    "【注意事项】\n"
                    "• 三个输入图像必须具有相同的尺寸（z, y, x）和数据类型；\n"
                    "• 建议使用TIFF格式，支持3D文件；\n"
                    "• 处理时间取决于图像体积大小，请耐心等待；\n"
                    "• 如需中断，请直接关闭程序；\n"
                    "• 若遇到错误，请检查日志中的详细报错信息。\n\n"
                    "【技术支持】\n"
                    "本工具基于Python开发，使用Tkinter界面。如有问题，请查阅相关文档。"
                ),
                'error_no_files': '请选择所有三个输入文件！',
                'error_no_output': '请选择输出根目录！',
                'error_file_not_exist': '文件不存在: {path}',
                'info_complete': '处理成功！\n结果保存在:\n{path}',
                'error_processing': '发生错误，请查看日志。\n{error}',
                'btn_run_processing': '处理中...',
            },
            'en': {
                'window_title': 'Oocyte SRS Imaging Depth Correction Tool',
                'input_frame': 'Input Images',
                'label_2850': '2856 cm⁻¹ Image:',
                'label_2930': '2930 cm⁻¹ Image:',
                'label_2980': '2980 cm⁻¹ Image:',
                'output_frame': 'Output Settings',
                'label_output': 'Output Folder:',
                'btn_run': 'Start Correction',
                'btn_clear': 'Clear Log',
                'btn_help': 'Help',
                'btn_lang': 'Switch Language',
                'browse_btn': 'Browse...',
                'browse_title': 'Select File',
                'log_frame': 'Log Information',
                'help_title': 'Help',
                'help_text': (
                    "【Method Introduction】\n"
                    "This tool processes oocyte SRS (Stimulated Raman Scattering) imaging data for depth attenuation correction.\n"
                    "【Usage Steps】\n"
                    "1. Select TIFF stack files for three wavenumbers (2856, 2930, 2980 cm⁻¹);\n"
                    "2. Choose an output root directory; the program will create subfolders named after the input file;\n"
                    "3. Click 'Start Correction' and the processing will proceed automatically (watch the log below);\n"
                    "4. Upon completion, a popup will appear. Results include: cell mask, lipid mask, corrected images, coefficients, etc.\n\n"
                    "【Notes】\n"
                    "• All three input images must have identical dimensions (z, y, x) and data type;\n"
                    "• TIFF format is recommended, 3D files are supported;\n"
                    "• Processing time depends on image volume, please be patient;\n"
                    "• To interrupt, simply close the program;\n"
                    "• If an error occurs, check the log for detailed information.\n\n"
                    "【Support】\n"
                    "This tool is built with Python and Tkinter. For questions, please refer to relevant documentation."
                ),
                'error_no_files': 'Please select all three input files!',
                'error_no_output': 'Please select an output root directory!',
                'error_file_not_exist': 'File does not exist: {path}',
                'info_complete': 'Processing completed successfully!\nResults saved in:\n{path}',
                'error_processing': 'An error occurred. Please check the log.\n{error}',
                'btn_run_processing': 'Processing...',
            }
        }

        # 文件路径变量
        self.path_2850 = tk.StringVar()
        self.path_2930 = tk.StringVar()
        self.path_2980 = tk.StringVar()
        self.output_dir = tk.StringVar()

        # 保存需要更新语言的控件引用
        self.lang_widgets = []

        # 创建界面
        self.create_widgets()

        # 重定向 stdout 和 stderr
        self.redirect_output()

        # 设置窗口标题
        self.root.title(self.get_text('window_title'))

        # 应用初始语言设置（包括翻转语言按钮）
        self.update_ui_language()

    def get_text(self, key, **kwargs):
        """根据当前语言获取指定键的文本，支持占位符替换"""
        text = self.strings[self.lang].get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

    def create_widgets(self):
        # 主框架
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 文件选择区域
        file_frame = tk.LabelFrame(main_frame, text=self.get_text('input_frame'), padx=5, pady=5)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        self.lang_widgets.append((file_frame, 'input_frame'))

        # 2850 文件
        row1 = tk.Frame(file_frame)
        row1.pack(fill=tk.X, pady=2)
        label1 = tk.Label(row1, text=self.get_text('label_2850'), width=14, anchor='w')
        label1.pack(side=tk.LEFT)
        self.lang_widgets.append((label1, 'label_2850'))
        tk.Entry(row1, textvariable=self.path_2850, width=50).pack(side=tk.LEFT, padx=(5, 5), expand=True, fill=tk.X)
        browse_btn1 = tk.Button(row1, text=self.get_text('browse_btn'), command=self.browse_2850)
        browse_btn1.pack(side=tk.RIGHT)
        self.lang_widgets.append((browse_btn1, 'browse_btn'))

        # 2930 文件
        row2 = tk.Frame(file_frame)
        row2.pack(fill=tk.X, pady=2)
        label2 = tk.Label(row2, text=self.get_text('label_2930'), width=14, anchor='w')
        label2.pack(side=tk.LEFT)
        self.lang_widgets.append((label2, 'label_2930'))
        tk.Entry(row2, textvariable=self.path_2930, width=50).pack(side=tk.LEFT, padx=(5, 5), expand=True, fill=tk.X)
        browse_btn2 = tk.Button(row2, text=self.get_text('browse_btn'), command=self.browse_2930)
        browse_btn2.pack(side=tk.RIGHT)
        self.lang_widgets.append((browse_btn2, 'browse_btn'))

        # 2980 文件
        row3 = tk.Frame(file_frame)
        row3.pack(fill=tk.X, pady=2)
        label3 = tk.Label(row3, text=self.get_text('label_2980'), width=14, anchor='w')
        label3.pack(side=tk.LEFT)
        self.lang_widgets.append((label3, 'label_2980'))
        tk.Entry(row3, textvariable=self.path_2980, width=50).pack(side=tk.LEFT, padx=(5, 5), expand=True, fill=tk.X)
        browse_btn3 = tk.Button(row3, text=self.get_text('browse_btn'), command=self.browse_2980)
        browse_btn3.pack(side=tk.RIGHT)
        self.lang_widgets.append((browse_btn3, 'browse_btn'))

        # 输出目录选择
        out_frame = tk.LabelFrame(main_frame, text=self.get_text('output_frame'), padx=5, pady=5)
        out_frame.pack(fill=tk.X, pady=(0, 10))
        self.lang_widgets.append((out_frame, 'output_frame'))

        row_out = tk.Frame(out_frame)
        row_out.pack(fill=tk.X, pady=2)
        label_out = tk.Label(row_out, text=self.get_text('label_output'), width=14, anchor='w')
        label_out.pack(side=tk.LEFT)
        self.lang_widgets.append((label_out, 'label_output'))
        tk.Entry(row_out, textvariable=self.output_dir, width=50).pack(side=tk.LEFT, padx=(5, 5), expand=True, fill=tk.X)
        browse_btn_out = tk.Button(row_out, text=self.get_text('browse_btn'), command=self.browse_output)
        browse_btn_out.pack(side=tk.RIGHT)
        self.lang_widgets.append((browse_btn_out, 'browse_btn'))

        # 控制按钮
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.run_btn = tk.Button(btn_frame, text=self.get_text('btn_run'),
                                 command=self.start_processing,
                                 bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'), padx=10)
        self.run_btn.pack(side=tk.LEFT, padx=5)
        self.lang_widgets.append((self.run_btn, 'btn_run'))

        clear_btn = tk.Button(btn_frame, text=self.get_text('btn_clear'), command=self.clear_log)
        clear_btn.pack(side=tk.LEFT, padx=5)
        self.lang_widgets.append((clear_btn, 'btn_clear'))

        help_btn = tk.Button(btn_frame, text=self.get_text('btn_help'), command=self.show_help)
        help_btn.pack(side=tk.LEFT, padx=5)
        self.lang_widgets.append((help_btn, 'btn_help'))

        lang_btn = tk.Button(btn_frame, text=self.get_text('btn_lang'), command=self.toggle_language)
        lang_btn.pack(side=tk.RIGHT, padx=5)
        self.lang_widgets.append((lang_btn, 'btn_lang'))

        # 日志输出区域
        log_frame = tk.LabelFrame(main_frame, text=self.get_text('log_frame'), padx=5, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.lang_widgets.append((log_frame, 'log_frame'))

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=80, height=20)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def toggle_language(self):
        """切换语言并刷新界面"""
        self.lang = 'en' if self.lang == 'zh' else 'zh'
        self.update_ui_language()

    def update_ui_language(self):
        """更新所有已注册控件的文本（语言按钮特殊处理：显示相反语言）"""
        for widget, key in self.lang_widgets:
            try:
                if key == 'btn_lang':
                    # 按钮文本显示与当前界面相反的语言
                    if self.lang == 'zh':
                        text = self.strings['en']['btn_lang']  # "Switch Language"
                    else:
                        text = self.strings['zh']['btn_lang']  # "切换语言"
                    widget.config(text=text)
                else:
                    widget.config(text=self.get_text(key))
            except tk.TclError:
                # 控件可能已被销毁，忽略
                pass
        # 更新窗口标题
        self.root.title(self.get_text('window_title'))
        # 如果运行按钮处于正常状态，更新其文本；否则保持当前文本（如“处理中...”）
        if self.run_btn['state'] == tk.NORMAL:
            self.run_btn.config(text=self.get_text('btn_run'))

    def browse_2850(self):
        filename = filedialog.askopenfilename(
            title=self.get_text('browse_title'),
            filetypes=[("TIFF", "*.tif *.tiff"), ("All", "*.*")]
        )
        if filename:
            self.path_2850.set(filename)

    def browse_2930(self):
        filename = filedialog.askopenfilename(
            title=self.get_text('browse_title'),
            filetypes=[("TIFF", "*.tif *.tiff"), ("All", "*.*")]
        )
        if filename:
            self.path_2930.set(filename)

    def browse_2980(self):
        filename = filedialog.askopenfilename(
            title=self.get_text('browse_title'),
            filetypes=[("TIFF", "*.tif *.tiff"), ("All", "*.*")]
        )
        if filename:
            self.path_2980.set(filename)

    def browse_output(self):
        dirname = filedialog.askdirectory(title=self.get_text('browse_title'))
        if dirname:
            self.output_dir.set(dirname)

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def redirect_output(self):
        """将 sys.stdout 和 sys.stderr 重定向到文本框"""
        self.redirector = RedirectText(self.log_text)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

    def show_help(self):
        """显示帮助信息"""
        messagebox.showinfo(
            title=self.get_text('help_title'),
            message=self.get_text('help_text')
        )

    def start_processing(self):
        """在单独线程中启动处理"""
        # 检查输入
        if not all([self.path_2850.get(), self.path_2930.get(), self.path_2980.get()]):
            messagebox.showerror(
                title=self.get_text('help_title'),
                message=self.get_text('error_no_files')
            )
            return
        if not self.output_dir.get():
            messagebox.showerror(
                title=self.get_text('help_title'),
                message=self.get_text('error_no_output')
            )
            return

        # 检查文件存在性
        for p in [self.path_2850.get(), self.path_2930.get(), self.path_2980.get()]:
            if not os.path.exists(p):
                messagebox.showerror(
                    title=self.get_text('help_title'),
                    message=self.get_text('error_file_not_exist', path=p)
                )
                return

        # 禁用按钮，避免重复点击
        self.run_btn.config(state=tk.DISABLED, text=self.get_text('btn_run_processing'))

        # 在新线程中运行处理
        thread = threading.Thread(target=self.processing_thread, daemon=True)
        thread.start()

    def processing_thread(self):
        """实际执行处理逻辑的线程函数"""
        try:
            self._run_processing()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                title=self.get_text('help_title'),
                message=self.get_text('error_processing', error=str(e))
            )
        finally:
            # 恢复按钮状态
            self.root.after(0, lambda: self.run_btn.config(
                state=tk.NORMAL, text=self.get_text('btn_run')
            ))

    def _run_processing(self):
        """核心处理流程（与原 main 函数类似，但使用用户选择的输出目录）"""
        print("=" * 50)
        print("开始处理...")
        print(f"2850: {self.path_2850.get()}")
        print(f"2930: {self.path_2930.get()}")
        print(f"2980: {self.path_2980.get()}")
        print(f"输出根目录: {self.output_dir.get()}")
        print("=" * 50)

        # 加载图像
        print("\n加载图像...")
        img_2850 = tifffile.imread(self.path_2850.get())
        img_2930 = tifffile.imread(self.path_2930.get())
        img_2980 = tifffile.imread(self.path_2980.get())

        # 统一为3D
        img_2850 = to_3d(img_2850)
        img_2930 = to_3d(img_2930)
        img_2980 = to_3d(img_2980)

        if not (img_2850.shape == img_2930.shape == img_2980.shape):
            raise ValueError("输入图像尺寸必须一致")

        # 计算差值图像
        print("计算差值图像...")
        diff_cell = img_2930.astype(np.float32) - img_2980.astype(np.float32)
        diff_lipid = img_2850.astype(np.float32) - img_2980.astype(np.float32)

        # 创建输出目录结构（基于用户选择的根目录和2850文件名）
        base_name = os.path.splitext(os.path.basename(self.path_2850.get()))[0]
        root_dir = os.path.join(self.output_dir.get(), base_name)
        os.makedirs(root_dir, exist_ok=True)

        cell_dir = os.path.join(root_dir, "CellExtraction")
        lipid_dir = os.path.join(root_dir, "LDExtraction")
        result_dir = os.path.join(root_dir, "Result")
        analysis_dir = os.path.join(root_dir, "Analysis")
        for d in [cell_dir, lipid_dir, result_dir, analysis_dir]:
            os.makedirs(d, exist_ok=True)

        # 保存差值图像
        tifffile.imwrite(os.path.join(cell_dir, "diff_2930_minus_2980.tif"), diff_cell.astype(np.float32))
        tifffile.imwrite(os.path.join(lipid_dir, "diff_2850_minus_2980.tif"), diff_lipid.astype(np.float32))
        print("差值图像已保存。")

        # 细胞分割
        print("\n--- 细胞分割 ---")
        cell_mask = get_cell_mask_3d(diff_cell,
                                     median_size=3,
                                     ball_radius_close=5,
                                     ball_radius_open=2,
                                     extra_fill_iterations=2)
        tifffile.imwrite(os.path.join(cell_dir, "cell_mask.tif"), cell_mask.astype(np.uint8))
        cell_segmented = diff_cell * cell_mask
        tifffile.imwrite(os.path.join(cell_dir, "cell_segmented.tif"), cell_segmented.astype(np.float32))
        print("细胞掩膜已保存。")

        # 脂滴分割
        print("\n--- 脂滴分割 ---")
        lipid_mask = segment_lipid_global_threshold(diff_lipid,
                                                    threshold=None,
                                                    median_filter_size=0,
                                                    min_size=0,
                                                    close_radius=1)
        tifffile.imwrite(os.path.join(lipid_dir, "lipid_mask.tif"), lipid_mask.astype(np.uint8))
        lipid_segmented = diff_lipid * lipid_mask
        tifffile.imwrite(os.path.join(lipid_dir, "lipid_segmented.tif"), lipid_segmented.astype(np.float32))
        print("脂滴掩膜已保存。")

        # 归一化处理（使用原始图像 img_2850）
        print("\n--- 归一化与结果输出 ---")
        process_image(img_2850, cell_mask, lipid_mask, result_dir, analysis_dir)

        print(f"\n处理完成！所有结果保存在: {root_dir}")
        print("=" * 50)
        # 弹出完成提示
        self.root.after(0, lambda: messagebox.showinfo(
            title=self.get_text('help_title'),
            message=self.get_text('info_complete', path=root_dir)
        ))


def main():
    root = tk.Tk()
    app = LipidCellProcessorUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()