"""
etl.py
------
Extract - Transform - Load 파이프라인.

1. Pandas / Polars 로 동일 데이터를 각각 로드하여 속도·메모리 사용량을 비교한다.
   (Polars 가 설치되어 있지 않은 실행 환경에서는 비교를 건너뛰고 경고만 남긴다.)
2. 결측치 처리, 중복 제거, 이상치 처리를 수행한다.
3. 분석용 파생 변수를 생성한다 (AI 사용 여부 이진화, JobSat 숫자화, 연봉 로그 변환 등).
4. 정제된 데이터를 data/processed/ 에 저장한다.
"""

import os
import time
import tracemalloc
import urllib.request

import numpy as np
import pandas as pd

from src.utils import (
    RAW_CSV_PATH,
    PROCESSED_CSV_PATH,
    ANALYSIS_COLS,
    TARGET_SALARY_USD,
    TARGET_SALARY_RAW,
    TARGET_JOBSAT,
    get_logger,
)

DATA_URL = "https://github.com/StackExchange/Survey/raw/refs/heads/main/packages/archive/2024/results.csv"


logger = get_logger(__name__)

# YearsCodePro / YearsCode 텍스트 응답을 숫자로 매핑
_YEARS_TEXT_MAP = {
    "Less than 1 year": 0.5,
    "More than 50 years": 51,
}


def _years_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.replace(_YEARS_TEXT_MAP), errors="coerce")


# ------------------------------------------------------------------
# 1. Pandas vs Polars 로드 비교
# ------------------------------------------------------------------
def compare_pandas_polars(path=RAW_CSV_PATH) -> dict:
    """동일 CSV 를 Pandas / Polars 로 각각 로드하여 속도·메모리를 비교한다."""
    result = {}

    tracemalloc.start()
    t0 = time.perf_counter()
    df_pd = pd.read_csv(path, low_memory=False)
    pd_time = time.perf_counter() - t0
    _, pd_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result["pandas"] = {
        "load_time_sec": round(pd_time, 4),
        "peak_memory_mb": round(pd_peak / (1024 ** 2), 2),
        "rows": len(df_pd),
        "cols": df_pd.shape[1],
    }

    try:
        import polars as pl

        tracemalloc.start()
        t0 = time.perf_counter()
        df_pl = pl.read_csv(path, infer_schema_length=10000)
        pl_time = time.perf_counter() - t0
        _, pl_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        result["polars"] = {
            "load_time_sec": round(pl_time, 4),
            "peak_memory_mb": round(pl_peak / (1024 ** 2), 2),
            "rows": df_pl.shape[0],
            "cols": df_pl.shape[1],
        }
    except ImportError:
        logger.warning(
            "polars 가 설치되어 있지 않아 비교를 건너뜁니다. "
            "`pip install polars` 후 재실행하면 비교 결과가 report.md 에 포함됩니다."
        )
        result["polars"] = None

    return result, df_pd


# ------------------------------------------------------------------
# 2. 결측치 / 중복 / 이상치 처리
# ------------------------------------------------------------------
def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {"raw_rows": len(df)}

    # 분석에 필요한 컬럼만 우선 추림
    cols = [c for c in ANALYSIS_COLS if c in df.columns]
    df = df[cols].copy()

    # 중복 제거
    before = len(df)
    df = df.drop_duplicates()
    stats["duplicates_removed"] = before - len(df)

    # 결측치 현황 기록 (핵심 변수 기준)
    key_cols = ["AISelect", TARGET_SALARY_USD, TARGET_JOBSAT, "YearsCodePro"]
    stats["missing_before"] = {c: int(df[c].isna().sum()) for c in key_cols if c in df.columns}

    # YearsCodePro 숫자화
    if "YearsCodePro" in df.columns:
        df["YearsCodePro"] = _years_to_numeric(df["YearsCodePro"])

    # AISelect 결측 제거 (AI 사용 여부가 핵심 독립변수이므로 결측 응답 제외)
    df = df[df["AISelect"].notna()]

    # 연봉(ConvertedCompYearly, USD 환산) 이상치 처리
    #   - 국가별 통화가 제각각인 CompTotal 대신, SO 가 USD 로 표준화한 ConvertedCompYearly 사용
    #   - 0 이하 값은 먼저 결측(NaN) 처리한 뒤, 남은 값만 1~99 퍼센타일 winsorize(클리핑)로 극단치 완화
    #     (주의: clip(lower=low)를 0 이하 값에 그대로 적용하면 low>0 이므로 값이 삭제되지 않고
    #      low 로 끌어올려지는 버그가 발생한다. 따라서 클리핑 전에 0 이하 값을 NaN 으로 분리한다.)
    if TARGET_SALARY_USD in df.columns:
        sal = df[TARGET_SALARY_USD]
        stats["salary_missing_usd"] = int(sal.isna().sum())
        sal = sal.where(sal.isna() | (sal > 0))  # 0 이하 값 -> NaN
        valid = sal.dropna()
        if len(valid) > 0:
            low, high = valid.quantile(0.01), valid.quantile(0.99)
            stats["salary_clip_bounds"] = (float(low), float(high))
            df[TARGET_SALARY_USD] = sal.clip(lower=low, upper=high)
        else:
            df[TARGET_SALARY_USD] = sal

    stats["rows_after_clean"] = len(df)
    return df, stats


# ------------------------------------------------------------------
# 3. 파생 변수 생성
# ------------------------------------------------------------------
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # AI 사용 여부 이진 변수 (Yes -> 1, 그 외 -> 0)
    df["AI_User"] = (df["AISelect"] == "Yes").astype(int)
    df["AISelect_clean"] = df["AISelect"].replace(
        {
            "No, and I don't plan to": "No",
            "No, but I plan to soon": "No (plan to)",
        }
    )

    # 연봉 로그 변환 (오른쪽 꼬리가 긴 분포 완화)
    if TARGET_SALARY_USD in df.columns:
        df["Salary_log"] = np.log1p(df[TARGET_SALARY_USD])

    # JobSat 은 이미 0~10 숫자이므로 형변환만 수행
    if TARGET_JOBSAT in df.columns:
        df[TARGET_JOBSAT] = pd.to_numeric(df[TARGET_JOBSAT], errors="coerce")

    return df


# ------------------------------------------------------------------
# 4. 파이프라인 엔트리 포인트
# ------------------------------------------------------------------
def download_raw_csv(url: str, dest_path: str):
    """지정된 URL에서 raw CSV 데이터를 다운로드하여 저장합니다."""
    logger.info("Raw CSV 파일이 존재하지 않아 다운로드를 시작합니다: %s", url)
    dest_dir = os.path.dirname(dest_path)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    headers = {"User-Agent": "Mozilla/5.0"}
    req = urllib.request.Request(url, headers=headers)

    try:
        t0 = time.perf_counter()
        with urllib.request.urlopen(req) as response, open(dest_path, "wb") as out_file:
            content_length = response.getheader("Content-Length")
            total_size = int(content_length) if content_length else None
            
            downloaded = 0
            block_size = 1024 * 1024  # 1MB
            last_reported = time.perf_counter()
            
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                
                now = time.perf_counter()
                if now - last_reported > 5:
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        logger.info("다운로드 중: %.1f MB / %.1f MB (%.1f%%)", 
                                    downloaded / (1024**2), total_size / (1024**2), percent)
                    else:
                        logger.info("다운로드 중: %.1f MB", downloaded / (1024**2))
                    last_reported = now
                    
        elapsed = time.perf_counter() - t0
        logger.info("다운로드 완료: %s (소요 시간: %.2f초, 크기: %.1f MB)", 
                    dest_path, elapsed, downloaded / (1024**2))
    except Exception as e:
        logger.error("다운로드 실패: %s", e)
        if os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        raise e


def run_etl() -> tuple[pd.DataFrame, dict]:
    logger.info("ETL 시작: %s", RAW_CSV_PATH)

    if not RAW_CSV_PATH.exists():
        download_raw_csv(DATA_URL, str(RAW_CSV_PATH))

    load_comparison, df_raw = compare_pandas_polars()
    logger.info("Pandas 로드: %s", load_comparison["pandas"])
    if load_comparison["polars"]:
        logger.info("Polars 로드: %s", load_comparison["polars"])

    df_clean, clean_stats = clean_data(df_raw)
    logger.info("정제 결과: %s", clean_stats)

    df_final = engineer_features(df_clean)

    df_final.to_csv(PROCESSED_CSV_PATH, index=False)
    logger.info("정제 데이터 저장 완료: %s (%d행)", PROCESSED_CSV_PATH, len(df_final))

    etl_report = {
        "load_comparison": load_comparison,
        "clean_stats": clean_stats,
        "final_rows": len(df_final),
        "final_cols": df_final.shape[1],
    }
    return df_final, etl_report


if __name__ == "__main__":
    run_etl()
