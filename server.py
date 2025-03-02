import socket
import threading
import os
import argparse
from datetime import datetime
from typing import Dict, Set
from mmp_protocol import MMPMessage, VideoProcessType
from video_processor import VideoProcessor

class VideoProcessingServer:
    def __init__(self, host='localhost', port=8000):
        self.host = host
        self.port = port
        self.max_storage = 4 * 1024 * 1024 * 1024 * 1024  # 4TB
        self.server_socket = None
        self.running = False
        self.active_clients: Dict[str, int] = {}  # IP address -> active processes count
        self.video_processor = VideoProcessor()
        self.processing_files: Set[str] = set()

    def _can_process_request(self, client_ip: str) -> bool:
      # 一つのクライアントから同時に1つの処理のみ受け付ける
        return self.active_clients.get(client_ip, 0) < 1

    def _add_client_process(self, client_ip: str):
        self.active_clients[client_ip] = self.active_clients.get(client_ip, 0) + 1

    def _remove_client_process(self, client_ip: str):
        self.active_clients[client_ip] = max(0, self.active_clients.get(client_ip, 0) - 1)

    def handle_client(self, client_socket: socket.socket, address: tuple):
        client_ip = address[0]
        try:
            # ヘッダーを受信（8バイト）
            header_bytes = client_socket.recv(8)
            if not header_bytes or len(header_bytes) != 8:
                return

            # ボディとペイロードを受信
            message = self._receive_message(client_socket, header_bytes)
            if not message:
                return

            # リクエストを処理
            if not self._can_process_request(client_ip):
                self._send_error(client_socket, 429, "Too many requests", "Please wait for your current process to complete")
                return

            self._add_client_process(client_ip)
            try:
                self._process_request(client_socket, message)
            finally:
                self._remove_client_process(client_ip)

        except Exception as e:
            print(f"Error handling client {address}: {e}")
            self._send_error(client_socket, 500, "Internal server error", str(e))
        finally:
            client_socket.close()

    def _receive_message(self, client_socket: socket.socket, header_bytes: bytes) -> MMPMessage:
        try:
            message = MMPMessage.decode_from_socket(client_socket, header_bytes)
            return message
        except Exception as e:
            print(f"Error receiving message: {e}")
            return None

    def _process_request(self, client_socket: socket.socket, message: MMPMessage):
        process_type = message.json_data.get('process_type')
        if not process_type:
            self._send_error(client_socket, 400, "Missing process type", "Please specify a process type")
            return

        # 一時ファイルを保存
        input_file = self._save_temp_file(message.payload, message.media_type)
        try:
            # プロセスタイプに応じた処理を実行
            if process_type == VideoProcessType.COMPRESS.value:
                success, msg, output_file = self.video_processor.compress_video(input_file)
            elif process_type == VideoProcessType.RESIZE_RESOLUTION.value:
                width = message.json_data.get('width', 1920)
                height = message.json_data.get('height', 1080)
                success, msg, output_file = self.video_processor.resize_resolution(input_file, width, height)
            elif process_type == VideoProcessType.CHANGE_ASPECT_RATIO.value:
                aspect_ratio = message.json_data.get('aspect_ratio', '16:9')
                success, msg, output_file = self.video_processor.change_aspect_ratio(input_file, aspect_ratio)
            elif process_type == VideoProcessType.EXTRACT_AUDIO.value:
                success, msg, output_file = self.video_processor.extract_audio(input_file)
            elif process_type in [VideoProcessType.CREATE_GIF.value, VideoProcessType.CREATE_WEBM.value]:
                start_time = message.json_data.get('start_time', '00:00:00')
                duration = message.json_data.get('duration', '00:00:10')
                if process_type == VideoProcessType.CREATE_GIF.value:
                    success, msg, output_file = self.video_processor.create_gif(input_file, start_time, duration)
                else:
                    success, msg, output_file = self.video_processor.create_webm(input_file, start_time, duration)
            else:
                self._send_error(client_socket, 400, "Invalid process type", "Please specify a valid process type")
                return

            if success and output_file:
                self._send_processed_file(client_socket, output_file)
            else:
                self._send_error(client_socket, 500, "Processing failed", msg)

        finally:
            # 一時ファイルを削除
            self.video_processor.cleanup_temp_file(input_file)
            if output_file:
                self.video_processor.cleanup_temp_file(output_file)

    def _save_temp_file(self, payload: bytes, media_type: str) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'input_{timestamp}.{media_type}'
        filepath = os.path.join(self.video_processor.temp_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(payload)
        return filepath

    def _send_processed_file(self, client_socket: socket.socket, filepath: str):
        try:
            with open(filepath, 'rb') as f:
                payload = f.read()
                media_type = filepath.split('.')[-1]
                message = MMPMessage(
                    json_data={"status": "success"},
                    media_type=media_type,
                    payload=payload
                )
                self._send_message(client_socket, message)
        except Exception as e:
            self._send_error(client_socket, 500, "Error sending processed file", str(e))

    def _send_error(self, client_socket: socket.socket, code: int, description: str, solution: str):
        message = MMPMessage.create_error_message(code, description, solution)
        self._send_message(client_socket, message)

    def _send_message(self, client_socket: socket.socket, message: MMPMessage):
        try:
            header_bytes, body_bytes, payload = message.encode()
            client_socket.sendall(header_bytes)
            client_socket.sendall(body_bytes)
            if payload:
                client_socket.sendall(payload)
        except Exception as e:
            print(f"Error sending message: {e}")

    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f"Server started on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"New connection from {address}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start the video processing server')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8000, help='Server port')

    args = parser.parse_args()
    server = VideoProcessingServer(host=args.host, port=args.port)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
        print("\nShutting down server...")
        server.stop()
