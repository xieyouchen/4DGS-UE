import math
import unreal
import os, json, sys
import shutil
import random

SCALE = 0.01
random.seed(42)

class MRQ:
    def __init__(self, camera_actor: unreal.Actor, seq_asset_path: str, output_path: str, n_samples: int = 4, res_X: int = 800, res_Y: int = 800):
        self.initial_location = camera_actor.get_actor_location()
        self.initial_rotation = camera_actor.get_actor_rotation()
        self.radius = self.initial_location.length()
        self.seq_asset_path = seq_asset_path
        self.n_samples = n_samples

        self.output_path = output_path  
        self.output_dir = f"{self.output_path}/camera{n_samples}"
        os.makedirs(self.output_dir, exist_ok=True)   

        self.res_X = res_X
        self.res_Y = res_Y
        self.camera_actor = camera_actor


        self.track = self.find_track("CineCameraActor")

        if self.radius == 0.0:
            raise ValueError("Camera is at origin; cannot orbit.")

    def find_track(self, camera_label: str):
        seq_asset_path = self.seq_asset_path
        # 1. 加载 LevelSequence
        level_seq = unreal.load_asset(seq_asset_path)
        if not level_seq:
            raise RuntimeError(f"Cannot load sequence: {seq_asset_path}")

        movie_scene = level_seq.get_movie_scene()

        # 2. 找到 Camera Binding
        camera_binding = None
        for binding in level_seq.get_bindings():
            if binding.get_name() == camera_label:
                camera_binding = binding
                break

        if not camera_binding:
            raise RuntimeError(f"Camera binding '{camera_label}' not found")
        
        # 3. 找 Transform Track
        transform_track = None
        for track in camera_binding.get_tracks():
            if isinstance(track, unreal.MovieScene3DTransformTrack):
                transform_track = track
                break

        if not transform_track:
            transform_track = camera_binding.add_track(unreal.MovieScene3DTransformTrack)
        return transform_track

    def remove_all_sections(self):
        transform_track = self.track
        sections = transform_track.get_sections()
        for section in sections:
            transform_track.remove_section(section)


    @staticmethod
    def _quat_from_axis_angle(axis: unreal.Vector, angle: float) -> unreal.Quat:
        half_a = angle * 0.5
        sin_half = math.sin(half_a)
        cos_half = math.cos(half_a)
        return unreal.Quat(
            axis.x * sin_half,
            axis.y * sin_half,
            axis.z * sin_half,
            cos_half
        )

    def _fibonacci_sphere(self, n_samples: int):
        points = []
        phi = math.pi * (3.0 - math.sqrt(5.0))
        for i in range(n_samples):
            y = 1.0 - (i / (n_samples - 1)) * 2.0 if n_samples > 1 else 0.0
            r = math.sqrt(max(0.0, 1.0 - y * y))
            theta = phi * i
            x = math.cos(theta) * r
            z = math.sin(theta) * r
            points.append(unreal.Vector(x, y, z))
        return points

    def _align_first_point_to_initial_dir(self, points):
        first = points[0].normal()
        start_dir = self.initial_location / self.radius
        dot = first.dot(start_dir)

        if abs(dot - 1.0) < 1e-6:
            quat = unreal.Quat.identity()
        elif abs(dot + 1.0) < 1e-6:
            axis = unreal.Vector(1, 0, 0)
            if abs(first.x) > 0.9:
                axis = unreal.Vector(0, 1, 0)
            axis = first.cross(axis).normal()
            quat = self._quat_from_axis_angle(axis, math.pi)
        else:
            axis = first.cross(start_dir).normal()
            angle = math.acos(max(-1.0, min(1.0, dot)))
            quat = self._quat_from_axis_angle(axis, angle)

        return [quat.rotate_vector(p) for p in points]

    def get_orbit_positions(self, n_samples: int, zooming_radius: float = 1.0):
        unit = self._fibonacci_sphere(n_samples)
        aligned = self._align_first_point_to_initial_dir(unit)
        unit = [p * self.radius * zooming_radius for p in aligned]
        return unit

    def reset_camera(self):
        self.set_sequencer_camera_transform(
            location=self.initial_location,
            rotation=self.initial_rotation,
            start_frame = 0,
            duration_frames = 1
        )


    def set_sequencer_camera_transform(
        self,
        location: unreal.Vector,
        rotation: unreal.Rotator,
        start_frame: int = 0,
        duration_frames: int = 150
    ):  
        transform_track = self.track
        # 4. 获取 / 创建 Section
        # sections = transform_track.get_sections()
        # if sections:
        #     print(f"Sections found: {len(sections)}")
        #     section = sections[0]
        #     print(f"Section found: {section.get_name()}")
        # else:
        #     section = transform_track.add_section()
        #     print(f"Section created: {section.get_name()}")
        section = transform_track.add_section()

        # 5. 获取 Channel
        channels = section.get_all_channels()

        tx, ty, tz = channels[0:3]
        rx, ry, rz = channels[3:6]

        # 6. 写入关键帧
        frame_start = start_frame
        frame_end = start_frame + duration_frames - 1
        # section.set_range(unreal.FrameNumber(frame_start), unreal.FrameNumber(frame_end))
        section.set_range(frame_start, frame_end)


        for f in range(frame_start, frame_end + 1):
            frame_number = unreal.FrameNumber(f)
            tx.add_key(frame_number, location.x)
            ty.add_key(frame_number, location.y)
            tz.add_key(frame_number, location.z)

            rx.add_key(frame_number, rotation.roll)
            ry.add_key(frame_number, rotation.pitch)
            rz.add_key(frame_number, rotation.yaw)

        unreal.log(f"[Sequencer] Set camera transform frames {frame_start}~{frame_end}")

    def render_to_png_sequence(self, seq_path: str, output_dir: str):
        capture = unreal.AutomatedLevelSequenceCapture()
        capture.level_sequence_asset = unreal.SoftObjectPath(seq_path)
        capture.settings.output_directory = unreal.DirectoryPath(output_dir)
        capture.settings.output_format = "{frame}"
        capture.settings.zero_pad_frame_numbers = 5
        capture.settings.use_custom_frame_rate = True
        capture.settings.custom_frame_rate = unreal.FrameRate(30, 1)
        capture.settings.resolution.res_x = self.res_X
        capture.settings.resolution.res_y = self.res_Y

        # 设置为 PNG 图像序列
        capture.set_image_capture_protocol_type(
            unreal.load_class(None, "/Script/MovieSceneCapture.ImageSequenceProtocol_PNG")
        )
        capture.get_image_capture_protocol().compression_quality = 100

        # 开始渲染
        unreal.SequencerTools.render_movie(capture, unreal.OnRenderMovieStopped())

    def transofrm_rotator(self, rotation: unreal.Rotator):
        new_rotation = rotation.copy()
        new_rotation.roll -= 90
        new_rotation.pitch = rotation.yaw
        new_rotation.yaw = 0
        return new_rotation
    
    

    def save_camera_parameters(self, transforms, output_filename="camera_parameters.json", pattern="customed"):
        import json
        import os
        import math
        import unreal

        camera_data_list = []
        # 获取相机内参 (假设所有帧一致)
        camera_component = self.camera_actor.get_cine_camera_component()
        fov_deg = camera_component.field_of_view
        fov_rad = math.radians(fov_deg)

        for idx, (pos, rotation) in enumerate(transforms):
            if(idx == 0):
                continue
            
            idx = idx - 1
            scale = 0.01  # cm -> m

            if pattern == "csdn":
                # 1. 获取 UE 世界坐标系下的基向量 (World Space Vectors)
                # UE: Forward(X), Right(Y), Up(Z)
                new_rotation = self.transofrm_rotator(rotation)
                fwd = new_rotation.get_forward_vector() # UE 中的前 (X)
                right = new_rotation.get_right_vector() # UE 中的右 (Y)
                up = new_rotation.get_up_vector()       # UE 中的上 (Z)
                
                # 2. 定义相机在 NeRF 坐标系下的方向向量 (Camera-to-World 矩阵的列)
                # 我们需要：
                # 列1: 相机的“右”在 NeRF 世界里的坐标
                # 列2: 相机的“下”在 NeRF 世界里的坐标
                # 列3: 相机的“前”在 NeRF 世界里的坐标
                matrix_list = [
                    [fwd.x, right.x, up.x,    pos.x * scale], # Row for NeRF X
                    [fwd.y, right.y, up.y,    pos.z * scale], # Row for NeRF Y
                    [fwd.z, right.z, up.z,    pos.y * scale], # Row for NeRF Z
                    [0.0,      0.0,   0.0,   1.0]           # Row for W
                ]

            elif pattern == "customed_wrong":
                new_rotation = rotation
                fwd = new_rotation.get_forward_vector() # UE 中的前 (X)
                right = new_rotation.get_right_vector() # UE 中的右 (Y)
                up = new_rotation.get_up_vector()       # UE 中的上 (Z)
                matrix_list = [
                    [right.x, up.x, -fwd.x,   pos.y * scale], # Row for NeRF X
                    [right.y, up.y, -fwd.y,   pos.z * scale], # Row for NeRF Y
                    [right.z, up.z, -fwd.z,   -pos.x * scale], # Row for NeRF Z
                    [0.0,      0.0,   0.0,   1.0]           # Row for W
                ]

            elif pattern == "customed":
                new_rotation = rotation
                fwd = new_rotation.get_forward_vector() # UE 中的前 (X)
                right = new_rotation.get_right_vector() # UE 中的右 (Y)
                up = new_rotation.get_up_vector()       # UE 中的上 (Z)
                matrix_list = [
                    [right.x, up.x, -fwd.x, pos.x * scale], # Row for NeRF X
                    [right.y, up.y, -fwd.y, pos.y * scale], # Row for NeRF Y
                    [right.z, up.z, -fwd.z, pos.z * scale], # Row for NeRF Z
                    [0.0,      0.0,   0.0, 1.0]           # Row for W
                ]
                unreal.log(f"matrix_list: {pattern}")

            elif pattern == "nerf":
                new_rotation = rotation
                fwd = new_rotation.get_forward_vector() # UE 中的前 (X)
                right = new_rotation.get_right_vector() # UE 中的右 (Y)
                up = new_rotation.get_up_vector()       # UE 中的上 (Z)
                matrix_list = [
                    [right.x, -up.x, fwd.x,   pos.x * scale], # Row for NeRF X
                    [right.y, -up.y, fwd.y,   pos.y * scale], # Row for NeRF Y
                    [right.z, -up.z, fwd.z,   pos.z * scale], # Row for NeRF Z
                    [0.0,      0.0,   0.0,   1.0]           # Row for W
                ]

            # matrix_list = [[round(val, 6) for val in row] for row in matrix_list]

            camera_info = {
                "camera_id": idx,
                "file_path": f"images/frame_{idx:05d}.png", # 对应你的渲染命名
                "camera_angle_x": fov_rad,
                "camera_hw": [self.res_Y, self.res_X], # 注意：通常是 [H, W]
                "transform_matrix": matrix_list
            }
            camera_data_list.append(camera_info)

        # 路径处理
        save_path = os.path.join(self.output_dir, output_filename)
        with open(save_path, 'w') as f:
            json.dump(camera_data_list, f, indent=4)
        
        unreal.log(f"Successfully exported {len(transforms)} frames to {save_path}")

    def get_camera_rotation(self, position: unreal.Vector, random_roll=False):
        return self.get_camera_quat(position, random_roll).rotator()
    
    def get_camera_quat(self, position: unreal.Vector, random_roll=False):
        # 1. Look-at（Forward 指向原点，Up 尽量朝世界 Z）
        base_rot = unreal.MathLibrary.find_look_at_rotation(
            position, unreal.Vector(0, 0, 0)
        )

        if not random_roll:
            return base_rot.quaternion()

        # 2. Forward 轴
        forward = base_rot.get_forward_vector().normal()

        import random
        # 3. 随机 roll
        roll_rad = random.uniform(0.0, 2.0 * math.pi)

        # 4. Axis-angle → quat（必须手写）
        half = roll_rad * 0.5
        s = math.sin(half)

        roll_quat = unreal.Quat(
            forward.x * s,
            forward.y * s,
            forward.z * s,
            math.cos(half)
        )

        # 5. 组合旋转（注意顺序）
        final_quat = roll_quat * base_rot.quaternion()

        return final_quat

    def test(self, zoom_factor=1):
        self.remove_all_sections()

        positions = self.get_orbit_positions(self.n_samples, zoom_factor)

        transforms = []

        for idx, pos in enumerate(positions):
            print(f"Position {idx}: {pos}")
            start_frame = idx * 150
            
            quat = self.get_camera_quat(pos, True)
            rotation = quat.rotator()

            mrq.set_sequencer_camera_transform(
                pos,
                rotation,
                start_frame=start_frame,
                duration_frames=150
            )

            transforms.append((pos, rotation))


        # 一次性渲染 300 帧
        mrq.render_to_png_sequence(self.seq_asset_path, self.output_dir)
        # 导出参数 JSON
        self.save_camera_parameters(transforms)



# 假设你已经选中了一个 CineCameraActor
selected_actors = unreal.EditorLevelLibrary.get_selected_level_actors()
camera_actor = None
for a in selected_actors:
    if a.get_class().get_name() in ("CineCameraActor", "CameraActor"):
        camera_actor = a
        break

if not camera_actor:
    raise RuntimeError("Please select a CameraActor in the level.")

# 创建 mrq
mrq = MRQ(camera_actor, "/Game/Sequencer/start", "../../../Saved/RenderOutput", 20)

# mrq.start()
mrq.test()

# 恢复原始状态
mrq.reset_camera()






