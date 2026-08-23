from rtk_gps_driver.nmea import navsat_status, parse_gga, quality_name


def test_parse_gga_and_quality_mapping():
    sentence = "$GNGGA,123519,2230.0000,N,11354.0000,E,4,12,0.8,10.0,M,0.0,M,,*5F"
    fix = parse_gga(sentence)

    assert fix is not None
    assert round(fix.latitude, 6) == 22.5
    assert round(fix.longitude, 6) == 113.9
    assert fix.quality == 4
    assert navsat_status(fix.quality) == 2
    assert quality_name(fix.quality) == "RTK_FIXED"


def test_reject_invalid_checksum():
    sentence = "$GNGGA,123519,2230.0000,N,11354.0000,E,4,12,0.8,10.0,M,0.0,M,,*00"
    assert parse_gga(sentence) is None
