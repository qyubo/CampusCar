"""海康 MVS SDK 图像采集适配器。"""

from __future__ import annotations

import importlib
import os
import socket
import struct
import sys
from ctypes import POINTER, cast, c_ubyte
from pathlib import Path
from typing import Any

import cv2
import numpy as np


class MvsCameraError(RuntimeError):
    """MVS 相机初始化或取帧失败。"""


class MvsCamera:
    """对海康 MVS Python wrapper 做最小稳定封装。"""

    def __init__(
        self,
        camera_ip: str = '',
        serial_number: str = '',
        sdk_path: str = '',
        width: int = 0,
        height: int = 0,
        fps: float = 0.0,
        timeout_ms: int = 1000,
    ) -> None:
        self.camera_ip = str(camera_ip or '').strip()
        self.serial_number = str(serial_number or '').strip()
        self.sdk_path = str(sdk_path or '').strip()
        self.width = int(width)
        self.height = int(height)
        self.fps = float(fps)
        self.timeout_ms = int(timeout_ms)
        self.sdk = self._load_sdk(self.sdk_path)
        self.camera = None
        self.payload_size = 0
        self._open()

    @staticmethod
    def sdk_search_paths(sdk_path: str = '') -> list[Path]:
        candidates: list[Path] = []
        if sdk_path:
            candidates.append(Path(sdk_path).expanduser())
        for variable in ('MVCAM_SDK_PATH', 'MVS_SDK_PATH'):
            value = os.environ.get(variable, '').strip()
            if value:
                candidates.append(Path(value).expanduser())
        candidates.extend(
            [
                Path('/opt/MVS/Samples/64/Python'),
                Path('/opt/MVS/Samples/64/Python/MvImport'),
                Path('/opt/MVS/Samples/64/Python/Wrapper'),
                Path('/opt/MVS/lib/64'),
                Path('/usr/local/MVS/Samples/64/Python'),
                Path('/usr/local/MVS/Samples/64/Python/MvImport'),
            ]
        )
        result: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            key = str(path.resolve()) if path.exists() else str(path)
            if key not in seen:
                seen.add(key)
                result.append(path)
        return result

    @classmethod
    def _load_sdk(cls, sdk_path: str) -> Any:
        search_paths = cls.sdk_search_paths(sdk_path)
        library_paths = [
            path for path in search_paths
            if path.name in {'64', '32', 'lib'} or path.name.startswith('lib')
        ]
        if library_paths:
            old_library_path = os.environ.get('LD_LIBRARY_PATH', '')
            new_library_path = ':'.join(str(path) for path in library_paths)
            os.environ['LD_LIBRARY_PATH'] = ':'.join(
                value for value in (new_library_path, old_library_path) if value
            )
        for path in search_paths:
            if path.exists() and path.is_dir() and str(path) not in sys.path:
                sys.path.insert(0, str(path))

        import_errors: list[str] = []
        for module_name in ('MvImport.MvCameraControl_class', 'MvCameraControl_class'):
            try:
                return importlib.import_module(module_name)
            except Exception as exc:  # noqa: BLE001
                import_errors.append(f'{module_name}: {exc}')

        paths = ', '.join(str(path) for path in search_paths)
        details = '; '.join(import_errors)
        raise MvsCameraError(
            '未找到海康 MVS Python SDK。'
            f'已搜索: {paths}。'
            f'导入错误: {details}'
        )

    def _constant(self, name: str, default: int = 0) -> int:
        return int(getattr(self.sdk, name, default))

    def _check(self, code: Any, operation: str) -> None:
        result = int(code)
        if result != 0:
            raise MvsCameraError(f'{operation}失败，MVS错误码: 0x{result:08x}')

    def _device_info(self, device_list: Any, index: int) -> Any:
        pointer = device_list.pDeviceInfo[index]
        return cast(pointer, POINTER(self.sdk.MV_CC_DEVICE_INFO)).contents

    def _device_ip(self, info: Any) -> str:
        gige_type = self._constant('MV_GIGE_DEVICE', 1)
        if int(getattr(info, 'nTLayerType', 0)) != gige_type:
            return ''
        try:
            value = int(info.SpecialInfo.stGigEInfo.nCurrentIp)
            return socket.inet_ntoa(struct.pack('I', value))
        except (AttributeError, OSError, struct.error, TypeError, ValueError):
            return ''

    def _device_serial(self, info: Any) -> str:
        try:
            value = info.SpecialInfo.stGigEInfo.chSerialNumber
        except AttributeError:
            return ''
        if isinstance(value, bytes):
            return value.split(b'\0', 1)[0].decode(errors='ignore')
        try:
            return bytes(value).split(b'\0', 1)[0].decode(errors='ignore')
        except (TypeError, ValueError):
            return str(value)

    def _matches(self, info: Any) -> bool:
        if self.camera_ip and self.camera_ip == self._device_ip(info):
            return True
        if self.serial_number and self.serial_number == self._device_serial(info):
            return True
        return not self.camera_ip and not self.serial_number

    def _enumerate_device(self) -> Any:
        device_list = self.sdk.MV_CC_DEVICE_INFO_LIST()
        layer_type = self._constant('MV_GIGE_DEVICE', 1) | self._constant('MV_USB_DEVICE', 4)
        enum_devices = getattr(self.sdk.MvCamera, 'MV_CC_EnumDevices', None)
        if enum_devices is None:
            enumerator = self.sdk.MvCamera()
            enum_devices = getattr(enumerator, 'MV_CC_EnumDevices', None)
        if enum_devices is None:
            enum_devices = getattr(self.sdk, 'MV_CC_EnumDevices', None)
        if enum_devices is None:
            raise MvsCameraError('MVS Python SDK 缺少 MV_CC_EnumDevices')
        self._check(enum_devices(layer_type, device_list), '枚举相机')

        count = int(getattr(device_list, 'nDeviceNum', 0))
        if count <= 0:
            raise MvsCameraError('MVS 未枚举到任何相机')
        for index in range(count):
            info = self._device_info(device_list, index)
            if self._matches(info):
                return info
        available = []
        for index in range(count):
            info = self._device_info(device_list, index)
            available.append(f'{self._device_ip(info) or "non-GigE"}/{self._device_serial(info) or "unknown"}')
        raise MvsCameraError(
            f'未找到目标相机 ip={self.camera_ip or "<auto>"} serial={self.serial_number or "<auto>"}；'
            f'已发现: {", ".join(available)}'
        )

    def _open(self) -> None:
        info = self._enumerate_device()
        self.camera = self.sdk.MvCamera()
        self._check(self.camera.MV_CC_CreateHandle(info), '创建相机句柄')
        try:
            access = self._constant('MV_ACCESS_Exclusive', 1)
            self._check(self.camera.MV_CC_OpenDevice(access, 0), '打开相机')
            self._check(self.camera.MV_CC_SetEnumValue('TriggerMode', 0), '关闭触发模式')
            self._set_optional('Width', self.width)
            self._set_optional('Height', self.height)
            self._set_optional('AcquisitionFrameRate', self.fps)
            self._set_optional('AcquisitionFrameRateEnable', 1 if self.fps > 0 else None)
            self._read_payload_size()
            self._check(self.camera.MV_CC_StartGrabbing(), '启动取流')
        except Exception:
            self.close()
            raise

    def _set_optional(self, name: str, value: Any) -> None:
        if value is None or (isinstance(value, (int, float)) and value <= 0):
            return
        setter = getattr(self.camera, 'MV_CC_SetFloatValue' if isinstance(value, float) else 'MV_CC_SetIntValue', None)
        if setter is None:
            return
        result = setter(name, value)
        if int(result) != 0:
            return

    def _read_payload_size(self) -> None:
        value = self.sdk.MVCC_INTVALUE()
        self._check(self.camera.MV_CC_GetIntValue('PayloadSize', value), '读取PayloadSize')
        self.payload_size = int(value.nCurValue)
        if self.payload_size <= 0:
            raise MvsCameraError('相机返回无效 PayloadSize')

    def _pixel_constant(self, name: str) -> int | None:
        value = getattr(self.sdk, name, None)
        return None if value is None else int(value)

    def _frame_to_bgr(self, buffer: Any, frame_info: Any) -> np.ndarray:
        width = int(frame_info.nWidth)
        height = int(frame_info.nHeight)
        length = int(frame_info.nFrameLen)
        pixel_type = int(frame_info.enPixelType)
        raw = np.frombuffer(buffer, dtype=np.uint8, count=length)

        if pixel_type == self._pixel_constant('PixelType_Gvsp_Mono8'):
            return cv2.cvtColor(raw.reshape(height, width), cv2.COLOR_GRAY2BGR)
        if pixel_type == self._pixel_constant('PixelType_Gvsp_BGR8_Packed'):
            return raw.reshape(height, width, 3).copy()
        if pixel_type == self._pixel_constant('PixelType_Gvsp_RGB8_Packed'):
            return cv2.cvtColor(raw.reshape(height, width, 3), cv2.COLOR_RGB2BGR)

        converter_type = getattr(self.sdk, 'MV_CC_PIXEL_CONVERT_PARAM', None)
        converter = getattr(self.camera, 'MV_CC_ConvertPixelType', None)
        bgr_type = self._pixel_constant('PixelType_Gvsp_BGR8_Packed')
        if converter_type is None or converter is None or bgr_type is None:
            raise MvsCameraError(f'暂不支持像素格式: 0x{pixel_type:08x}')

        dst_size = width * height * 3
        destination = (c_ubyte * dst_size)()
        params = converter_type()
        params.nWidth = width
        params.nHeight = height
        params.pSrcData = buffer
        params.nSrcDataLen = length
        params.enSrcPixelType = pixel_type
        params.enDstPixelType = bgr_type
        params.pDstBuffer = destination
        params.nDstBufferSize = dst_size
        self._check(converter(params), 'MVS像素格式转换')
        return np.frombuffer(destination, dtype=np.uint8, count=dst_size).reshape(height, width, 3).copy()

    def read(self) -> np.ndarray:
        if self.camera is None:
            raise MvsCameraError('相机未打开')
        data = (c_ubyte * self.payload_size)()
        frame_info = self.sdk.MV_FRAME_OUT_INFO_EX()
        result = self.camera.MV_CC_GetOneFrameTimeout(data, self.payload_size, frame_info, self.timeout_ms)
        self._check(result, '读取相机帧')
        return self._frame_to_bgr(data, frame_info)

    def close(self) -> None:
        if self.camera is None:
            return
        try:
            self.camera.MV_CC_StopGrabbing()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.camera.MV_CC_CloseDevice()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.camera.MV_CC_DestroyHandle()
        except Exception:  # noqa: BLE001
            pass
        self.camera = None
