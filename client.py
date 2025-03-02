import socket
import os
import struct
import argparse

class VideoUploadClient:
    def __init__(self, host='localhost', port=8000):
        self.host = host
        self.port = port
        self.packet_size = 1400 # 1400バイトのパケットサイズでファイル送信

    def validate_file(self, filepath):
        # ファイルの存在チェック
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        # mp4ファイルのチェック
        if not filepath.lower().endswith('.mp4'):
            raise ValueError("Only .mp4 files are supported")

        # ファイルサイズチェック
        file_size = os.path.getsize(filepath)
        if file_size > 4 * 1024 * 1024 * 1024:  # 4GB
            raise ValueError("File size exceeds 4GB limit")

        return file_size

    def upload_file(self, filepath):
        try:
            # ファイルのバリデーション
            file_size = self.validate_file(filepath)

            # ソケットを作成しサーバーに接続
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((self.host, self.port))

            # 最初に送信する32バイトでファイルサイズを指定
            size_str = str(file_size).ljust(32)
            client_socket.send(size_str.encode())

            # ファイル送信
            sent_size = 0
            with open(filepath, 'rb') as f:
                while sent_size < file_size:
                    remaining = file_size - sent_size
                    chunk_size = min(self.packet_size, remaining)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    client_socket.send(chunk)
                    sent_size += len(chunk)
                    # 進捗表示
                    progress = (sent_size / file_size) * 100
                    print(f"Upload progress: {progress:.2f}%", end='\r')

            print("\nWaiting for server response...")
            # サーバーからのレスポンスを受信(ステータス情報を含む16バイトのメッセージ)
            response = struct.unpack('!16s', client_socket.recv(16))[0].strip()
            response_str = response.decode()

            if 'UPLOAD_SUCCESS' in response_str:
                print("File uploaded successfully!")
            elif 'STORAGE_FULL' in response_str:
                print("Error: Server storage is full")
            elif 'UPLOAD_FAILED' in response_str:
                print("Error: Upload failed")
            else:
                print(f"Error: Unknown server response - {response_str}")

        except ConnectionRefusedError:
            print("Error: Could not connect to server")
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            client_socket.close()

def main():
  # コマンドライン引数のパーサーを作成
    parser = argparse.ArgumentParser(description='Upload video files to server')
    parser.add_argument('file', help='Path to the mp4 file to upload')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8000, help='Server port')

    args = parser.parse_args()
    client = VideoUploadClient(args.host, args.port)
    client.upload_file(args.file)

if __name__ == '__main__':
    main()
