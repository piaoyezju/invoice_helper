"""
发票合并工具 - GUI界面
支持文件拖入、打印预览、直接打印
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import os
import sys
from PIL import Image, ImageTk

from invoice_merger import (
    build_merged_doc, merge_two_files, merge_multiple_pairs,
    render_preview, print_direct,
    is_image, is_pdf,
)


class InvoiceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("发票合并打印工具")
        self.root.geometry("620x610")
        self.root.resizable(False, False)
        self.files = []
        self.auto_crop_var = tk.BooleanVar(value=True)
        self._build_ui()
        self._setup_drop()

    def _build_ui(self):
        tk.Label(self.root, text="发票合并打印工具", font=("微软雅黑", 16, "bold")).pack(pady=8)
        tk.Label(self.root, text="A4竖放，上下各一张横向发票（竖向自动旋转）",
                 font=("微软雅黑", 9), fg="gray").pack()

        # 拖放提示区域
        self.drop_frame = tk.LabelFrame(self.root, text="拖放文件到这里", font=("微软雅黑", 10))
        self.drop_frame.pack(padx=15, pady=(8, 0), fill="x")

        self.drop_label = tk.Label(
            self.drop_frame,
            text="将发票图片或PDF拖到这里\n支持 JPG / PNG / BMP / TIFF / PDF",
            font=("微软雅黑", 10), fg="#888", height=3
        )
        self.drop_label.pack(fill="x", padx=10, pady=5)

        # 文件列表
        frame_files = tk.LabelFrame(self.root, text="已选择的文件", font=("微软雅黑", 10))
        frame_files.pack(padx=15, pady=8, fill="both", expand=True)

        self.listbox = tk.Listbox(frame_files, height=7, font=("微软雅黑", 9))
        self.listbox.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar = tk.Scrollbar(frame_files, command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y", pady=5)
        self.listbox.config(yscrollcommand=scrollbar.set)

        # 操作按钮
        frame_btns = tk.Frame(self.root)
        frame_btns.pack(pady=4)

        for col, (text, cmd) in enumerate([
            ("添加文件", self.add_files),
            ("移除选中", self.remove_selected),
            ("清空列表", self.clear_files),
        ]):
            tk.Button(frame_btns, text=text, width=10, font=("微软雅黑", 9),
                      command=cmd).grid(row=0, column=col, padx=4)

        # 排序 + 复制
        frame_order = tk.Frame(self.root)
        frame_order.pack(pady=2)
        for col, (text, cmd) in enumerate([
            ("上移", self.move_up), ("下移", self.move_down), ("复制一份", self.duplicate_last),
        ]):
            tk.Button(frame_order, text=text, width=8, font=("微软雅黑", 9),
                      command=cmd).grid(row=0, column=col, padx=4)

        # 自动裁剪选项
        frame_options = tk.Frame(self.root)
        frame_options.pack(pady=2)
        tk.Checkbutton(frame_options, text="自动裁剪发票区域（去除截图多余部分）",
                       variable=self.auto_crop_var, font=("微软雅黑", 9)).pack()

        # 预览 + 打印按钮
        frame_action = tk.Frame(self.root)
        frame_action.pack(pady=8)

        tk.Button(frame_action, text="预览", width=14, height=2,
                  font=("微软雅黑", 11, "bold"), bg="#2196F3", fg="white",
                  command=self.do_preview).grid(row=0, column=0, padx=8)

        tk.Button(frame_action, text="直接打印", width=14, height=2,
                  font=("微软雅黑", 11, "bold"), bg="#4CAF50", fg="white",
                  command=self.do_print).grid(row=0, column=1, padx=8)

    def _setup_drop(self):
        """设置文件拖放支持"""
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self._on_drop)

    def _on_drop(self, event):
        """处理拖入的文件"""
        # tkinterdnd2 用空格分隔多个文件，花括号包裹含空格的路径
        raw = event.data
        files = self._parse_dnd_paths(raw)

        added = 0
        skipped = 0
        for f in files:
            if not os.path.isfile(f):
                continue
            if is_image(f) or is_pdf(f):
                self.files.append(f)
                self.listbox.insert(tk.END, os.path.basename(f))
                added += 1
            else:
                skipped += 1

        if added > 0:
            self.drop_label.config(text=f"已添加 {added} 个文件", fg="#4CAF50")
            self.root.after(2000, lambda: self.drop_label.config(
                text="将发票图片或PDF拖到这里\n支持 JPG / PNG / BMP / TIFF / PDF", fg="#888"))
        if skipped > 0:
            messagebox.showwarning("提示", f"跳过 {skipped} 个不支持的文件")

    @staticmethod
    def _parse_dnd_paths(data):
        """解析 tkinterdnd2 拖放路径数据，处理花括号包裹的含空格路径"""
        paths = []
        i = 0
        while i < len(data):
            if data[i] == '{':
                j = data.index('}', i)
                paths.append(data[i + 1:j])
                i = j + 2  # 跳过 } 和空格
            elif data[i] == ' ':
                i += 1
            else:
                j = data.find(' ', i)
                if j == -1:
                    j = len(data)
                paths.append(data[i:j])
                i = j + 1
        return paths

    def add_files(self):
        filetypes = [
            ("所有支持的文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp *.pdf"),
            ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp"),
            ("PDF文件", "*.pdf"),
        ]
        paths = filedialog.askopenfilenames(title="选择发票文件", filetypes=filetypes)
        for p in paths:
            self.files.append(p)
            self.listbox.insert(tk.END, os.path.basename(p))

    def remove_selected(self):
        sel = self.listbox.curselection()
        for i in reversed(sel):
            self.listbox.delete(i)
            del self.files[i]

    def clear_files(self):
        self.files.clear()
        self.listbox.delete(0, tk.END)

    def move_up(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return
        i = sel[0]
        self.files[i - 1], self.files[i] = self.files[i], self.files[i - 1]
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i - 1, text)
        self.listbox.selection_set(i - 1)

    def move_down(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] == self.listbox.size() - 1:
            return
        i = sel[0]
        self.files[i], self.files[i + 1] = self.files[i + 1], self.files[i]
        text = self.listbox.get(i)
        self.listbox.delete(i)
        self.listbox.insert(i + 1, text)
        self.listbox.selection_set(i + 1)

    def duplicate_last(self):
        if not self.files:
            return
        last = self.files[-1]
        self.files.append(last)
        self.listbox.insert(tk.END, os.path.basename(last) + " (副本)")

    def _check_files(self):
        if len(self.files) < 1:
            messagebox.showwarning("提示", "请至少添加1个文件")
            return False
        return True

    def do_preview(self):
        if not self._check_files():
            return
        try:
            images = render_preview(self.files, dpi=150, auto_crop=self.auto_crop_var.get())
            PreviewWindow(self.root, images, self.files, auto_crop=self.auto_crop_var.get())
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {e}")

    def do_print(self):
        if not self._check_files():
            return
        printer = _ask_printer(self.root)
        if printer is None:
            return
        try:
            print_direct(self.files, printer_name=printer, auto_crop=self.auto_crop_var.get())
            messagebox.showinfo("提示", f"已发送到: {printer}")
        except Exception as e:
            messagebox.showerror("错误", f"打印失败: {e}")


class PreviewWindow:
    """打印预览窗口"""

    def __init__(self, parent, images, files, auto_crop=False):
        self.images = images
        self.files = files
        self.auto_crop = auto_crop
        self.current = 0
        self.zoom = 0.5
        self.tk_img = None

        self.win = tk.Toplevel(parent)
        self.win.title("打印预览")
        self.win.geometry("700x850")
        self.win.resizable(True, True)
        self._build()

    def _build(self):
        toolbar = tk.Frame(self.win)
        toolbar.pack(fill="x", padx=5, pady=5)

        self.btn_prev = tk.Button(toolbar, text="< 上一页", command=self.prev_page, width=10)
        self.btn_prev.pack(side="left", padx=5)

        self.page_label = tk.Label(toolbar, text="", font=("微软雅黑", 10))
        self.page_label.pack(side="left", padx=10)

        self.btn_next = tk.Button(toolbar, text="下一页 >", command=self.next_page, width=10)
        self.btn_next.pack(side="left", padx=5)

        tk.Button(toolbar, text="放大", command=self.zoom_in, width=6).pack(side="left", padx=5)
        tk.Button(toolbar, text="缩小", command=self.zoom_out, width=6).pack(side="left", padx=5)

        tk.Button(toolbar, text="打印", font=("微软雅黑", 10, "bold"),
                  bg="#4CAF50", fg="white", width=8,
                  command=self.do_print).pack(side="right", padx=5)
        tk.Button(toolbar, text="保存PDF", font=("微软雅黑", 10),
                  width=8, command=self.do_save).pack(side="right", padx=5)

        canvas_frame = tk.Frame(self.win)
        canvas_frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="#808080")
        self.canvas.pack(fill="both", expand=True)
        # 监听 canvas 尺寸变化，每次变化都重绘居中
        self.canvas.bind('<Configure>', lambda e: self._show_page())

    def _show_page(self):
        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        img = self.images[self.current]
        w = int(img.width * self.zoom)
        h = int(img.height * self.zoom)
        resized = img.resize((w, h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(resized)

        x = max(0, (cw - w) // 2)
        y = max(0, (ch - h) // 2)
        self.canvas.create_image(x, y, anchor="nw", image=self.tk_img)

        self.page_label.config(text=f"第 {self.current + 1} / {len(self.images)} 页")
        self.btn_prev.config(state="normal" if self.current > 0 else "disabled")
        self.btn_next.config(state="normal" if self.current < len(self.images) - 1 else "disabled")

    def prev_page(self):
        if self.current > 0:
            self.current -= 1
            self._show_page()

    def next_page(self):
        if self.current < len(self.images) - 1:
            self.current += 1
            self._show_page()

    def zoom_in(self):
        self.zoom = min(2.0, self.zoom + 0.1)
        self._show_page()

    def zoom_out(self):
        self.zoom = max(0.2, self.zoom - 0.1)
        self._show_page()

    def do_print(self):
        printer = _ask_printer(self.win)
        if printer is None:
            return
        try:
            print_direct(self.files, printer_name=printer, auto_crop=self.auto_crop)
            messagebox.showinfo("提示", f"已发送到: {printer}", parent=self.win)
        except Exception as e:
            messagebox.showerror("错误", f"打印失败: {e}", parent=self.win)

    def do_save(self):
        path = filedialog.asksaveasfilename(
            parent=self.win, title="保存PDF",
            defaultextension=".pdf", filetypes=[("PDF文件", "*.pdf")]
        )
        if not path:
            return
        try:
            doc = build_merged_doc(self.files, auto_crop=self.auto_crop)
            doc.save(path)
            doc.close()
            messagebox.showinfo("提示", f"已保存: {path}", parent=self.win)
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}", parent=self.win)


def _icon_path():
    """获取图标文件路径，兼容 PyInstaller"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    png = os.path.join(base, 'icon.png')
    return png if os.path.exists(png) else None


def _get_printers():
    """获取系统打印机列表"""
    if sys.platform == 'win32':
        import win32print
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        return [p[2] for p in printers]
    else:
        import subprocess
        result = subprocess.run(['lpstat', '-a'], capture_output=True, text=True)
        return [line.split()[0] for line in result.stdout.strip().split('\n') if line]


def _ask_printer(parent):
    """弹出打印机选择对话框，返回选中的打印机名，取消返回 None"""
    try:
        printers = _get_printers()
    except Exception:
        return None

    if not printers:
        messagebox.showwarning("提示", "未找到打印机", parent=parent)
        return None

    if len(printers) == 1:
        return printers[0]

    # 选择对话框
    dialog = tk.Toplevel(parent)
    dialog.title("选择打印机")
    dialog.geometry("350x280")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    tk.Label(dialog, text="请选择打印机:", font=("微软雅黑", 10)).pack(padx=15, pady=(15, 5), anchor="w")

    listbox = tk.Listbox(dialog, font=("微软雅黑", 9), height=8)
    listbox.pack(padx=15, pady=5, fill="both", expand=True)
    for p in printers:
        listbox.insert(tk.END, p)
    listbox.selection_set(0)

    result = [None]

    def on_ok():
        sel = listbox.curselection()
        if sel:
            result[0] = printers[sel[0]]
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="确定", width=10, command=on_ok).pack(side="left", padx=10)
    tk.Button(btn_frame, text="取消", width=10, command=on_cancel).pack(side="left", padx=10)

    dialog.bind('<Return>', lambda e: on_ok())
    dialog.bind('<Escape>', lambda e: on_cancel())

    parent.wait_window(dialog)
    return result[0]


def main():
    root = TkinterDnD.Tk()
    icon_path = _icon_path()
    if icon_path:
        img = Image.open(icon_path)
        icon_photo = ImageTk.PhotoImage(img)
        root.iconphoto(True, icon_photo)
        root._icon_photo = icon_photo  # 防止被GC回收
    InvoiceApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
