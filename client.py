import socket
import os
import argparse
import time
from typing import Optional, Dict, Any
from mmp_protocol import MMPMessage, VideoProcessType, MediaType

class VideoProcessingClient:
    def __init__(self, host='localhost', port=8000):
        self.host = host
        self.port = port
        self.status_check_interval = 60  # 1分間隔で処理状況を確認

    def _validate_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist")
            return False

        if not file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            print("Error: Unsupported file format")
            return False

        file_size = os.path.getsize(file_path)
        if file_size > 4 * 1024 * 1024 * 1024:  # 4GB
            print("Error: File size must be less than 4GB")
            return False

        return True

    def _send_request(self, file_path: str, process_type: VideoProcessType, params: Optional[Dict[str, Any]] = None) -> bool:
        if not self._validate_file(file_path):
            return False

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.host, self.port))

            # ファイルを読み込んでメッセージを作成
            with open(file_path, 'rb') as f:
                file_content = f.read()

            json_data = {"process_type": process_type.value}
            if params:
                json_data.update(params)

            message = MMPMessage(
                json_data=json_data,
                media_type=MediaType.MP4.value,
                payload=file_content
            )

            # リクエストを送信
            header_bytes, body_bytes, payload = message.encode()
            client_socket.sendall(header_bytes)
            client_socket.sendall(body_bytes)
            client_socket.sendall(payload)

            print("Request sent, waiting for response...")

            # レスポンスを受信
            header_bytes = client_socket.recv(8)
            if not header_bytes:
                print("Error: No response from server")
                return False

            response = MMPMessage.decode_from_socket(client_socket, header_bytes)
            if not response:
                print("Error: Invalid response from server")
                return False

            if "error_code" in response.json_data:
                print(f"Error: {response.json_data['description']}")
                print(f"Solution: {response.json_data['solution']}")
                return False

            # 処理結果をファイルに保存
            output_path = self._generate_output_path(file_path, response.media_type)
            with open(output_path, 'wb') as f:
                f.write(response.payload)

            print(f"\nProcessing complete! Output saved to: {output_path}")
            return True

        except ConnectionRefusedError:
            print("Error: Could not connect to server. Make sure the server is running.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if 'client_socket' in locals():
                client_socket.close()

        return False

    def _generate_output_path(self, input_path: str, output_type: str) -> str:
        directory = os.path.dirname(input_path)
        filename = os.path.splitext(os.path.basename(input_path))[0]
        return os.path.join(directory, f"{filename}_processed.{output_type}")

    def compress_video(self, file_path: str) -> bool:
        return self._send_request(file_path, VideoProcessType.COMPRESS)

    def resize_resolution(self, file_path: str, width: int, height: int) -> bool:
        params = {"width": width, "height": height}
        return self._send_request(file_path, VideoProcessType.RESIZE_RESOLUTION, params)

    def change_aspect_ratio(self, file_path: str, aspect_ratio: str) -> bool:
        params = {"aspect_ratio": aspect_ratio}
        return self._send_request(file_path, VideoProcessType.CHANGE_ASPECT_RATIO, params)

    def extract_audio(self, file_path: str) -> bool:
        return self._send_request(file_path, VideoProcessType.EXTRACT_AUDIO)

    def create_gif(self, file_path: str, start_time: str, duration: str) -> bool:
        params = {"start_time": start_time, "duration": duration}
        return self._send_request(file_path, VideoProcessType.CREATE_GIF, params)

    def create_webm(self, file_path: str, start_time: str, duration: str) -> bool:
        params = {"start_time": start_time, "duration": duration}
        return self._send_request(file_path, VideoProcessType.CREATE_WEBM, params)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process a video file')
    parser.add_argument('file', help='Path to the video file')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8000, help='Server port')
    parser.add_argument('--action', choices=['compress', 'resize', 'aspect', 'audio', 'gif', 'webm'],
                        required=True, help='Processing action to perform')
    parser.add_argument('--width', type=int, help='Width for resize')
    parser.add_argument('--height', type=int, help='Height for resize')
    parser.add_argument('--aspect-ratio', help='Aspect ratio (e.g., "16:9")')
    parser.add_argument('--start-time', help='Start time for gif/webm (e.g., "00:00:00")')
    parser.add_argument('--duration', help='Duration for gif/webm (e.g., "00:00:10")')

    args = parser.parse_args()
    client = VideoProcessingClient(host=args.host, port=args.port)

    if args.action == 'compress':
        client.compress_video(args.file)
    elif args.action == 'resize':
        if not args.width or not args.height:
            print("Error: Width and height are required for resize")
        else:
            client.resize_resolution(args.file, args.width, args.height)
    elif args.action == 'aspect':
        if not args.aspect_ratio:
            print("Error: Aspect ratio is required (e.g., --aspect-ratio '16:9')")
        else:
            client.change_aspect_ratio(args.file, args.aspect_ratio)
    elif args.action == 'audio':
        client.extract_audio(args.file)
    elif args.action in ['gif', 'webm']:
        if not args.start_time or not args.duration:
            print("Error: Start time and duration are required for gif/webm creation")
        else:
            if args.action == 'gif':
                client.create_gif(args.file, args.start_time, args.duration)
            else:
                client.create_webm(args.file, args.start_time, args.duration)
