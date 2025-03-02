import socket
import threading
import os
import struct
import argparse
from datetime import datetime

class VideoUploadServer:
    def __init__(self, host='localhost', port=8000, storage_dir='uploads'):
        self.host = host
        self.port = port
        self.storage_dir = storage_dir
        self.max_storage = 4 * 1024 * 1024 * 1024 * 1024  # 最大4TBのファイルを保存可能
        self.packet_size = 1400 # 1400バイトのパケットサイズでファイル受信
        self.server_socket = None # 使用するソケット
        self.running = False # サーバーが動作中かどうか

        # ストレージディレクトリの作成
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)

    # ストレージディレクトリ内の全ファイルサイズを取得する
    def get_total_storage_used(self):
        total_size = 0
        # os.walk()で対象ディレクトリ内を走査する
        for dirpath, dirnames, filenames in os.walk(self.storage_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    # クライアントへの応答処理
    def handle_client(self, client_socket, address):
        try:
            # 最初にサーバーに送信される32バイトは、ファイルのバイト数
            file_size_bytes = client_socket.recv(32)
            file_size = int(file_size_bytes.decode().strip())

            # ストレージ容量チェック
            if self.get_total_storage_used() + file_size > self.max_storage:
              # struct.pack()でエラーメッセージを16バイトの文字列に変換
                client_socket.send(struct.pack('!16s', b'STORAGE_FULL'))
                return

            # ファイル名の生成（タイムスタンプ）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'video_{timestamp}.mp4'
            filepath = os.path.join(self.storage_dir, filename)

            # ファイル受信
            # 受信データをパケットサイズに分割してファイルに書き出し
            received_size = 0
            with open(filepath, 'wb') as f:
                while received_size < file_size:
                    remaining = file_size - received_size
                    chunk_size = min(self.packet_size, remaining)
                    chunk = client_socket.recv(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    received_size += len(chunk)

            # 完了メッセージ送信
            # struct.pack()でメッセージを16バイトの文字列に変換
            if received_size == file_size:
                client_socket.send(struct.pack('!16s', b'UPLOAD_SUCCESS'))
            else:
              # ネットワーク切断、クライアントプログラムの異常終了、送信中のエラー発生などの場合
                client_socket.send(struct.pack('!16s', b'UPLOAD_FAILED'))
                os.remove(filepath)  # 不完全なファイルを削除

        except Exception as e:
            print(f"Error handling client {address}: {e}")
            try:
                client_socket.send(struct.pack('!16s', b'SERVER_ERROR'))
            except:
                pass
        finally:
            client_socket.close()

    def start(self):
      # TCPソケットの作成
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # ソケットをポートに割り当て、リッスン
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        # 動作状態のフラグをtrueに設定
        self.running = True
        print(f"Server started on {self.host}:{self.port}")

        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                print(f"New connection from {address}")
                
                # クライアントへの応答処理を別スレッドで実行
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
    # コマンドライン引数のパーサーを作成
    parser = argparse.ArgumentParser(description='Start the video upload server')
    parser.add_argument('--host', default='localhost', help='Server host')
    parser.add_argument('--port', type=int, default=8000, help='Server port')

    # 引数を解析
    args = parser.parse_args()
    
    # サーバーインスタンスを作成して起動
    server = VideoUploadServer(host=args.host, port=args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()
