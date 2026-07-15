"""
[종합 실습] 데이터 수집 미니 파이프라인
작성일: 2026-07-15
작성자: 배영환
변경이력:
  - ver 0.1: API 요청 에러 처리 및 결과 요약 기능 추가
  - ver 0.1.1: REST Countries API(https://restcountries.com/v3.1/alpha/KR > https://countries.dev/alpha/KR) 와 IP-API 요청 시 에러 수정(https -> http)
"""
import asyncio
import httpx

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
        
        for name, result in zip(names, results):
            if isinstance(result, Exception):
                print(f"[{name}] 수집 실패: {result}")
            else:
                # 응답 형태에 따른 결과 데이터 요약 출력
                if name == "Open-Meteo":
                    # 기온 정보 일부(처음 5개 시간대) 예시 출력
                    hourly_times = result.get("hourly", {}).get("time", [])[:5]
                    hourly_temps = result.get("hourly", {}).get("temperature_2m", [])[:5]
                    print(f"[{name}] 수집 성공 (데이터 수: {len(result.get('hourly', {}).get('time', []))}개)")
                    print(f"    - 샘플 데이터: {list(zip(hourly_times, hourly_temps))}")
                elif name == "RestCountries":
                    # 국가의 공식 이름 예시 출력
                    country_name = result.get("name", "N/A") if isinstance(result, dict) else "N/A"
                    print(f"[{name}] 수집 성공 (국가명: {country_name})")
                elif name == "IP-API":
                    # 국가 및 도시 정보 예시 출력
                    country = result.get("country", "N/A")
                    city = result.get("city", "N/A")
                    print(f"[{name}] 수집 성공 (지역: {country}, {city})")


if __name__ == "__main__":
    # 비동기 메인 이벤트 루프 실행
    asyncio.run(main())
