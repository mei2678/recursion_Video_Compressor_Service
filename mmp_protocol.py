import json
import struct
from enum import Enum
from typing import Dict, Any, Tuple

class MediaType(Enum):
    MP4 = "mp4"
    MP3 = "mp3"
    GIF = "gif"
    WEBM = "webm"
    JSON = "json"

class MMPHeader:
    def __init__(self, json_size: int, media_type_size: int, payload_size: int):
        self.json_size = json_size  # JSONサイズバイト (max 64KB)
        self.media_type_size = media_type_size  # メディアタイプサイズバイト (max 255)
        self.payload_size = payload_size  # プレイロードサイズバイト (max 1TB)

    @classmethod
    def from_bytes(cls, header_bytes: bytes) -> 'MMPHeader':
        json_size = struct.unpack('!H', header_bytes[0:2])[0]  # unsigned short (2バイト)
        media_type_size = struct.unpack('!B', header_bytes[2:3])[0]  # unsigned char (1バイト)
        payload_size = struct.unpack('!Q', header_bytes[3:8])[0]  # unsigned long long (5バイト使用)
        return cls(json_size, media_type_size, payload_size)

    def to_bytes(self) -> bytes:
        return struct.pack('!HBQ', 
                         self.json_size,
                         self.media_type_size,  
                         self.payload_size)

class MMPMessage:
    def __init__(self, json_data: Dict[str, Any], media_type: str, payload: bytes):
        self.json_data = json_data
        self.media_type = media_type
        self.payload = payload

    @classmethod
    def create_error_message(cls, error_code: int, description: str, solution: str) -> 'MMPMessage':
        error_json = {
            "error_code": error_code,
            "description": description,
            "solution": solution
        }
        return cls(error_json, "json", b"")

    def encode(self) -> Tuple[bytes, bytes, bytes]:
        json_bytes = json.dumps(self.json_data).encode('utf-8')
        media_type_bytes = self.media_type.encode('utf-8')
        
        header = MMPHeader(
            len(json_bytes),
            len(media_type_bytes),
            len(self.payload)
        )
        
        return header.to_bytes(), json_bytes + media_type_bytes, self.payload

    @classmethod
    def decode(cls, header_bytes: bytes, body_bytes: bytes, payload_bytes: bytes) -> 'MMPMessage':
        header = MMPHeader.from_bytes(header_bytes)
        json_data = json.loads(body_bytes[:header.json_size].decode('utf-8'))
        media_type = body_bytes[header.json_size:header.json_size + header.media_type_size].decode('utf-8')
        return cls(json_data, media_type, payload_bytes)

# 動画処理タイプの定義
class VideoProcessType(Enum):
    COMPRESS = "compress"
    RESIZE_RESOLUTION = "resize_resolution"
    CHANGE_ASPECT_RATIO = "change_aspect_ratio"
    EXTRACT_AUDIO = "extract_audio"
    CREATE_GIF = "create_gif"
    CREATE_WEBM = "create_webm"
