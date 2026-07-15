"""
[종합 실습] 데이터 수집 미니 파이프라인
API 요청 결과를 검증하고, 에러 발생 시 적절한 메시지를 출력하는 Pydantic v2 모델 정의
작성일: 2026-07-15
작성자: 배영환
변경이력:
  - ver 0.1: API 요청 에러 처리 및 결과 요약 기능 추가
  - ver 0.1.1: REST Countries API(https://restcountries.com/v3.1/alpha/KR > https://countries.dev/alpha/KR) 와 IP-API 요청 시 에러 수정(https -> http)
  - ver 0.2: Pydantic v2 모델 검증 적용 
"""
import asyncio
import httpx
from pydantic import ValidationError
from models import OpenMeteoResponse, RestCountriesResponse, IpApiResponse

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
                    
                    # 검증 완료된 객체의 속성을 간단히 출력하여 확인
                    if name == "Open-Meteo":
                        print(f"    - 위치: 위도 {validated_data.latitude}, 경도 {validated_data.longitude}")
                        print(f"    - 수집된 기온 데이터 수: {len(validated_data.hourly.temperature_2m)}개")
                    elif name == "RestCountries":
                        print(f"    - 국가명: {validated_data.name}, 수도: {validated_data.capital}, 인구수: {validated_data.population}")
                    elif name == "IP-API":
                        print(f"    - 조회된 IP: {validated_data.query} (지역: {validated_data.country}, {validated_data.city})")
                except ValidationError as e:
                    print(f"[{name}] 스키마 검증 실패 (ValidationError 발생):")
                    print(e)
                except Exception as e:
                    print(f"[{name}] 예기치 못한 검증 오류 발생: {e}")


if __name__ == "__main__":
    # 비동기 메인 이벤트 루프 실행
    asyncio.run(main())
