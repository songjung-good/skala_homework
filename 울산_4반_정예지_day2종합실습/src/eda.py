"""
eda.py
------
탐색적 데이터 분석(EDA).

- 기술통계 (평균/중앙값/표준편차/분위수)
- Seaborn 정적 시각화 (AI 사용 여부별 연봉 Boxplot, 만족도 Violin plot, 상관관계 Heatmap)
- Plotly 인터랙티브 시각화 (국가별 AI 사용률 Bar, AI 사용 여부별 연봉 분포 Histogram)
  -> plotly 미설치 환경에서는 matplotlib 으로 동일한 정보를 대체 시각화하고 로그로 안내한다.
- Pearson 상관관계 Heatmap
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.utils import FIGURES_DIR, TARGET_SALARY_USD, TARGET_JOBSAT, get_logger, setup_korean_font

logger = get_logger(__name__)
sns.set_theme(style="whitegrid")

# 한글 폰트 설정 (그래프 내 한글 라벨 깨짐 방지)
# 하드코딩된 폰트명은 실행 환경(OS)에 따라 없는 경우 한글이 네모(□)로 깨지므로,
# 시스템에 실제 설치된 한글 폰트를 자동 탐색해 적용한다 (src/utils.py 참고).
KOREAN_FONT_USED = setup_korean_font()


def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    cols = [c for c in [TARGET_SALARY_USD, "Salary_log", TARGET_JOBSAT, "YearsCodePro", "WorkExp"] if c in df.columns]
    desc = df[cols].describe().T
    desc["median"] = df[cols].median()
    logger.info("기술통계 산출 완료 (%d개 변수)", len(cols))
    return desc


def plot_salary_boxplot_seaborn(df: pd.DataFrame) -> str:
    """AI 사용 여부별 연봉 Boxplot (Seaborn, 정적 이미지)."""
    plot_df = df.dropna(subset=[TARGET_SALARY_USD, "AISelect_clean"])
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.boxplot(data=plot_df, x="AISelect_clean", y=TARGET_SALARY_USD, ax=ax, hue="AISelect_clean", legend=False)
    ax.set_title("AI 도구 사용 여부별 연봉(USD) 분포", fontsize=14)
    ax.set_xlabel("AI 도구 사용 여부")
    ax.set_ylabel("연 환산 연봉 (USD)")
    fig.tight_layout()
    out_path = FIGURES_DIR / "salary_by_ai_boxplot.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info("저장: %s", out_path)
    return str(out_path)


def plot_jobsat_violin_seaborn(df: pd.DataFrame) -> str:
    """AI 사용 여부별 직무 만족도 Violin plot (Seaborn, 정적 이미지)."""
    plot_df = df.dropna(subset=[TARGET_JOBSAT, "AISelect_clean"])
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.violinplot(data=plot_df, x="AISelect_clean", y=TARGET_JOBSAT, ax=ax, hue="AISelect_clean", legend=False)
    ax.set_title("AI 도구 사용 여부별 직무 만족도(JobSat) 분포", fontsize=14)
    ax.set_xlabel("AI 도구 사용 여부")
    ax.set_ylabel("직무 만족도 (0~10)")
    fig.tight_layout()
    out_path = FIGURES_DIR / "jobsat_by_ai_violin.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info("저장: %s", out_path)
    return str(out_path)


def plot_correlation_heatmap(df: pd.DataFrame) -> str:
    cols = [c for c in [TARGET_SALARY_USD, "YearsCodePro", TARGET_JOBSAT, "AI_User", "WorkExp"] if c in df.columns]
    corr = df[cols].corr(method="pearson")
    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Pearson 상관관계 Heatmap", fontsize=14)
    fig.tight_layout()
    out_path = FIGURES_DIR / "correlation_heatmap.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    logger.info("저장: %s", out_path)
    return str(out_path), corr


def plot_interactive_country_ai_rate(df: pd.DataFrame) -> str:
    """국가별 AI 사용률 (Plotly interactive; 미설치 시 matplotlib bar 로 대체)."""
    rate = (
        df.dropna(subset=["Country"])
        .groupby("Country")["AI_User"]
        .agg(["mean", "count"])
        .query("count >= 3")
        .sort_values("mean", ascending=False)
        .head(15)
        .reset_index()
    )
    rate["mean"] = (rate["mean"] * 100).round(1)

    try:
        import plotly.express as px

        fig = px.bar(
            rate,
            x="Country",
            y="mean",
            title="국가별 AI 도구 사용률 (상위 15개국, 응답 3건 이상)",
            labels={"mean": "AI 사용률 (%)", "Country": "국가"},
            hover_data=["count"],
        )
        fig.update_layout(xaxis_tickangle=-45)
        out_path = FIGURES_DIR / "country_ai_rate_interactive.html"
        fig.write_html(out_path, include_plotlyjs="cdn")
        logger.info("저장 (Plotly interactive): %s", out_path)
        return str(out_path)
    except ImportError:
        logger.warning("plotly 미설치 -> matplotlib 정적 이미지로 대체합니다. (`pip install plotly` 권장)")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(data=rate, x="Country", y="mean", ax=ax, hue="Country", legend=False)
        ax.set_title("국가별 AI 도구 사용률 (상위 15개국, 응답 3건 이상) - plotly 대체본")
        ax.set_ylabel("AI 사용률 (%)")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        out_path = FIGURES_DIR / "country_ai_rate_interactive_fallback.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return str(out_path)


def plot_interactive_salary_histogram(df: pd.DataFrame) -> str:
    """연봉 분포 Histogram (Plotly interactive; 미설치 시 matplotlib 대체)."""
    plot_df = df.dropna(subset=[TARGET_SALARY_USD, "AISelect_clean"])
    try:
        import plotly.express as px

        fig = px.histogram(
            plot_df,
            x=TARGET_SALARY_USD,
            color="AISelect_clean",
            barmode="overlay",
            opacity=0.6,
            nbins=40,
            title="AI 사용 여부에 따른 연봉(USD) 분포",
            labels={TARGET_SALARY_USD: "연 환산 연봉 (USD)"},
        )
        out_path = FIGURES_DIR / "salary_histogram_interactive.html"
        fig.write_html(out_path, include_plotlyjs="cdn")
        logger.info("저장 (Plotly interactive): %s", out_path)
        return str(out_path)
    except ImportError:
        logger.warning("plotly 미설치 -> matplotlib 정적 이미지로 대체합니다.")
        fig, ax = plt.subplots(figsize=(9, 6))
        for label, sub in plot_df.groupby("AISelect_clean"):
            ax.hist(sub[TARGET_SALARY_USD], bins=40, alpha=0.5, label=label)
        ax.set_title("AI 사용 여부에 따른 연봉(USD) 분포 - plotly 대체본")
        ax.set_xlabel("연 환산 연봉 (USD)")
        ax.legend()
        fig.tight_layout()
        out_path = FIGURES_DIR / "salary_histogram_interactive_fallback.png"
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        return str(out_path)


def run_eda(df: pd.DataFrame) -> dict:
    logger.info("EDA 시작")
    desc = descriptive_stats(df)
    box_path = plot_salary_boxplot_seaborn(df)
    violin_path = plot_jobsat_violin_seaborn(df)
    heatmap_path, corr = plot_correlation_heatmap(df)
    country_path = plot_interactive_country_ai_rate(df)
    hist_path = plot_interactive_salary_histogram(df)

    return {
        "descriptive_stats": desc,
        "correlation": corr,
        "figures": {
            "salary_boxplot": box_path,
            "jobsat_violin": violin_path,
            "correlation_heatmap": heatmap_path,
            "country_ai_rate": country_path,
            "salary_histogram": hist_path,
        },
        "korean_font": KOREAN_FONT_USED,
    }


if __name__ == "__main__":
    from src.etl import run_etl

    df, _ = run_etl()
    run_eda(df)
