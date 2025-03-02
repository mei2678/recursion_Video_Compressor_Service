import os
import subprocess
from typing import Tuple, Optional
import json
from datetime import datetime

class VideoProcessor:
    def __init__(self, temp_dir: str = "tmp"):
        self.temp_dir = temp_dir
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

    def _generate_temp_filename(self, extension: str) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return os.path.join(self.temp_dir, f'temp_{timestamp}.{extension}')

    def _run_ffmpeg_command(self, command: list) -> Tuple[bool, str]:
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                return False, f"FFmpeg error: {result.stderr}"
            return True, "Success"
        except Exception as e:
            return False, str(e)

    def compress_video(self, input_file: str) -> Tuple[bool, str, Optional[str]]:
        output_file = self._generate_temp_filename('mp4')
        command = [
            'ffmpeg', '-i', input_file,
            '-c:v', 'libx264', '-crf', '23',  # 画質と圧縮率のバランス
            '-c:a', 'aac', '-b:a', '128k',    # 音声圧縮
            output_file
        ]
        success, message = self._run_ffmpeg_command(command)
        return success, message, output_file if success else None

    def resize_resolution(self, input_file: str, width: int, height: int) -> Tuple[bool, str, Optional[str]]:
        output_file = self._generate_temp_filename('mp4')
        command = [
            'ffmpeg', '-i', input_file,
            '-vf', f'scale={width}:{height}',
            '-c:a', 'copy',
            output_file
        ]
        success, message = self._run_ffmpeg_command(command)
        return success, message, output_file if success else None

    def change_aspect_ratio(self, input_file: str, aspect_ratio: str) -> Tuple[bool, str, Optional[str]]:
        output_file = self._generate_temp_filename('mp4')
        # アスペクト比を幅と高さに分解（例：16:9）
        width, height = map(int, aspect_ratio.split(':'))
        command = [
            'ffmpeg', '-i', input_file,
            '-vf', f'scale=iw*min({width}/iw\\,{height}/ih):ih*min({width}/iw\\,{height}/ih)',
            '-c:a', 'copy',
            output_file
        ]
        success, message = self._run_ffmpeg_command(command)
        return success, message, output_file if success else None

    def extract_audio(self, input_file: str) -> Tuple[bool, str, Optional[str]]:
        output_file = self._generate_temp_filename('mp3')
        command = [
            'ffmpeg', '-i', input_file,
            '-vn',  # 映像を無効化
            '-ar', '44100',  # サンプリングレート
            '-ac', '2',      # ステレオ
            '-b:a', '192k',  # ビットレート
            output_file
        ]
        success, message = self._run_ffmpeg_command(command)
        return success, message, output_file if success else None

    def create_gif(self, input_file: str, start_time: str, duration: str) -> Tuple[bool, str, Optional[str]]:
        output_file = self._generate_temp_filename('gif')
        command = [
            'ffmpeg', '-i', input_file,
            '-ss', start_time,
            '-t', duration,
            '-vf', 'fps=10,scale=320:-1:flags=lanczos',
            output_file
        ]
        success, message = self._run_ffmpeg_command(command)
        return success, message, output_file if success else None

    def create_webm(self, input_file: str, start_time: str, duration: str) -> Tuple[bool, str, Optional[str]]:
        output_file = self._generate_temp_filename('webm')
        command = [
            'ffmpeg', '-i', input_file,
            '-ss', start_time,
            '-t', duration,
            '-c:v', 'libvpx-vp9',
            '-crf', '30',
            '-b:v', '0',
            output_file
        ]
        success, message = self._run_ffmpeg_command(command)
        return success, message, output_file if success else None

    def cleanup_temp_file(self, filepath: str):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            print(f"Error cleaning up temp file {filepath}: {e}")
