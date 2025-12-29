import math
import unreal

class MRQ:
    def __init__(self, camera_actor: unreal.Actor, seq_asset_path: str, output_path: str, n_samples: int = 4):
        self.initial_location = camera_actor.get_actor_location()
        self.initial_rotation = camera_actor.get_actor_rotation()
        self.radius = self.initial_location.length()
        self.seq_asset_path = seq_asset_path
        self.output_path = output_path      
        self.n_samples = n_samples

        self.track = self.find_track("CineCameraActor")

        if self.radius == 0.0:
            raise ValueError("Camera is at origin; cannot orbit.")
        
    def start(self):
        positions = self.get_orbit_positions(self.n_samples)
        for i in range(self.n_samples):
            mrq.set_camera_to_position(positions[i])
            mrq.render_to_png_sequence(seq_path=self.seq_asset_path, output_dir=mrq.output_path)
        mrq.reset_camera()

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

    def get_orbit_positions(self, n_samples: int):
        unit = self._fibonacci_sphere(n_samples)
        aligned = self._align_first_point_to_initial_dir(unit)
        unit = [p * self.radius for p in aligned]
        for i, p in enumerate(unit):
            print(i, p)
        return unit

    def set_camera_to_position(self, position: unreal.Vector):
        # 设置旋转：看向原点
        rotation = unreal.MathLibrary.find_look_at_rotation(position, unreal.Vector(0, 0, 0))

        self.set_sequencer_camera_transform(
            seq_asset_path="/Game/Sequencer/start",
            camera_label="CineCameraActor",
            location=position,
            rotation=rotation,
            frame=150
        )

    def reset_camera(self):
        self.set_sequencer_camera_transform(
            seq_asset_path="/Game/Sequencer/start",
            camera_label="CineCameraActor",
            location=self.initial_location,
            rotation=self.initial_rotation,
            start_frame = 0,
            duration_frames = 1
        )

    def orbit_and_apply(self, index: int, n_samples: int):
        positions = self.get_orbit_positions(n_samples)
        if not (0 <= index < len(positions)):
            raise IndexError(f"Index {index} out of range.")
        self.set_camera_to_position(positions[index])

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
        capture.settings.output_format = "{sequence}_{frame}"
        capture.settings.zero_pad_frame_numbers = 5
        capture.settings.use_custom_frame_rate = True
        capture.settings.custom_frame_rate = unreal.FrameRate(30, 1)
        capture.settings.resolution.res_x = 400
        capture.settings.resolution.res_y = 400

        # 设置为 PNG 图像序列
        capture.set_image_capture_protocol_type(
            unreal.load_class(None, "/Script/MovieSceneCapture.ImageSequenceProtocol_PNG")
        )
        capture.get_image_capture_protocol().compression_quality = 100

        # 开始渲染
        unreal.SequencerTools.render_movie(capture, unreal.OnRenderMovieStopped())

    def test(self):
        self.remove_all_sections()

        positions = self.get_orbit_positions(self.n_samples)
        
        for idx, pos in enumerate(positions):
            print(f"Position {idx}: {pos}")
            start_frame = idx * 150
            rotation = unreal.MathLibrary.find_look_at_rotation(pos, unreal.Vector(0,0,0))
            mrq.set_sequencer_camera_transform(
                pos,
                rotation,
                start_frame=start_frame,
                duration_frames=150
            )

        output_dir = f"{self.output_path}/camera_{idx}"   
        # 一次性渲染 300 帧
        mrq.render_to_png_sequence(self.seq_asset_path, output_dir)

        

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
mrq = MRQ(camera_actor, "/Game/Sequencer/start", "../../../Saved/RenderOutput", 2)

# mrq.start()
mrq.test()

# 恢复原始状态
# mrq.reset_camera()



