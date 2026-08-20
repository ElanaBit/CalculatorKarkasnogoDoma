# -*- coding: utf-8 -*-
"""Генерирует иконку приложения в .ico и .png."""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = size / 256

    def P(x, y):
        return (x * m, y * m)

    # фон: скруглённый прямоугольник с градиентом
    r = int(56 * m)
    x0, y0 = P(8, 8)
    x1, y1 = P(248, 248)
    top = (24, 36, 62)
    bot = (11, 16, 30)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=(18, 26, 44, 255))
    # мягкий градиент
    for y in range(int(y0), int(y1)):
        t = (y - y0) / (y1 - y0)
        col = lerp(top, bot, t)
        d.line([(x0 + r, y), (x1 - r, y)], fill=col + (255,))
    d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=(70, 90, 130, 120), width=2)

    # дом: крыша (градиент янтарный)
    roof = lerp((255, 176, 46), (255, 122, 26), 0.5)
    d.polygon([P(38, 128), P(128, 62), P(218, 128)], fill=roof)
    # конёк крыши
    d.line([P(38, 128), P(128, 62), P(218, 128)], fill=(255, 210, 120), width=int(3 * m))
    # корпус дома
    d.rounded_rectangle([P(62, 128), P(194, 200)], radius=int(8 * m), fill=(238, 244, 252, 255))
    # дверь
    d.rounded_rectangle([P(112, 156), P(144, 200)], radius=int(6 * m), fill=roof)
    # окно с «расчётом»
    d.rounded_rectangle([P(78, 142), P(104, 158)], radius=int(4 * m), fill=(96, 165, 250, 255))
    d.rounded_rectangle([P(152, 142), P(178, 158)], radius=int(4 * m), fill=(96, 165, 250, 255))
    return img


def main():
    sizes = [256, 128, 64, 48, 32, 16]
    imgs = [draw_icon(s) for s in sizes]
    out_ico = os.path.join(ROOT, 'app', 'app.ico')
    imgs[0].save(out_ico, format='ICO', sizes=[(s, s) for s in sizes[1:]])
    # PNG-превью
    draw_icon(256).save(os.path.join(ROOT, '_tools', 'app_preview.png'))
    print('ICO saved:', out_ico)


if __name__ == '__main__':
    main()
