import os
import shutil

# 使用原始字符串解决路径转义问题
rootpath = r'D:\Softwares\Epic Games\UE_5.5\Saved\RenderOutput'
path = r'D:\Softwares\Epic Games\UE_5.5\Saved\RenderOutput\camera_1_tmp'
items_per_folder = 150

# 获取目录下所有的 png 文件并排序，确保逻辑正确
all_files = sorted([f for f in os.listdir(path) if f.endswith('.png')])
all_files = [all_files[0]] + all_files[-1:] + all_files[1:-1] 
print(all_files)

total_files = len(all_files)

# 计算需要多少个文件夹
# 使用整除计算文件夹数量
num_folders = total_files // items_per_folder

print(f"检测到 {total_files} 张图片，将分配到 {num_folders} 个文件夹中。")

for i in range(num_folders):
    # 1. 创建文件夹 cam_00, cam_01...
    folder_name = f"cam_{i:02d}"
    folder_path = os.path.join(path, folder_name)
    
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # 2. 移动该组的 150 张图片
    for j in range(items_per_folder):
        # 计算当前图片在总列表中的索引
        file_idx = i * items_per_folder + j
        
        if file_idx < total_files:
            src_name = all_files[file_idx]
            src_path = os.path.join(path, src_name)
            
            # 目标文件名建议保持原样，或者按你的需求改为 0.png, 1.png...
            # 这里演示改为 0.png, 1.png 格式
            dst_name = f"{j:04d}.png" 
            dst_path = os.path.join(folder_path, dst_name)
            
            shutil.move(src_path, dst_path)

print("处理完成！")

shutil.move(os.path.join(rootpath, 'cameras_parameters.json'), os.path.join(path, 'cameras_parameters.json'))