"""
[종합 실습] 데이터 수집 미니 파이프라인
API 요청 결과를 검증하고, 에러 발생 시 적절한 메시지를 출력하는 Pydantic v2 모델 정의
작성일: 2026-07-15
작성자: 배영환
변경이력:
  - ver 0.1: API 요청 에러 처리 및 결과 요약 기능 추가
  - ver 0.1.1: REST Countries API(https://restcountries.com/v3.1/alpha/KR > https://countries.dev/alpha/KR) 와 IP-API 요청 시 에러 수정(https -> http)
  - ver 0.2: Pydantic v2 모델 검증 적용 
  - ver 0.3: CSV/Parquet 저장 및 로드 성능 비교 기능 추가
"""

import asyncio
import httpx
import os
import time
import pandas as pd
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator

# ==============================================================================
# [Pydantic v2 데이터 검증 모델 정의]
# ==============================================================================

# 1. Open-Meteo 데이터 검증 모델
class HourlyData(BaseModel):
    time: List[str] = Field(description="시간대 목록")
    temperature_2m: List[float] = Field(description="기온 목록")
    precipitation_probability: List[int] = Field(description="강수확률 목록")

    @field_validator("temperature_2m")
    @classmethod
    def validate_temperatures(cls, v: List[float]) -> List[float]:
        # 기온이 지나치게 비현실적인 값인지 검증 (-80도 ~ 60도 범위)
        for temp in v:
            if not (-80.0 <= temp <= 60.0):
                raise ValueError(f"비현실적인 기온 감지: {temp}°C")
        return v

    @field_validator("precipitation_probability")
    @classmethod
    def validate_precipitation(cls, v: List[int]) -> List[int]:
        # 강수확률은 0%에서 100% 사이여야 함
        for prob in v:
            if not (0 <= prob <= 100):
                raise ValueError(f"비현실적인 강수확률 감지: {prob}%")
        return v


class OpenMeteoResponse(BaseModel):
    latitude: float = Field(description="위도")
    longitude: float = Field(description="경도")
    elevation: float = Field(description="고도")
    hourly: HourlyData = Field(description="시간별 데이터")


# 2. RestCountries (countries.dev) 데이터 검증 모델
class FlagData(BaseModel):
    png: str = Field(description="PNG 국기 이미지 URL")
    svg: str = Field(description="SVG 국기 이미지 URL")


class RestCountriesResponse(BaseModel):
    name: str = Field(description="국가명")
    capital: Optional[str] = Field(default="", description="수도명")
    region: str = Field(description="대륙 지역")
    population: int = Field(description="인구 수")
    flags: FlagData = Field(description="국기 데이터")

    @field_validator("population")
    @classmethod
    def validate_population(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"인구 수는 음수일 수 없습니다: {v}")
        return v


# 3. IP-API 데이터 검증 모델
class IpApiResponse(BaseModel):
    status: str = Field(description="요청 결과 상태 (success/fail)")
    country: str = Field(description="국가명")
    city: str = Field(description="도시명")
    lat: float = Field(description="위도")
    lon: float = Field(description="경도")
    query: str = Field(description="조회된 IP 주소")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v != "success":
            raise ValueError(f"IP 조회 API가 실패 응답을 반환했습니다: status={v}")
        return v

# ==============================================================================
# [API 요청 및 데이터 수집/검증/저장 파이프라인]
# ==============================================================================

# API Endpoints 정의
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast?latitude=37.5665&longitude=126.9780&hourly=temperature_2m,precipitation_probability&forecast_days=3&timezone=Asia/Seoul"
REST_COUNTRIES_URL = "https://countries.dev/alpha/KR"
IP_API_URL = "http://ip-api.com/json/8.8.8.8"


async def fetch_data(client: httpx.AsyncClient, name: str, url: str) -> dict:
    """
    지정한 API URL로 비동기 GET 요청을 보내고 JSON 데이터를 반환
    
    Args:
        client (httpx.AsyncClient): HTTP 비동기 클라이언트 객체
        name (str): 로그 식별을 위한 API 이름
        url (str): API 요청 대상 URL
        
    Returns:
        dict: API 응답 JSON 데이터
    """
    print(f"[{name}] API 요청 시작...")
    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        print(f"[{name}] API 요청 성공!")
        return response.json()
    # HTTP 에러가 발생한 경우 (예: 4xx, 5xx)    
    except httpx.HTTPStatusError as e:
        print(f"[{name}] HTTP 에러 발생: {e.response.status_code}")
        raise
    except httpx.RequestError as e:
        print(f"[{name}] 네트워크/요청 에러 발생: {e}")
        raise
    except Exception as e:
        print(f"[{name}] 알 수 없는 에러 발생: {e}")
        raise


def save_and_benchmark(df: pd.DataFrame):
    """
    DataFrame을 CSV와 Parquet 형식으로 저장 및 로드하여 
    각각의 수행 시간과 파일 크기를 비교하고 벤치마크 결과를 출력합니다.
    """
    print("\n=== 데이터 저장 및 성능 비교 (Benchmark) ===")
    
    csv_path = "collected_data.csv"
    parquet_path = "collected_data.parquet"
    
    # 매번 측정 시점마다 time.perf_counter()를 호출하여 정확한 시간 측정
    # 1. CSV 쓰기 성능 측정
    start_time = time.perf_counter()
    df.to_csv(csv_path, index=False)
    csv_write_time = time.perf_counter() - start_time
    
    # 2. Parquet 쓰기 성능 측정
    start_time = time.perf_counter()
    df.to_parquet(parquet_path, index=False)
    parquet_write_time = time.perf_counter() - start_time
    
    # 3. CSV 읽기 성능 측정
    start_time = time.perf_counter()
    pd.read_csv(csv_path)
    csv_read_time = time.perf_counter() - start_time
    
    # 4. Parquet 읽기 성능 측정
    start_time = time.perf_counter()
    pd.read_parquet(parquet_path)
    parquet_read_time = time.perf_counter() - start_time
    
    # 파일 크기 측정
    csv_size = os.path.getsize(csv_path) / 1024  # KB
    parquet_size = os.path.getsize(parquet_path) / 1024  # KB
    
    # 결과 출력
    print(f"{'포맷':<10} | {'쓰기 속도(s)':<12} | {'읽기 속도(s)':<12} | {'파일 크기(KB)':<12}")
    print("-" * 59)
    print(f"{'CSV':<10} | {csv_write_time:.6f} | {csv_read_time:.6f} | {csv_size:.2f} KB")
    print(f"{'Parquet':<10} | {parquet_write_time:.6f} | {parquet_read_time:.6f} | {parquet_size:.2f} KB")
    print("-" * 59)
    print("※ 데이터 규모가 작아 측정 오차가 발생할 수 있습니다.")


async def main():
    # httpx.AsyncClient를 컨텍스트 매니저로 사용하여 리소스 누수를 방지
    # 301 리디렉션 대응을 위해 follow_redirects=True 옵션을 적용
    async with httpx.AsyncClient(follow_redirects=True) as client:
        print("=== 비동기 API 수집 파이프라인 시작 ===")
        
        # asyncio.gather를 활용하여 3개의 API를 동시에 병렬 수집
        # return_exceptions=True 설정으로 하나의 실패가 전체 실패로 이어지지 않게 처리
        results = await asyncio.gather(
            fetch_data(client, "Open-Meteo", OPEN_METEO_URL),
            fetch_data(client, "RestCountries", REST_COUNTRIES_URL),
            fetch_data(client, "IP-API", IP_API_URL),
            return_exceptions=True
        )
        
        print("\n=== 수집 완료 및 결과 요약 ===")
        names = ["Open-Meteo", "RestCountries", "IP-API"]
        
        # 각 API에 대응하는 Pydantic 모델 매핑
        model_mapping = {
            "Open-Meteo": OpenMeteoResponse,
            "RestCountries": RestCountriesResponse,
            "IP-API": IpApiResponse
        }

        # 검증 통과된 데이터를 보관하기 위한 임시 변수
        validated_open_meteo = None
        validated_rest_countries = None
        validated_ip_api = None

        for name, result in zip(names, results):
            if isinstance(result, Exception):
                print(f"[{name}] 수집 단계 실패: {result}")
                continue

            model_class = model_mapping.get(name)
            if model_class:
                try:
                    # Pydantic v2 validation 수행
                    validated_data = model_class.model_validate(result)
                    print(f"[{name}] 데이터 검증 통과!")
                    
                    # 검증 완료된 객체의 속성을 변수에 바인딩
                    if name == "Open-Meteo":
                        validated_open_meteo = validated_data
                        # print(f"    - 위치: 위도 {validated_data.latitude}, 경도 {validated_data.longitude}")
                        # print(f"    - 수집된 기온 데이터 수: {len(validated_data.hourly.temperature_2m)}개")
                    elif name == "RestCountries":
                        validated_rest_countries = validated_data
                        # print(f"    - 국가명: {validated_data.name}, 수도: {validated_data.capital}, 인구수: {validated_data.population}")
                    elif name == "IP-API":
                        validated_ip_api = validated_data
                        # print(f"    - 조회된 IP: {validated_data.query} (지역: {validated_data.country}, {validated_data.city})")
                except ValidationError as e:
                    print(f"[{name}] 스키마 검증 실패 (ValidationError 발생):")
                    print(e)
                except Exception as e:
                    print(f"[{name}] 예기치 못한 검증 오류 발생: {e}")

        # 3가지 데이터가 모두 정상 검증된 경우 Pandas DataFrame 구축 및 저장 성능 비교
        if validated_open_meteo and validated_rest_countries and validated_ip_api:
            # 1. Open-Meteo 시간별 데이터를 기반으로 기본 DataFrame 생성
            df = pd.DataFrame({
                "time": validated_open_meteo.hourly.time,
                "temperature_2m": validated_open_meteo.hourly.temperature_2m,
                "precipitation_probability": validated_open_meteo.hourly.precipitation_probability
            })
            
            # 2. RestCountries 및 IP-API 데이터의 단일 값을 모든 행에 복제하여 추가
            df["country_name"] = validated_rest_countries.name
            df["country_capital"] = validated_rest_countries.capital
            df["country_population"] = validated_rest_countries.population
            df["ip_query"] = validated_ip_api.query
            df["ip_country"] = validated_ip_api.country
            df["ip_city"] = validated_ip_api.city
            df["ip_latitude"] = validated_ip_api.lat
            df["ip_longitude"] = validated_ip_api.lon
            
            # 3. 벤치마크 수행
            save_and_benchmark(df)
        else:
            print("\n[오류] 일부 API의 수집 또는 검증이 실패하여 데이터 저장을 진행할 수 없습니다.")

if __name__ == "__main__":
    # 비동기 메인 이벤트 루프 실행
    asyncio.run(main())
