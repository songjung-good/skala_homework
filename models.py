"""
[종합 실습] 데이터 수집 미니 파이프라인
Pydantic v2 모델을 사용하여 API 요청 결과를 검증하는 코드
작성일: 2026-07-15
작성자: 배영환
변경이력:
  - ver 0.1: Open-Meteo, RestCountries, IP-API 응답 모델 정의
"""
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator


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
