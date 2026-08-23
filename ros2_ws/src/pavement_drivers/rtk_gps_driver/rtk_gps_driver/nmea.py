"""Small, dependency-free NMEA GGA parser used by the ROS2 node and monitor."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GGAFix:
    """The fields needed by NavSatFix and NTRIP."""

    sentence: str
    latitude: float
    longitude: float
    altitude: float
    quality: int
    satellites: int
    hdop: float


def _nmea_coordinate(value: str, direction: str) -> Optional[float]:
    if not value or direction not in {"N", "S", "E", "W"}:
        return None
    try:
        number = float(value)
        degrees = int(number / 100)
        minutes = number - degrees * 100
        if minutes >= 60:
            return None
        result = degrees + minutes / 60.0
        return -result if direction in {"S", "W"} else result
    except (TypeError, ValueError):
        return None


def _checksum_is_valid(sentence: str) -> bool:
    if "*" not in sentence:
        return True
    body, checksum = sentence[1:].split("*", 1)
    if len(checksum) < 2:
        return False
    value = 0
    for char in body:
        value ^= ord(char)
    try:
        return value == int(checksum[:2], 16)
    except ValueError:
        return False


def parse_gga(sentence: str) -> Optional[GGAFix]:
    """Parse a GGA sentence; quality 0 is retained as an invalid fix."""
    sentence = sentence.strip()
    if not sentence.startswith("$") or not _checksum_is_valid(sentence):
        return None
    fields = sentence.split("*", 1)[0].split(",")
    if len(fields) < 10 or not fields[0].upper().endswith("GGA"):
        return None
    latitude = _nmea_coordinate(fields[2], fields[3].upper())
    longitude = _nmea_coordinate(fields[4], fields[5].upper())
    if latitude is None or longitude is None:
        return None
    try:
        quality = int(fields[6] or 0)
        satellites = int(fields[7] or 0)
        hdop = float(fields[8] or 99.9)
        altitude = float(fields[9] or 0.0)
    except ValueError:
        return None
    return GGAFix(
        sentence=sentence,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        quality=quality,
        satellites=satellites,
        hdop=hdop,
    )


def quality_name(quality: int) -> str:
    return {
        0: "NO_FIX",
        1: "SINGLE",
        2: "DIFFERENTIAL",
        4: "RTK_FIXED",
        5: "RTK_FLOAT",
        6: "ESTIMATED",
    }.get(quality, f"UNKNOWN_{quality}")


def navsat_status(quality: int) -> int:
    """Map NMEA GGA quality to sensor_msgs/NavSatStatus constants."""
    if quality == 0:
        return -1
    if quality in {2, 6}:
        return 1
    if quality in {4, 5}:
        return 2
    return 0
