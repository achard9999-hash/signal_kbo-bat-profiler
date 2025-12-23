import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
import os

# 페이지 설정
st.set_page_config(page_title="KBO Bat Profiler", layout="wide")

# 1. 연도별 경기 수 정의 (규정타석 계산용)
GAMES_PER_YEAR = {
    2025: 144, 2024: 144, 2023: 144, 2022: 144, 2021: 144, 2020: 144, 
    2019: 144, 2018: 144, 2017: 144, 2016: 144, 2015: 144,
    2014: 128, 2013: 128, 2012: 133, 2011: 133, 2010: 133, 
    2009: 133, 2008: 126, 2007: 126, 2006: 126, 2005: 126, 
    2004: 133, 2003: 133, 2002: 133, 2001: 133
}

# 2. 데이터 로드 함수
@st.cache_data
def load_yearly_data(year):
    file_path = f'batters_all_advanced_saber_{year}.csv'
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        if '날짜' in df.columns:
            df['날짜'] = pd.to_datetime(df['날짜'])
        
        # 추가 지표 계산 (IsoP 등)
        if '장타율' in df.columns and '타율' in df.columns:
            df['IsoP'] = df['장타율'] - df['타율']
        
        # K%, BB%, BB/K 계산 (컬럼명이 존재할 경우)
        if '삼진' in df.columns and '타석' in df.columns:
            df['K%'] = (df['삼진'] / df['타석']).replace([np.inf, -np.inf], 0).fillna(0)
        if '볼넷' in df.columns and '타석' in df.columns:
            df['BB%'] = (df['볼넷'] / df['타석']).replace([np.inf, -np.inf], 0).fillna(0)
        if '볼넷' in df.columns and '삼진' in df.columns:
            df['BB/K'] = (df['볼넷'] / df['삼진']).replace([np.inf, -np.inf], 0).fillna(0)
            
        # HR%, PA/HR 계산
        if '홈런' in df.columns and '타석' in df.columns:
            df['HR%'] = (df['홈런'] / df['타석']).replace([np.inf, -np.inf], 0).fillna(0)
            df['PA/HR'] = (df['타석'] / df['홈런']).replace([np.inf, -np.inf], 0).fillna(0)

        return df
    else:
        st.error(f"{year}년 데이터 파일을 찾을 수 없습니다.")
        return None

# --- UI 레이아웃 ---
st.title("⚾ KBO Bat Profiler")
st.markdown("Developed by yyd")

with st.sidebar:
    st.header("설정 (Settings)")
    years = list(range(2025, 2000, -1))
    selected_year = st.selectbox("연도 선택 (Select Year)", years)
    
    df = load_yearly_data(selected_year)
    
    if df is not None:
        teams = sorted(df['팀'].unique())
        selected_team = st.selectbox("팀 선택 (Select Team)", ["ALL Teams"] + teams)
        
        if selected_team != "ALL Teams":
            player_list = sorted(df[df['팀'] == selected_team]['선수명'].unique())
        else:
            player_list = sorted(df['선수명'].unique())
            
        selected_player = st.selectbox("선수 선택 (Select Player)", player_list)
        generate_btn = st.button("생성 (Generate) !")

# --- 메인 로직 ---
if df is not None and 'generate_btn' in locals() and generate_btn:
    # 1. 시즌 최종 데이터 추출
    season_final = df.sort_values('날짜').groupby('선수명').tail(1).copy()
    
    # 2. 규정타석 계산 (해당 연도 경기 수 * 3.1, 소수점 버림)
    total_games = GAMES_PER_YEAR.get(selected_year, 144)
    qualified_pa = int(total_games * 3.1)
    
    # 3. 최소 기준(타석 3 이상) 필터링
    season_final = season_final[season_final['타석'] >= 3]
    
    # 4. 선택 선수 데이터 확보
    player_results = season_final[season_final['선수명'] == selected_player]
    
    if player_results.empty:
        st.warning(f"{selected_player} 선수는 타석 기준 미달로 데이터가 없습니다.")
    else:
        player_data = player_results.iloc[0]
        st.header(f"📊 {selected_player} ({player_data['팀']}) - {selected_year} Season")
        st.write(f"시즌 규정타석: {qualified_pa} PA (현재 {int(player_data['타석'])} PA)")

        # 5. 21개 지표 설정 (7행 3열 구성)
        metrics = [
            ("안타 (H)", "안타"), ("홈런 (HR)", "홈런"), ("고의사구 (IBB)", "고의사구"),
            ("타율 (AVG)", "타율"), ("출루율 (OBP)", "출루율"), ("장타율 (SLG)", "장타율"),
            ("OPS", "OPS"), ("BABIP", "BABIP"), ("SecA", "SecA"),
            ("K%", "K%"), ("BB%", "BB%"), ("BB/K", "BB/K"),
            ("HR%", "HR%"), ("PA/HR", "PA/HR"), ("IsoP", "IsoP"),
            ("RC", "RC"), ("RC/27", "RC/27"), ("XR", "XR"),
            ("wOBA", "wOBA"), ("wRAA", "wRAA"), ("wRC+", "wRC+")
        ]

        # 비율 지표 리스트 (누적 지표 3개 제외)
        rate_metrics = [m[1] for m in metrics[3:]]

        # 6. 시각화 (3열 배치)
        cols = st.columns(3)

        for i, (label, col_name) in enumerate(metrics):
            if col_name in season_final.columns:
                with cols[i % 3]:
                    val = player_data[col_name]
                    all_values = season_final[col_name].dropna()
                    
                    # --- 규정타석 기반 순위 산정 로직 ---
                    if col_name in rate_metrics:
                        # 18개 비율 지표: 규정타석 미달자는 바닥에 배치
                        qualified_mask = season_final['타석'] >= qualified_pa
                        unqualified_mask = ~qualified_mask
                        
                        q_vals = season_final.loc[qualified_mask, col_name].dropna()
                        uq_vals = season_final.loc[unqualified_mask, col_name].dropna()
                        
                        is_player_qualified = player_data['타석'] >= qualified_pa
                        
                        if is_player_qualified:
                            # 규정타석 채운 경우: 규정타석 그룹 내 순위 + 상위 퍼센트
                            rank_val = (q_vals > val).sum() + 1
                            total_for_rank = len(q_vals) + len(uq_vals)
                            # 백분위: 전체 중 (미달자 전원 + 규정타석 내 본인 아래)
                            percentile = ((len(uq_vals) + (q_vals <= val).sum()) / total_for_rank) * 100
                        else:
                            # 미달인 경우: 미달 그룹 내 순위 + 규정타석 채운 사람 뒤로 밀림
                            rank_val = len(q_vals) + (uq_vals > val).sum() + 1
                            total_for_rank = len(q_vals) + len(uq_vals)
                            # 백분위: 전체 중 (미달 그룹 내 본인 아래 사람 수)
                            percentile = ((uq_vals <= val).sum() / total_for_rank) * 100
                    else:
                        # 누적 지표 (안타, 홈런, 고의사구): 기존 방식
                        rank_val = (all_values > val).sum() + 1
                        total_for_rank = len(all_values)
                        percentile = percentileofscore(all_values, val, kind='rank')

                    # 안전장치 및 포맷팅
                    if not np.isfinite(percentile): percentile = 0
                    safe_percentile = int(round(percentile))
                    color = "#e74c3c" if safe_percentile > 50 else "#3498db"
                    
                    if pd.isnull(val): display_val = "N/A"
                    elif col_name in ["안타", "홈런", "고의사구"]: display_val = f"{int(val)}"
                    else: display_val = f"{val:.3f}"
                    
                    rank_text = f"순위: {int(rank_val)}위 / {total_for_rank}명"

                    st.markdown(f"""
                        <div style="margin-bottom: 22px;">
                            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                                <span style="font-weight: bold; font-size: 14px;">{label}</span>
                                <span style="font-size: 14px; cursor: help;" title="{rank_text}">
                                    <b>{display_val}</b>
                                </span>
                            </div>
                            <div style="background-color: #eee; border-radius: 10px; height: 14px; width: 100%;">
                                <div style="background-color: {color}; width: {safe_percentile}%; height: 14px; border-radius: 10px; text-align: right; padding-right: 8px; color: white; font-size: 10px; line-height: 14px;">
                                    {safe_percentile}
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

    st.info("💡 비율 지표(타율~wRC+)는 규정타석 미달 시 하위 순위로 자동 배정됩니다.")

elif df is None:
    st.info("데이터를 로드하는 중입니다...")
else:
    st.write("사이드바에서 연도와 선수를 선택한 후 **Generate** 버튼을 눌러주세요.")
