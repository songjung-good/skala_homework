import pytest
from pydantic import ValidationError
from main import OpenMeteoResponse, RestCountriesResponse, IpApiResponse


# 1. IP-API 스키마 검증 테스트 (정상 케이스)
def test_ip_api_validation_success():
    valid_data = {
        "status": "success",
        "country": "South Korea",
        "city": "Seoul",
        "lat": 37.5665,
        "lon": 126.9780,
        "query": "127.0.0.1"
    }
    response = IpApiResponse.model_validate(valid_data)
    assert response.status == "success"
    assert response.city == "Seoul"
    assert response.lat == 37.5665


# 2. IP-API 스키마 검증 테스트 (실패 케이스: status != success)
def test_ip_api_validation_failure():
    invalid_data = {
        "status": "fail",  # validator에 의해 ValidationError 유발
        "country": "South Korea",
        "city": "Seoul",
        "lat": 37.5665,
        "lon": 126.9780,
        "query": "127.0.0.1"
    }
    with pytest.raises(ValidationError) as excinfo:
        IpApiResponse.model_validate(invalid_data)
    assert "IP 조회 API가 실패 응답을 반환했습니다" in str(excinfo.value)


# 3. RestCountries 스키마 검증 테스트 (정상 케이스)
def test_rest_countries_validation_success():
    valid_data = {
        "name": "Korea (Republic of)",
        "capital": "Seoul",
        "region": "Asia",
        "population": 51780579,
        "flags": {
            "png": "https://flagcdn.com/w320/kr.png",
            "svg": "https://flagcdn.com/kr.svg"
        }
    }
    response = RestCountriesResponse.model_validate(valid_data)
    assert response.name == "Korea (Republic of)"
    assert response.population == 51780579
    assert response.flags.png == "https://flagcdn.com/w320/kr.png"


# 4. RestCountries 스키마 검증 테스트 (실패 케이스: 인구수 음수)
def test_rest_countries_validation_failure():
    invalid_data = {
        "name": "Korea (Republic of)",
        "capital": "Seoul",
        "region": "Asia",
        "population": -12345,  # validator에 의해 ValidationError 유발
        "flags": {
            "png": "https://flagcdn.com/w320/kr.png",
            "svg": "https://flagcdn.com/kr.svg"
        }
    }
    with pytest.raises(ValidationError) as excinfo:
        RestCountriesResponse.model_validate(invalid_data)
    assert "인구 수는 음수일 수 없습니다" in str(excinfo.value)


# 5. Open-Meteo 스키마 검증 테스트 (정상 케이스)
def test_open_meteo_validation_success():
    valid_data = {
        "latitude": 37.5,
        "longitude": 127.0,
        "elevation": 26.0,
        "hourly": {
            "time": ["2026-07-15T00:00", "2026-07-15T01:00"],
            "temperature_2m": [25.5, 26.0],
            "precipitation_probability": [20, 80]
        }
    }
    response = OpenMeteoResponse.model_validate(valid_data)
    assert response.latitude == 37.5
    assert response.hourly.temperature_2m[0] == 25.5
    assert response.hourly.precipitation_probability[1] == 80


# 6. Open-Meteo 스키마 검증 테스트 (실패 케이스: 비현실적인 기온 감지)
def test_open_meteo_validation_temperature_failure():
    invalid_data = {
        "latitude": 37.5,
        "longitude": 127.0,
        "elevation": 26.0,
        "hourly": {
            "time": ["2026-07-15T00:00"],
            "temperature_2m": [99.0],  # validator에 의해 ValidationError 유발
            "precipitation_probability": [0]
        }
    }
    with pytest.raises(ValidationError) as excinfo:
        OpenMeteoResponse.model_validate(invalid_data)
    assert "비현실적인 기온 감지" in str(excinfo.value)
