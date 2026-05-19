# 发票合并打印工具

> 纯 AI 编写的发票打印工具

将 2 张图片或 2 份 PDF 发票合并到一张 A4 纸上打印，节省纸张。

## 功能

- A4 竖放，上下各放一张横向发票
- 竖向发票自动旋转 90 度变为横向
- 支持 JPG / PNG / BMP / TIFF / PDF
- 文件拖放添加
- 打印预览，支持翻页、缩放
- 中间裁剪线标记
- 直接打印或保存 PDF
- 批量处理多个文件
- 一键打包成 exe

## 使用

### 直接运行

```bash
pip install -r requirements.txt
python main.py
```

### 打包 exe

```bash
build.bat
```

输出：`dist/InvoiceTool.exe`

## 界面

拖入文件 → 预览 → 打印，三步完成。

## 许可

MIT
