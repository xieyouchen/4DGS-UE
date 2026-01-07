import shutil
from pathlib import Path

name = 'camera20'
base_dir = Path(f'D:/Softwares/Epic Games/UE_5.5/Saved/RenderOutput/{name}/')  # 当前目录
transforms_path = base_dir / f"{name}"

def mv_png_to_tmp():

    # 1. 定义初始目录和目标目录
    target_dir = base_dir / f"{name}" / 'images'

    # 2. 如果 tmp 文件夹不存在，则创建它
    target_dir.mkdir(parents=True, exist_ok=True)

    

    # 3. 遍历符合 cam_xx 格式的文件夹
    # cam_?? 匹配 cam_ 后跟两个字符的文件夹
    for cam_folder in base_dir.glob('cam_??'):
        if cam_folder.is_dir():
            # 获取父目录编号（例如从 'cam_00' 提取 '00'）
            folder_suffix = cam_folder.name.split('_')[-1]
            
            # 定义源文件路径和目标文件路径
            source_file = cam_folder / '0149.png'
            target_file = target_dir / f"{folder_suffix}.png"
            
            # 4. 执行复制操作
            if source_file.exists():
                shutil.copy2(source_file, target_file)
                print(f"已复制: {source_file} -> {target_file}")
            else:
                print(f"跳过: {cam_folder} 中未找到 0149.png")

    print("mv_png_to_tmp() 任务完成！")

def convert_cameraJson_to_transform():
    import json
    import math
    import os

    # 1. 加载你的原始数据 (假设存放在 data 变量中)
    path = os.path.join(base_dir, 'camera_parameters.json')
    with open(path, 'r') as f:
        original_data = json.load(f)

    # 这里用你提供的原始数据作为示例
    # original_data = [
    #     # ... (此处省略你提供的 10 个 json 块) ...
    # ]

    def convert_nerf_json(data_list):
        if not data_list:
            return {}

        # 提取共有参数（以第一个相机为例）
        first_cam = data_list[0]
        w = float(first_cam["camera_hw"][1])
        h = float(first_cam["camera_hw"][0])
        angle_x = float(first_cam["camera_angle_x"])
        
        # 计算焦距 fl_x (NeRF 常用格式)
        fl_x = w / (2.0 * math.tan(angle_x / 2.0))
        fl_y = fl_x  # 假设像素是正方形
        
        # 构造新的 JSON 结构
        new_json = {
            "camera_angle_x": angle_x,
            "camera_angle_y": angle_x, # 假设相同
            "fl_x": fl_x,
            "fl_y": fl_y,
            "cx": w / 2.0,
            "cy": h / 2.0,
            "w": w,
            "h": h,
            "aabb_scale": 4,
            "frames": []
        }

        # 遍历每个原始 json 块，构造 frames
        for i, item in enumerate(data_list):
            # 根据你的要求，文件名对应关系是 i.png
            # 补全两位数文件名，如 00.png, 01.png
            file_name = f"{i:02d}.png"
            
            frame = {
                "file_path": f"images/{file_name}",
                "transform_matrix": item["transform_matrix"]
            }
            new_json["frames"].append(frame)
        
        return new_json

    # 执行转换
    result_json = convert_nerf_json(original_data)

    # 2. 保存为新的 json 文件
    with open(os.path.join(transforms_path, 'transforms.json'), 'w', encoding='utf-8') as f:
        json.dump(result_json, f, indent=4)

    print("convert_cameraJson_to_transform() 转换完成，已生成 transforms.json")


mv_png_to_tmp()
convert_cameraJson_to_transform()
