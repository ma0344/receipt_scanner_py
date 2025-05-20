# -*- coding: utf-8 -*-
import os
import enum
import math
import numpy as np
from typing import List, Tuple, Type, Optional, NamedTuple
import cv2
from cv2 import RotatedRect
from numpy import ndarray as mat
from PySide6.QtGui import QImage, QPixmap


class processMode(enum.Enum):
    s_chanel = 0
    lab_chanel = 1
    gaus_median = 2


class SlidersValue:
    def __init__(self, val1: int, val2: int, val3: int):
        self.val1 = val1
        self.val2 = val2
        self.val3 = val3


class ResultSize(NamedTuple):
    width: float
    height: float


def black_area_to_white(image: mat) -> mat:
    # 2値化処理を行い、黒と白の二値画像にする
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary_image = cv2.threshold(gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 二値画像上で輪郭を抽出する
    contours, _ = cv2.findContours(binary_image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    ret_mat = image.copy()

    # 一定以上の面積を持つ輪郭を特定し、白で塗りつぶす
    area_threshold = 60000  # 一定以上の面積の閾値
    area_threshold_top = 130000
    fill_color = (255, 255, 255)  # 白色

    for contour in contours:
        area = cv2.contourArea(contour)
        if area_threshold < area < area_threshold_top:
            cv2.drawContours(ret_mat, [contour], -1, fill_color, -1)
    plot_img(ret_mat, 'black_area_to_white_img')
    return ret_mat


def convert_to_lab(img: mat) -> mat:
    lab_image = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
    return lab_image


def process_lab_image(img: mat, val1: int) -> mat:
    lab_planes = cv2.split(img)
    _, processed_image = cv2.threshold(lab_planes[0], val1, 255, cv2.THRESH_BINARY)
    # plot_img(processed_image, 'process_lab_img')
    return processed_image


def to_gray(img: mat) -> mat:
    # グレースケールに変換
    grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # plot_img(grayscale, 'grayscale_img')
    return grayscale


def sobel(img: mat) -> mat:
    dx = cv2.Sobel(img, cv2.CV_8U, 1, 0)
    dy = cv2.Sobel(img, cv2.CV_8U, 0, 1)
    sobel = np.sqrt(dx * dx + dy * dy)
    sobel = (sobel * 128).astype('uint8')
    # plot_img(sobel, 'sobel_img')
    return sobel


def change_threshold(image: mat, val1: int, val2: int, sw1: bool) -> mat:
    img = image.copy()
    img = hide_table(img, (0, 0, 0,))
    lab_image = convert_to_lab(img.copy())
    processd_image = process_lab_image(lab_image, val1, val2)
    closed_image = morp_ex_close(processd_image)
    if sw1 == 1:
        draw_rect = True
    else:
        draw_rect = False
    return get_rect_draw_image(closed_image, draw_rect)


def get_pixmap(img: mat) -> QPixmap:
    pixmap = QPixmap.fromImage(QImage(img, img.shape[1], img.shape[0], img.strides[0], QImage.Format_RGB888))
    return pixmap

# from pylsd.lsd import lsd


def convert_to_hsv(img: mat) -> mat:
    hsv_image = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    return hsv_image


def get_s_channel(hsv: mat) -> mat:
    s = hsv[:, :, 1]

    # plot_img(h, 'h_channel_img')
    # plot_img(s, 's_channel_img')
    # plot_img(v, 'v_channel_img')
    return s


def equalize(channel: mat) -> mat:
    equalized_s_channel = cv2.equalizeHist(channel)
    # plot_img(equalized_s_channel, 'equalized_s_channel')
    return equalized_s_channel


def Bilateral(img: mat, iteration=5) -> mat:
    for _ in range(iteration):
        img = cv2.bilateralFilter(img, 20, 80, 50)
    return img


def adjust_exposure_and_black_level(image: mat, black_level: int) -> mat:
    # 露出を調整
    adjusted = image + 0
    adjusted = np.clip(adjusted, 0, 255)  # 値を0から255の範囲に制限

    # 黒レベルを調整
    min_val = np.min(adjusted[adjusted > 0])
    adjusted[adjusted == 0] = black_level
    adjusted = adjusted - min_val + black_level
    adjusted = np.clip(adjusted, 0, 255)  # 再度、値を0から255の範囲に制限
    # plot_img(adjusted, 'adjusted_image')
    return adjusted


def sharp_kernel(k: int):
    kernel = np.array([
        [-k / 9, -k / 9, -k / 9],
        [-k / 9, 1 + 8 * k / 9, -k / 9],
        [-k / 9, -k / 9, -k / 9]
    ])
    return kernel


def apply_2d_filter(img: mat, kernel_value: int = 1):
    # シャープネスの係数
    kernel = sharp_kernel(kernel_value)
    out_image = cv2.filter2D(img, -1, kernel)
    return out_image


def apply_2dfilter(img: mat, kernel: int) -> mat:
    return cv2.filter2D(img, -1, kernel)


def hide_table(image: mat, color: int = 0) -> mat:
    # マスク画像を作成（処理対象の領域は1、無視する領域は0とする）
    mask = np.zeros(image.shape[:2], dtype=np.uint8)  # 白色で初期化
    # 左上の計算欄の領域を黒で塗りつぶす
    cv2.rectangle(mask, (0, 0), (int(image.shape[1] * 0.525), int(image.shape[0] * 0.225)), 255, -1)
    # 最下部のスキャナーのズレ領域を黒で塗りつぶす
    cv2.rectangle(mask, (0, int(image.shape[0] * 0.993)), (image.shape[1], image.shape[0]), 255, -1)
    # 右端のスキャナーのズレ領域を黒で塗りつぶす
    cv2.rectangle(mask, (int(image.shape[1] * 0.995), 0), (image.shape[1], image.shape[0]), 255, -1)
    # マスクを適用して特定の領域を無視する

    # 反転マスクを作成
    inv_mask = cv2.bitwise_not(mask)

    # マスクを適用して隠したい領域以外を保持
    masked_image = cv2.bitwise_and(image, image, mask=inv_mask)

    # 色で塗りつぶす
    if len(image.shape) == 2:  # グレースケール画像
        color_fill = np.full(image.shape, color[0], dtype=np.uint8)
    else:  # カラー画像
        color_fill = np.full(image.shape, color, dtype=np.uint8)
    colored_mask = cv2.bitwise_and(color_fill, color_fill, mask=mask)

    # 画像を結合
    result = cv2.add(masked_image, colored_mask)

    plot_img(result, 'hide_table_img')
    return result


def binarize(img: mat, val1: int) -> mat:
    _, binary_img = cv2.threshold(img, val1, 255, cv2.THRESH_BINARY_INV)
    # binary_img = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 255, 2)
    # plot_img(binary_img, 'binary_img')
    return binary_img


def morphology_open(img: mat, kernel_val: tuple[int, int] = (3, 3), iterations: int = 1) -> mat:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_val)
    morp_open = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel, iterations=iterations)
    return morp_open


def morphology_close(img: mat, kernel_val: tuple[int, int] = (3, 3), iterations: int = 1) -> mat:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_val)
    morp_close = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel, iterations=iterations)
    return morp_close


def morp_ex_open(img: mat, iteration: int = 1) -> mat:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    morp_ex_open_image = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel, iterations=iteration)
    return morp_ex_open_image


def morp_ex_close(img: mat, iteration: int = 1) -> mat:
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    morp_ex_close_image = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel, iterations=iteration)
    return morp_ex_close_image


def scaleAbs(img: mat, alpha: float, beta: float) -> mat:
    return cv2.convertScaleAbs(img, alpha=alpha, beta=beta)


def cany_edge(img: mat) -> mat:
    cany = cv2.Canny(img, 50, 1000)
    plot_img(cany, 'cany_img')
    return cany


def apply_gamma_correction(img: mat, gamma: float = 1.0) -> mat:
    # ガンマ補正
    inv_gamma = 1 / gamma
    lut = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(img, lut)


def unsharp(image):
    v1 = 10
    v2 = 100
    v3 = 30
    t = v1
    v = (v2 / 220) * 2
    k = v3 * 2 + 1
    blurred = cv2.GaussianBlur(image, (k, k), t)

    # 量を調整（ここでは500%）
    amount = v

    # 元の画像との差分を計算し、元の画像に加算
    unsharp_image = cv2.addWeighted(image, 1 + amount, blurred, -amount, t)
    return unsharp_image


def get_resized_image(img: mat) -> mat:
    return cv2.resize(img, (window_width, window_height))


def taple_to_rotatedrect(taple: Tuple[Tuple[float, float], Tuple[float, float], float]) -> RotatedRect:
    return RotatedRect(taple[0], taple[1], taple[2])


def rotatedrect_to_taple(rect: RotatedRect) -> Tuple[Tuple[float, float], Tuple[float, float], float]:
    if not hasattr(rect, "center"):
        return ((rect[0][0], rect[0][1]), (rect[1][0], rect[1][1]), rect[2])
    return (rect.center, rect.size, rect.angle)


def mat_to_pixmap(mat: mat) -> QPixmap:
    try:
        # matをQImageに変換
        rgbMat = cv2.cvtColor(mat, cv2.COLOR_BGR2RGB)
        # QImageをQPixmapに変換
        height, width, channel = rgbMat.shape
        bytesPerLine = 3 * width
        qImg = QImage(rgbMat.data, width, height, bytesPerLine, QImage.Format_RGB888)
        qPixmap = QPixmap.fromImage(qImg)
        return qPixmap
    except Exception as e:
        print(e)
        return None


def pixmap_to_mat(pixmap: QPixmap) -> np.ndarray:
    qimage = pixmap.toImage()
    w, h = qimage.size().width(), qimage.size().height()

    # PySide6でのQImageのフォーマットチェック
    dtype = np.uint8
    channels = 4
    # 他のフォーマットに対する処理を省略

    # bytesPerLineを使用して行ごとのバイト数を取得
    # bytes_per_line = qimage.bytesPerLine()
    # memoryviewからバイト列を取得してnumpy配列に変換
    arr = np.frombuffer(qimage.bits().tobytes(), dtype=dtype).reshape((h, w, channels))
    return arr


def pixmap_to_mat_(pixmap: QPixmap) -> np.ndarray:
    qimage = pixmap.toImage()
    w, h, d = qimage.size().width(), qimage.size().height(), qimage.depth()
    bytes_ = qimage.bits().asstring(w * h * d // 8)
    arr = np.frombuffer(bytes_, dtype=np.uint8).reshape((h, w, d // 8))
    return arr


def get_image(image_path: str, sliders_value: SlidersValue, return_proc_image: bool = False, mode: processMode = processMode.s_chanel) -> mat:
    image = imread(image_path)
    val1, val2, val3 = sliders_value.val1, sliders_value.val2, sliders_value.val3
    match mode:
        case processMode.s_chanel:
            mat = s_channel_equalize(image, val1, val2, val3)
            if return_proc_image:
                return mat
            rotated_rects = get_rotated_rects(mat, 10000, 350, 310)
            return get_rect_draw_image(image, rotated_rects)
        case processMode.lab_chanel:
            return change_threshold(image, val1, val2, return_proc_image)
        case processMode.lsd:
            return (image)
        case processMode.none:
            return image
        case _:
            return image


def get_rect_draw_image(img: mat, rotated_rects: List[RotatedRect], flag=False) -> mat:
    res_image = img.copy()
    # flag = info.function != 'receiptListSelection_changed' and info.function != 'sheetImage_mouse_moved'

    for rect in rotated_rects:
        box = cv2.boxPoints(rotatedrect_to_taple(rect))
        box = np.int0(box)
        cv2.drawContours(res_image, [box], 0, (0, 0, 255), 2)

        if flag:
            # 角度を文字列として描画
            text = f"{rect.angle:.2f} degrees"
            cv2.putText(res_image, text, (int(rect.center[0]), int(rect.center[1])), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 255), 4, cv2.LINE_AA)
    return res_image


def crop_image(mat_image: mat, rect: RotatedRect) -> mat:
    center, size, angle = rect.center, rect.size, rect.angle

    # 角度が45度より大きい画像は縦横を入れ替えて90度マイナス
    if abs(angle) > 45:
        size = (size[1], size[0])
        angle -= 90

    # 画像の回転
    rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated_image = cv2.warpAffine(mat_image, rot_matrix, (mat_image.shape[1], mat_image.shape[0]))

    # 回転後の矩形の左上座標を計算
    x, y = int(center[0] - size[0] / 2), int(center[1] - size[1] / 2)

    # 矩形のクロップ
    cropped_image = rotated_image[y:y + int(size[1]), x:x + int(size[0])]
    return cropped_image


def find_contours(img: mat) -> List[mat]:
    contours, _ = cv2.findContours(img.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_L1)
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 100]
    return contours


def narrow_down_contours(image: mat, contours: mat, size: float, min_height: float, min_width: float) -> List[RotatedRect]:
    """輪郭を条件で絞り込んで矩形のみにする
    """
    rotated_rectangles = []
    for contour in contours:
        if cv2.contourArea(contour) >= size:
            rotated_rect: RotatedRect = taple_to_rotatedrect(cv2.minAreaRect(contour))
            # adjusted_rect = adjust_rotated_rectangle(rotated_rect)
            rect_size = get_rect_size(rotated_rect)
            if rect_size.width >= min_width and rect_size.height >= min_height:
                if rect_size.height < image.shape[0] * 0.9:
                    rotated_rectangles.append(rotated_rect)
    return rotated_rectangles


def get_rotated_rects(image: mat, size: int, min_height: int, min_width: int) -> List[RotatedRect]:
    if len(image.shape) > 2:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    adjusted_rotated_rectangles = narrow_down_contours(image, contours, size, min_height, min_width)

    return adjusted_rotated_rectangles


def get_rect_size(rect: RotatedRect) -> ResultSize:
    box = cv2.boxPoints(rect)
    if 0 <= rect.angle < 45:
        x1, y1 = box[0]
        x2, y2 = box[1]
        x3, y3 = box[1]
        x4, y4 = box[2]
    else:
        x1, y1 = box[1]
        x2, y2 = box[2]
        x3, y3 = box[2]
        x4, y4 = box[3]
    height = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    width = math.sqrt((x3 - x4)**2 + (y3 - y4)**2)
    return ResultSize(width, height)


def get_rotated_rect_points(center: Tuple[float, float], size: Tuple[float, float], angle: float) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
    # 中心、サイズ、角度から回転した矩形の4つの角の座標を計算
    rect = (center, size, angle)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    return box


def get_box_points(rect_: cv2.RotatedRect) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
    # 中心、サイズ、角度から回転した矩形の4つの角の座標を計算
    # rect = ((rect_['Center']['X'], rect_['Center']['Y']), (rect_['Size']['Width'], rect_['Size']['Height']), rect_['Angle'])
    rect = (rect_.center, rect_.size, rect_.angle)
    box = cv2.boxPoints(rect)
    box = np.int0(box)
    return box


def adjust_rotated_rectangle(rotated_rect: cv2.RotatedRect) -> RotatedRect:
    """
    RotatedRectの点を適切に並べ替えて角度を調整する関数。
    rotated_rect: 元のRotatedRect (中心点, (幅, 高さ), 角度)
    戻り値: 修正されたRotatedRect
    """
    center, size, angle = rotated_rect
    width, height = size

    # 角度に基づいて幅と高さを調整
    if 0 <= angle < 45:
        # 角度が0度以上45度未満の場合、box[0]からbox[1]は高さ
        width, height = size[0], size[1]
    else:
        # 角度が45度以上の場合、box[0]からbox[1]は幅
        width, height = size[1], size[0]
        angle = angle - 90

    return (center, (width, height), angle)


def get_crop_rects(source, sliders_value: SlidersValue, mode: processMode = processMode.s_chanel) -> List[RotatedRect]:
    if isinstance(source, str):
        image = imread(source)
    elif isinstance(source, np.ndarray):
        image = source

    val1, val2, val3 = sliders_value.val1, sliders_value.val2, sliders_value.val3
    match mode:

        case processMode.s_chanel:
            mat = s_channel_equalize(image, val1, val2, val3)
            rects = get_rotated_rects(mat, 10000, 350, 310)
            rotatedrects: List[RotatedRect] = []
            for rect in rects:
                rotatedrects.append(rect)
            return rotatedrects

        case processMode.lab_chanel:
            return change_threshold(image, val1, val2)

        case _:
            return image


def s_channel_equalize_(image: mat, va1: int, va2: int) -> mat:
    img = image.copy()
    hsv_image = convert_to_hsv(img)
    s_channel = get_s_channel(hsv_image)
    equolized_image = equalize(s_channel)
    bilateral_image = Bilateral(equolized_image, 1)
    adjusted_image = adjust_exposure_and_black_level(bilateral_image, black_level=va2)
    hide_table_img = hide_table(image=adjusted_image, color=(255, 255, 255))
    bin_image = binarize(hide_table_img, va1)
    morp_ex_open_img = morp_ex_open(bin_image, 3)
    morp_ex_close_img = morp_ex_close(morp_ex_open_img, 3)
    return morp_ex_close_img


def s_channel_equalize(image: mat, va1: int, va2: int, va3: int) -> mat:
    img = image.copy()
    hsv_image = convert_to_hsv(img)
    s_channel = get_s_channel(hsv_image)
    scaleAbs_image = scaleAbs(s_channel, va1, va2)
    bin_image = binarize(scaleAbs_image, va3)
    morp_ex_open_img = morp_ex_open(bin_image, 2)
    morp_ex_close_img = morp_ex_close(morp_ex_open_img, 2)
    if __name__ == '__main__':
        cv2.imshow("scaleABS", get_resized_image(scaleAbs_image))
        cv2.imshow("binary", get_resized_image(bin_image))
        cv2.imshow("morpOpen", get_resized_image(morp_ex_open_img))
        cv2.imshow("morpClose", get_resized_image(morp_ex_close_img))
    return morp_ex_close_img


def process_image(img):
    # 1. HSVチャンネルに分解
    v1 = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 2]
    # 2. V1を複製してV2を作成
    # 3. をしきい値235で2値化し、階調を反転してv2を作成
    _, v2 = cv2.threshold(v1, 235, 255, cv2.THRESH_BINARY_INV)
    # 4. マスクをカラー画像に適用
    masked_img = cv2.bitwise_and(img, img, mask=v2)

    # 5. マスクでカバーされていない部分を白で塗りつぶす
    white_background = np.full_like(img, (255, 255, 255), dtype=np.uint8)
    final_image = cv2.bitwise_or(masked_img, white_background, mask=cv2.bitwise_not(v2))

    return final_image


def apply_mask_image(image):
    # 1. HSVチャンネルに分解
    v1 = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)[:, :, 2]
    # 2. V1をしきい値235で2値化し、階調を反転してV2を作成
    _, mask = cv2.threshold(v1, 235, 255, cv2.THRESH_BINARY)
    mask = adjust_mask_to_image(image, mask)
    # 4. マスクをカラー画像に適用
    maskd_img = cv2.bitwise_or(image, mask)

    return maskd_img


def adjust_mask_to_image(image, mask):
    # 元の画像のチャンネル数に基づいてマスクを調整
    num_channels = image.shape[2]
    if num_channels == 3:  # RGBまたはBGR画像の場合
        mask = cv2.merge([mask, mask, mask])  # マスクを3チャンネルに拡張
    elif num_channels == 4:  # RGBA画像の場合
        alpha_channel = np.ones(mask.shape, dtype=mask.dtype) * 255
        mask = cv2.merge([mask, mask, mask, alpha_channel])  # マスクを4チャンネルに拡張

    return mask


def imreadj(path: str) -> mat:
    tmp_dir = os.getcwd()
    # 1. 対象ファイルがあるディレクトリに移動
    if len(path.split("/")) > 1:
        file_dir = "/".join(path.split("/")[:-1])
        os.chdir(file_dir)
    # 2. 対象ファイルの名前を変更
    tmp_name = "tmp_name"
    os.rename(path.split("/")[-1], tmp_name)
    # 3. 対象ファイルを読み取る
    img = cv2.imread(tmp_name)
    # 4. 対象ファイルの名前を戻す
    os.rename(tmp_name, path.split("/")[-1])
    # カレントディレクトリをもとに戻す
    os.chdir(tmp_dir)
    return img


def imread(filename: str, flags: int = cv2.IMREAD_COLOR, dtype: Type[np.generic] = np.uint8) -> Optional[mat]:
    try:
        n = np.fromfile(filename, dtype)
        img = cv2.imdecode(n, flags)
        return img
    except Exception as e:
        print(e)
        return None


def imwrite(filename: str, img: mat, params: Optional[List[int]] = None) -> bool:

    try:
        ext = os.path.splitext(filename)[1]
        result, n = cv2.imencode(ext, img, params)

        if result:
            with open(filename, mode='w+b') as f:
                n.tofile(f)
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False


def plot_img(img: mat, file_name: str) -> mat:
    """画像の書き出し
    """
    # plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    # cv2.imshow("Image", resized_image)
    cv2.imwrite('./{}.png'.format(file_name), img)


def on_trackbar_change(pos):
    global v1, v2, v3, s1
    v1 = cv2.getTrackbarPos("val1", "Image")
    v2 = cv2.getTrackbarPos("val2", "Image")
    v3 = cv2.getTrackbarPos("val3", "Image")
    s1 = cv2.getTrackbarPos("swich", "Image")
    s_channel_equalize(v1, v2, v3, s1)


def show_mat_in_imshow(name: str, imarge: mat):
    cv2.namedWindow(name, cv2.WINDOW_NORMAL)
    cv2.imshow(name, imarge)
    cv2.imwrite(name + ".png", imarge)
#    cv2.waitKey(0)
#    cv2.destroyAllWindows()


if __name__ == '__main__':

    # 画像の読み込み
    filename = 'C:\\Users\\ma\\desktop\\001.jpg'
    # filename = 'C:\\Users\\ma\\desktop\\20231203_1.jpg'
    image = cv2.imread(filename)
    cv2.namedWindow("Image")

    # ウィンドウサイズの定義
    window_width = int((image.shape[1] * 800) / image.shape[0])
    window_height = 800

    # 画像をウィンドウサイズに合わせてリサイズ
    # トラックバーの作成
    v1 = 0  # 27
    v2 = 250
    v3 = 125
    s1 = 0
    cv2.createTrackbar("val1", "Image", v1, 255, on_trackbar_change)
    cv2.createTrackbar("val2", "Image", v2, 255, on_trackbar_change)
    cv2.createTrackbar("val3", "Image", v3, 255, on_trackbar_change)
    # cv2.createTrackbar("swich", "Image", s1, 1, on_trackbar_change)

    # ウィンドウの作成
    unsharp_image = unsharp(image, 5, v1, v2, v3)

    if s1 == 1:
        draw_rect = True
    else:
        draw_rect = False

    cv2.imshow('Image', unsharp_image)

    # 初期表示
    # change_threshold(v1, v2)

    # ウィンドウが閉じるまで待機
    cv2.waitKey(0)
    cv2.destroyAllWindows()
