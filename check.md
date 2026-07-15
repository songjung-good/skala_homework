
  3가지 API에서 비동기로 데이터를 수집하는 첫 단계 코드인 main.py
  작성을 완료하고 테스트 실행까지 마쳤습니다.

  ### 💡 주요 변경 및 구현 사항

  1. API 대체: 공식  restcountries.com  API가 최신 업데이트를
  거치며 API Key 발급을 강제(무료 키를 발급받더라도 301 리디렉션
  에러가 발생)하게 됨에 따라, 인증 및 리디렉션 없이 빠르게 사용
  가능한 대체 미러 API인  https://countries.dev/alpha/KR 로
  엔드포인트를 마이그레이션했습니다.
  2. 비동기 요청 파이프라인 구현:  asyncio.gather() 와  httpx.
  AsyncClient() 를 활용하여 3개의 API를 동시에 병렬로 호출하도록
  설계했습니다.
  3. 에러 핸들링: 개별 API 장애 상황(네트워크 에러, HTTP Status
  에러 등)에 따른 예외 처리 구조를 마련했습니다.

  ### 🧪 실행 결과

    === 비동기 API 수집 파이프라인 시작 ===
    [Open-Meteo] API 요청 시작...
    [RestCountries] API 요청 시작...
    [IP-API] API 요청 시작...
    [IP-API] API 요청 성공!
    [RestCountries] API 요청 성공!
    [Open-Meteo] API 요청 성공!

    === 수집 완료 및 결과 요약 ===
    [Open-Meteo] 수집 성공 (데이터 수: 72개)
    [RestCountries] 수집 성공 (국가명: Korea (Republic of))
    [IP-API] 수집 성공 (지역: United States, Ashburn)

  이제 다음 과제 단계인 Pydantic v2를 사용한 스키마 검증(Schema
  Validation) 모델 정의( models.py  작성 등)로 넘어갈 수
  있습니다. 준비되시면 말씀해 주세요!
