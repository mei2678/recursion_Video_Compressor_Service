# 概要

このサービスは、動画ファイルをサーバーにアップロードし、様々な処理を行うことができます。サーバーはFFMPEGを使用して動画処理を実行し、処理済みのファイルをクライアントに返送します。

# 機能要件

## 通信プロトコル

クライアントとサーバー間の通信には、Multiple Media Protocol（MMP）を使用します：

- **ヘッダー（64ビット）**:
  - JSONサイズ（2バイト）
  - メディアタイプサイズ（1バイト）
  - ペイロードサイズ（5バイト）

- **ボディ**:
  - JSON（最大64KB）: 処理パラメータを含む
  - メディアタイプ: ファイル形式（mp4, mp3, gif, webmなど）
  - ペイロード: ファイルデータ（最大1TB）

## 動画処理機能

1. **動画圧縮**
   ```bash
   python client.py video.mp4 --action compress
   ```

2. **解像度変更**
   ```bash
   python client.py video.mp4 --action resize --width 1920 --height 1080
   ```

3. **アスペクト比変更**
   ```bash
   python client.py video.mp4 --action aspect --aspect-ratio "16:9"
   ```

4. **音声抽出（MP3）**
   ```bash
   python client.py video.mp4 --action audio
   ```

5. **GIF作成**
   ```bash
   python client.py video.mp4 --action gif --start-time "00:00:00" --duration "00:00:10"
   ```

6. **WEBM作成**
   ```bash
   python client.py video.mp4 --action webm --start-time "00:00:00" --duration "00:00:10"
   ```

# 非機能要件

- サーバーは最大で4TBのデータを一時的に保存可能
- 全てのファイルは処理完了後に自動的に削除される
- 1つのIPアドレスからは同時に1つの処理のみ受け付ける
- サーバーのリソースの60%以上を動画処理に割り当てる
- 毎秒5,000個の1,400バイトのパケットを処理可能

# 動作確認方法

## 1. 必要なソフトウェア

- Python 3.7以上
- FFmpeg

MacでのFFmpegインストール:
```bash
brew install ffmpeg
```

## 2. サーバーの起動

```bash
# ローカルで起動
python server.py

# 特定のIPアドレスでの起動（他のデバイスからのアクセス用）
python server.py --host 192.168.1.100
```

## 3. クライアントの実行

### 基本的な使い方
```bash
# 動画圧縮
python client.py video.mp4 --action compress

# 解像度変更（1080p）
python client.py video.mp4 --action resize --width 1920 --height 1080

# アスペクト比変更（16:9）
python client.py video.mp4 --action aspect --aspect-ratio "16:9"

# 音声抽出
python client.py video.mp4 --action audio

# GIF作成（最初の10秒）
python client.py video.mp4 --action gif --start-time "00:00:00" --duration "00:00:10"
```

### リモートサーバーの指定
```bash
python client.py video.mp4 --action compress --host 192.168.1.100 --port 8000
```

## 3. アップロード状況の確認

クライアント実行時に以下のような進捗状況が表示されます：

```
Upload progress: 45.67%  # リアルタイムで更新
Waiting for server response...
File uploaded successfully!  # アップロード成功時
```

## 4. サーバーの終了

サーバーを終了するには、ターミナルで`Ctrl+C`を押します。

```
^C
Shutting down server...
```

## 注意事項

- サーバーが起動していない状態でクライアントを実行すると、接続エラーが発生します
- サポートされるファイル形式: mp4, avi, mov, mkv
- ファイルサイズは4GB以下である必要があります
- 1つのIPアドレスからは同時に1つの処理のみ実行できます
- 処理結果は元のファイル名に `_processed` を付加して保存されます
- ファイル名に空白が含まれる場合は、クォートで囲んで指定してください：
  ```bash
  python client.py "~/Downloads/my video.mp4" --action compress
  ```

## ネットワーク接続

異なるデバイス間でファイル転送を行う場合：

1. サーバー側の IP アドレスを確認：

```bash
# Macの場合
ifconfig | grep "inet "
```

2. サーバーを起動（サーバーデバイスの IP アドレスを指定）：

```bash
# 例：サーバーのIPアドレスが192.168.1.100の場合
python server.py --host 192.168.1.100
```

3. クライアントを実行（サーバーの IP アドレスを指定）：

```bash
python client.py video.mp4 --host 192.168.1.100
```

注意：

- `localhost`や`127.0.0.1`は同じデバイス内でのみ接続可能です
- 異なるデバイス間で接続する場合は、ローカル IP アドレスを使用してください
- ファイアウォールの設定で使用するポート（デフォルト：8000）が開いている必要があります
