"""
发票合并工具 - 将2张图片或2份PDF发票合并到一张A4纸上打印
支持: JPG, PNG, BMP, TIFF, PDF
布局: A4竖放，上下各放一张横向发票。竖向源文件自动旋转90度。
"""

import fitz  # PyMuPDF
from PIL import Image
import os
import sys
import tempfile


# A4 尺寸 (单位: 点, 1点 = 1/72英寸)
A4_WIDTH = 595.28
A4_HEIGHT = 841.89
MARGIN = 15  # 页边距
GAP = 10  # 两个发票之间的间距

# 每个发票可用区域 (上半/下半)
ITEM_WIDTH = A4_WIDTH - 2 * MARGIN
ITEM_HEIGHT = (A4_HEIGHT - 2 * MARGIN - GAP) / 2

# 支持的图片格式
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp')


def is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def is_pdf(path):
    return os.path.splitext(path)[1].lower() == '.pdf'


def fit_rect(src_width, src_height, dst_width, dst_height):
    """计算保持宽高比的缩放尺寸和居中偏移"""
    ratio = min(dst_width / src_width, dst_height / src_height)
    new_w = src_width * ratio
    new_h = src_height * ratio
    x_offset = (dst_width - new_w) / 2
    y_offset = (dst_height - new_h) / 2
    return new_w, new_h, x_offset, y_offset


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


def add_image_to_page(page, img_path, y_start):
    """将图片添加到页面的上半或下半区域。竖向图片自动旋转90度。"""
    img = Image.open(img_path)
    src_w, src_h = img.size
    img.close()

    rotated = src_h > src_w
    if rotated:
        src_w, src_h = src_h, src_w

    new_w, new_h, x_off, y_off = fit_rect(src_w, src_h, ITEM_WIDTH, ITEM_HEIGHT)

    # 用临时PDF方式嵌入，兼容性最好
    tmp_pdf = img_to_temp_pdf(img_path)
    try:
        src_doc = fitz.open(tmp_pdf)
        target = fitz.Rect(
            MARGIN + x_off,
            y_start + y_off,
            MARGIN + x_off + new_w,
            y_start + y_off + new_h
        )
        page.show_pdf_page(target, src_doc, 0)
        src_doc.close()
    finally:
        try:
            os.unlink(tmp_pdf)
        except:
            pass


def add_pdf_page_to_page(page, src_doc, src_page_num, y_start):
    """将PDF页面添加到页面的上半或下半区域。竖向页面自动旋转90度。"""
    src_page = src_doc[src_page_num]
    src_w = src_page.rect.width
    src_h = src_page.rect.height

    rotated = src_h > src_w
    if rotated:
        src_w, src_h = src_h, src_w

    new_w, new_h, x_off, y_off = fit_rect(src_w, src_h, ITEM_WIDTH, ITEM_HEIGHT)

    target = fitz.Rect(
        MARGIN + x_off,
        y_start + y_off,
        MARGIN + x_off + new_w,
        y_start + y_off + new_h
    )
    page.show_pdf_page(target, src_doc, src_page_num, rotate=90 if rotated else 0)


def draw_cut_line(page):
    """在页面中间画一条虚线裁剪标记"""
    y = MARGIN + ITEM_HEIGHT + GAP / 2
    p1 = fitz.Point(MARGIN, y)
    p2 = fitz.Point(A4_WIDTH - MARGIN, y)
    page.draw_line(p1, p2, color=(0.5, 0.5, 0.5), width=0.5, dashes="[3 3]")

    # 两端剪刀标记
    scissor = "✂"
    page.insert_text(fitz.Point(MARGIN - 2, y + 3), scissor, fontsize=8, color=(0.5, 0.5, 0.5))


def build_merged_doc(files):
    """将文件列表两两合并，返回 fitz.Document 对象。"""
    doc = fitz.open()
    for i in range(0, len(files), 2):
        page = doc.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        f1 = files[i]
        if is_image(f1):
            add_image_to_page(page, f1, MARGIN)
        elif is_pdf(f1):
            src = fitz.open(f1)
            add_pdf_page_to_page(page, src, 0, MARGIN)
            src.close()

        if i + 1 < len(files):
            f2 = files[i + 1]
            y_bottom = MARGIN + ITEM_HEIGHT + GAP
            if is_image(f2):
                add_image_to_page(page, f2, y_bottom)
            elif is_pdf(f2):
                src = fitz.open(f2)
                add_pdf_page_to_page(page, src, 0, y_bottom)
                src.close()

        # 画裁剪线
        draw_cut_line(page)
    return doc


def merge_two_files(file1, file2, output_path):
    """将两个文件合并到一张A4纸上，保存到 output_path"""
    doc = build_merged_doc([file1, file2])
    doc.save(output_path)
    doc.close()
    return output_path


def render_preview(files, dpi=150):
    """生成预览图，返回 PIL Image 列表（每页一张图）。"""
    from PIL import Image as PILImage
    import io

    doc = build_merged_doc(files)
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = PILImage.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)
    doc.close()
    return images


def print_direct(files, printer_name=None):
    """合并文件并直接打印到打印机。"""
    doc = build_merged_doc(files)
    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    tmp_path = tmp.name
    tmp.close()
    doc.save(tmp_path)
    doc.close()

    try:
        os.startfile(tmp_path, 'print')
    except Exception as e:
        os.unlink(tmp_path)
        raise e

    import threading
    def cleanup():
        import time
        time.sleep(10)
        try:
            os.unlink(tmp_path)
        except:
            pass
    threading.Thread(target=cleanup, daemon=True).start()
    return tmp_path


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
