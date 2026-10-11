import os
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import Polygon
from shapely.ops import transform
from pyproj import CRS, Transformer


def calculate_irregular_volume(tif_path, twd97_coords, custom_base_elevation):
    print("🚀 正在執行台灣 TWD97 座標至世界 UTM 51N 坐標系的自動幾何轉換...")

    # 1. 定義座標轉換器 (從台灣二度分帶 EPSG:3826 轉到您的地圖內建 EPSG:32651)
    crs_twd97 = CRS.from_epsg(3826)
    crs_utm51n = CRS.from_epsg(32651)
    transformer = Transformer.from_crs(
        crs_twd97, crs_utm51n, always_xy=True
    )

    # 2. 轉換多邊形頂點
    twd97_poly = Polygon(twd97_coords)
    utm51n_poly = transform(transformer.transform, twd97_poly)
    shapes = [utm51n_poly]

    print("📡 座標咬合成功！正在切削不規則工區邊界並載入 3D 地形數據...")

    # 3. 讀取與剪裁地表模型
    with rasterio.open(tif_path) as src:
        pixel_width, pixel_height = src.res
        pixel_area = abs(pixel_width * pixel_height)

        try:
            out_image, _ = mask(src, shapes, crop=True)
        except ValueError as e:
            print(f"❌ 剪裁失敗: {e}")
            print(
                "💡 提示：請確認您的點位確實包覆在無人機拍攝的中央範圍內。"
            )
            return

        elevation_matrix = out_image
        nodata_value = src.nodata

    valid_mask = elevation_matrix != nodata_value
    site_elevations = elevation_matrix[valid_mask]

    print(f"📊 區域內有效觀測網格數: {len(site_elevations)} 個像素")
    print(f"📐 單一網格解析度面積: {pixel_area:.4f} 平方公尺")

    # 4. 核心土方計算 (以 A1 的實體觀測高程 17.174 為水平切削基準)
    cut_depths = site_elevations - custom_base_elevation
    cut_depths[cut_depths < 0] = 0
    total_cut_volume = np.sum(cut_depths) * pixel_area

    fill_depths = custom_base_elevation - site_elevations
    fill_depths[fill_depths < 0] = 0
    total_fill_volume = np.sum(fill_depths) * pixel_area

    print("\n================ 工地土方量計算報告 ================")
    print(f"地圖內建坐標系統 : EPSG:32651 (UTM Zone 51N)")
    print(f"設定自訂基準高程 : {custom_base_elevation:.3f} 公尺 (A1點高度)")
    print(f"不規則圈選總面積 : {(len(site_elevations) * pixel_area):.2f} 平方公尺")
    print(f"🔥 總挖方體積 (Cut Volume) : {total_cut_volume:.3f} 立方公尺 (m³)")
    print(f"🍀 總填方體估算 (Fill Volume): {total_fill_volume:.3f} 立方公尺 (m³)")
    print("====================================================")


if __name__ == "__main__":
    input_tif = "dsm.tif"

    # 🚀 直接填入您最熟悉的平面圖實體 TWD97 座標，順時針閉合排列
    工區不規則邊界 = [
        (307334.994, 2764390.966),  # Q2225 (西北側)
        (307337.638, 2764375.567),  # A1 (西北側)
        (307399.777, 2764382.141),  # A2 (東北側)
        (307389.316, 2764369.210),  # K6 (偏東側場內點)
        (307334.994, 2764390.966),  # 閉合起點
    ]

    您的自訂高度 = 17.174  # 帶入 A1 實測高程作為基準面

    if not os.path.exists(input_tif):
        print(f"❌ 錯誤：找不到 [{input_tif}] 檔案！")
    else:
        calculate_irregular_volume(
            input_tif, 工區不規則邊界, 您的自訂高度
        )
