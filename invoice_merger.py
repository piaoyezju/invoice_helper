"""
发票合并工具 - 将图片/PDF发票合并到A4纸上打印
支持: JPG, PNG, BMP, TIFF, PDF
布局: 按长宽比排序，大图每页2张，小图每页3张。竖向源文件自动旋转90度。
"""

import fitz  # PyMuPDF
from PIL import Image
import io
import os
import sys
import tempfile
from auto_crop import auto_crop_invoice


# A4 尺寸 (单位: 点, 1点 = 1/72英寸)
A4_WIDTH = 595.28
A4_HEIGHT = 841.89
MARGIN = 15  # 页边距
GAP = 10  # 两个发票之间的间距

# 支持的图片格式
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp')


def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def is_pdf(path):
    return os.path.splitext(path)[1].lower() == '.pdf'


def img_to_temp_pdf(img_path):
    """将图片转为临时PDF文件，返回临时PDF路径。竖向图片先旋转。"""
    img = Image.open(img_path)
    if img.mode == 'RGBA':
        img = img.convert('RGB')

    w, h = img.size
    rotated = h > w
    if rotated:
        img = img.rotate(-90, expand=True)  # 顺时针90度
        w, h = h, w

    # 以图片尺寸创建PDF页面
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_path = tmp.name
    tmp.close()
    img.save(tmp_path, 'PDF', resolution=150)
    return tmp_path


def _fit_rect(src_w, src_h, dst_w, dst_h):
    """保持宽高比的缩放，返回 (new_w, new_h, x_off, y_off)"""
    ratio = min(dst_w / src_w, dst_h / src_h)
    nw = src_w * ratio
    nh = src_h * ratio
    return nw, nh, (dst_w - nw) / 2, (dst_h - nh) / 2


def _add_image_to_section(page, img_path, y_start, section_h):
    """将图片放入指定区域（竖向自动旋转）。img_path 应为已抠图的路径。"""
    try:
        img = Image.open(img_path)
        src_w, src_h = img.size
        img.close()

        if src_h > src_w:
            src_w, src_h = src_h, src_w

        dst_w = A4_WIDTH - 2 * MARGIN
        new_w, new_h, x_off, y_off = _fit_rect(src_w, src_h, dst_w, section_h)

        tmp_pdf = img_to_temp_pdf(img_path)
        try:
            src_doc = fitz.open(tmp_pdf)
            target = fitz.Rect(MARGIN + x_off, y_start + y_off,
                               MARGIN + x_off + new_w, y_start + y_off + new_h)
            page.show_pdf_page(target, src_doc, 0)
            src_doc.close()
        finally:
            try:
                os.unlink(tmp_pdf)
            except:
                pass
    except Exception:
        pass


def _add_pdf_to_section(page, src_doc, src_page_num, y_start, section_h):
    """将PDF页面放入指定区域（竖向自动旋转）。"""
    sp = src_doc[src_page_num]
    src_w, src_h = sp.rect.width, sp.rect.height
    if src_h > src_w:
        src_w, src_h = src_h, src_w

    dst_w = A4_WIDTH - 2 * MARGIN
    new_w, new_h, x_off, y_off = _fit_rect(src_w, src_h, dst_w, section_h)

    target = fitz.Rect(MARGIN + x_off, y_start + y_off,
                       MARGIN + x_off + new_w, y_start + y_off + new_h)
    page.show_pdf_page(target, src_doc, src_page_num, rotate=90 if sp.rect.height > sp.rect.width else 0)


def _draw_cut_lines(page, n):
    """画裁剪线。n=2: 中间一条线; n=3: 两条线三等分。"""
    usable = A4_HEIGHT - 2 * MARGIN
    for idx in range(1, n):
        y = MARGIN + (usable / n) * idx - GAP / 2
        p1 = fitz.Point(MARGIN, y)
        p2 = fitz.Point(A4_WIDTH - MARGIN, y)
        page.draw_line(p1, p2, color=(0.5, 0.5, 0.5), width=0.5, dashes="[3 3]")
        scissor = "✂"
        page.insert_text(fitz.Point(MARGIN - 2, y + 3), scissor, fontsize=8, color=(0.5, 0.5, 0.5))


def _get_size(path, effective_path):
    """获取文件旋转后的宽高。"""
    try:
        if is_pdf(path):
            pdf_doc = fitz.open(path)
            pw, ph = pdf_doc[0].rect.width, pdf_doc[0].rect.height
            pdf_doc.close()
            w, h = (ph, pw) if ph > pw else (pw, ph)
        else:
            img = Image.open(effective_path)
            w, h = img.size
            img.close()
            if h > w:
                w, h = h, w
    except:
        w, h = 1, 1
    return w, h


def _sort_by_rendered(items):
    """按渲染高度降序排序。"""
    usable_w = A4_WIDTH - 2 * MARGIN
    for i, (path, eff_path, w, h) in enumerate(items):
        rendered = (h * usable_w / w) if w > 0 and h > 0 else 0
        items[i] = (path, eff_path, w, h, rendered)
    items.sort(key=lambda x: x[4], reverse=True)
    return items


def build_merged_doc(files, auto_crop=False):
    """动态排版：按渲染高度排序，高图2拼，矮图3拼。"""
    usable_h = A4_HEIGHT - 2 * MARGIN
    usable_w = A4_WIDTH - 2 * MARGIN
    threshold_h = usable_h / 3

    temp_files = []
    items = []

    for path in files:
        effective_path = path
        if auto_crop and is_image(path):
            cropped = auto_crop_invoice(path)
            if cropped is not None:
                tmp_crop = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                cropped.save(tmp_crop.name, 'PNG')
                tmp_crop.close()
                effective_path = tmp_crop.name
                temp_files.append(effective_path)

        if is_pdf(path) or is_image(path):
            w, h = _get_size(path, effective_path)
            items.append((path, effective_path, w, h))

    items = _sort_by_rendered(items)

    doc = fitz.open()
    try:
        idx = 0
        while idx < len(items):
            _, _, w, h, rendered_h = items[idx]
            count = 2 if rendered_h > threshold_h else 3

            page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
            section_h = ((usable_h - GAP) / 2) if count == 2 else ((usable_h - 2 * GAP) / 3)
            y = MARGIN

            for j in range(count):
                if idx + j >= len(items):
                    break
                orig_p, eff_p = items[idx + j][0], items[idx + j][1]
                if is_image(orig_p):
                    _add_image_to_section(page, eff_p, y, section_h)
                elif is_pdf(orig_p):
                    try:
                        src = fitz.open(eff_p)
                        _add_pdf_to_section(page, src, 0, y, section_h)
                        src.close()
                    except:
                        pass
                y += section_h + GAP

            _draw_cut_lines(page, count)
            idx += count
    finally:
        for tf in temp_files:
            try:
                os.unlink(tf)
            except:
                pass
    return doc


def merge_two_files(file1, file2, output_path, auto_crop=False):
    """将两个文件合并到一张A4纸上，保存到 output_path"""
    doc = build_merged_doc([file1, file2], auto_crop=auto_crop)
    doc.save(output_path)
    doc.close()
    return output_path


def render_preview(files, dpi=150, auto_crop=False):
    """生成预览图，返回 PIL Image 列表（每页一张图）。"""
    from PIL import Image as PILImage
    import io

    doc = build_merged_doc(files, auto_crop=auto_crop)
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = PILImage.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    doc.close()
    return images


def print_direct(files, printer_name=None, auto_crop=False):
    """合并文件并直接调用系统打印，不打开任何应用程序。"""
    doc = build_merged_doc(files, auto_crop=auto_crop)
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_path = tmp.name
    tmp.close()
    doc.save(tmp_path)
    doc.close()

    try:
        if sys.platform == 'win32':
            _print_windows(tmp_path, printer_name)
        else:
            _print_unix(tmp_path, printer_name)
    finally:
        import threading
        def cleanup():
            import time
            time.sleep(10)
            try:
                os.unlink(tmp_path)
            except:
                pass
        threading.Thread(target=cleanup, daemon=True).start()


def _print_windows(pdf_path, printer_name=None):
    """Windows: 直接调用打印机，不打开应用。"""
    import win32print
    import win32ui
    import win32con
    from PIL import ImageWin, Image

    doc = fitz.open(pdf_path)
    images = []
    zoom = 300 / 72
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    doc.close()

    printer = printer_name or win32print.GetDefaultPrinter()
    hprinter = win32print.OpenPrinter(printer)
    try:
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer)
        page_w = hdc.GetDeviceCaps(win32con.PHYSICALWIDTH)
        page_h = hdc.GetDeviceCaps(win32con.PHYSICALHEIGHT)

        hdc.StartDoc("Invoice")
        for img in images:
            hdc.StartPage()
            dib = ImageWin.Dib(img)
            dib.draw(hdc.GetHandleOutput(), (0, 0, page_w, page_h))
            hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()
    finally:
        win32print.ClosePrinter(hprinter)


def _print_unix(pdf_path, printer_name=None):
    """macOS/Linux: 用 lp 命令打印。"""
    import subprocess
    cmd = ['lp']
    if printer_name:
        cmd += ['-d', printer_name]
    cmd.append(pdf_path)
    subprocess.run(cmd, check=True)


def merge_multiple_pairs(files, output_dir, output_name=None):
    """批量合并: 每两个文件一组，生成独立PDF"""
    results = []
    for i in range(0, len(files), 2):
        if i + 1 < len(files):
            f1, f2 = files[i], files[i + 1]
            name = f"{output_name}_{i // 2 + 1}.pdf" if output_name else f"merged_{i // 2 + 1}.pdf"
            out = os.path.join(output_dir, name)
            merge_two_files(f1, f2, out)
            results.append(out)
        else:
            f1 = files[i]
            name = f"{output_name}_{i // 2 + 1}_single.pdf" if output_name else f"merged_{i // 2 + 1}_single.pdf"
            out = os.path.join(output_dir, name)
            doc = build_merged_doc([f1])
            doc.save(out)
            doc.close()
            results.append(out)
    return results


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法: python invoice_merger.py <文件1> <文件2> [输出文件名]")
        print("支持: JPG, PNG, BMP, TIFF, PDF")
        sys.exit(1)

    f1, f2 = sys.argv[1], sys.argv[2]
    out = sys.argv[3] if len(sys.argv) > 3 else "merged_output.pdf"
    result = merge_two_files(f1, f2, out)
    print(f"已生成: {result}")
