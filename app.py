import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import percentileofscore
import os

# 페이지 설정
st.set_page_config(page_title="KBO Bat Profiler", layout="wide")

# 1. 데이터 로드 함수 (분할된 파일명 규칙에 맞게 수정)
@st.cache_data
def load_yearly_data(year):
    # 파일명이 루트(최상단)에 있으므로 경로 수정
    file_path = f'batters_all_advanced_saber_{year}.csv'
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        # 날짜 형식 변환
        if '날짜' in df.columns:
            df['날짜'] = pd.to_datetime(df['날짜'])
        return df
    else:
        st.error(f"{year}년 데이터 파일을 찾을 수 없습니다.")
        return None

# --- UI 레이아웃 ---
st.title("⚾ KBO Bat Profiler")
st.markdown("Developed by Byeongwoo")

# 사이드바 설정
with st.sidebar:
    st.header("설정 (Settings)")
    
    # 2001~2025 연도 선택
    years = list(range(2025, 2000, -1))
    selected_year = st.selectbox("연도 선택 (Select Year)", years)
    
    # 선택된 연도 데이터 로드
    df = load_yearly_data(selected_year)
    
    if df is not None:
        # 팀 선택
        teams = sorted(df['팀'].unique())
        selected_team = st.selectbox("팀 선택 (Select Team)", ["ALL Teams"] + teams)
        
        # 선수 선택
        if selected_team != "ALL Teams":
            player_list = sorted(df[df['팀'] == selected_team]['선수명'].unique())
        else:
            player_list = sorted(df['선수명'].unique())
            
        selected_player = st.selectbox("선수 선택 (Select Player)", player_list)
        generate_btn = st.button("생성 (Generate) !")

# --- 메인 로직 ---
if df is not None and 'generate_btn' in locals() and generate_btn:
    # 1. 해당 시즌 모든 선수의 '마지막 기록' 추출 (백분위 기준)
    # 날짜 기준 정렬 후 가장 마지막 행만 남김
    season_final = df.sort_values('날짜').groupby('선수명').tail(1)
    
    # 2. 선택한 선수의 최종 성적
    player_data = season_final[season_final['선수명'] == selected_player].iloc[0]
    
    st.header(f"📊 {selected_player} ({player_data['팀']}) - {selected_year} Season")
    
    # 3. 요청하신 13가지 핵심 지표 설정
    metrics = {
        "안타 (H)": "안타",
        "홈런 (HR)": "홈런",
        "고의사구 (IBB)": "고의사구",
        "타율 (AVG)": "타율",
        "출루율 (OBP)": "출루율",
        "장타율 (SLG)": "장타율",
        "OPS": "OPS",
        "BABIP": "BABIP",
        "SecA": "SecA",
        "RC": "RC",
        "wOBA": "wOBA",
        "wRAA": "wRAA",
        "wRC+": "wRC+"
    }
    
    # 4. 시각화 (3열 배치)
    cols = st.columns(3)
    
    for i, (label, col_name) in enumerate(metrics.items()):
        if col_name in season_final.columns:
            with cols[i % 3]:
                all_values = season_final[col_name].dropna().values
                val = player_data[col_name]
                
                # 백분위 (높을수록 좋음)
                percentile = percentileofscore(all_values, val, kind='rank')
                
                # 순위 (내림차순 정렬 기준)
                rank = season_final[col_name].rank(ascending=False, method='min').loc[player_data.name]
                total_players = len(all_values)
                
                # 색상 결정 (백분위 50 기준)
                color = "#e74c3c" if percentile > 50 else "#3498db"
                
                # 수치 포맷팅 (정수/실수 구분)
                display_val = f"{val:.3f}" if isinstance(val, float) else f"{int(val)}"
                
                st.markdown(f"""
                    <div style="margin-bottom: 22px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                            <span style="font-weight: bold; font-size: 14px;">{label}</span>
                            <span style="font-size: 14px; cursor: help;" title="순위: {int(rank)}위 / {total_players}명">
                                <b>{display_val}</b>
                            </span>
                        </div>
                        <div style="background-color: #eee; border-radius: 10px; height: 14px; width: 100%;">
                            <div style="background-color: {color}; width: {percentile}%; height: 14px; border-radius: 10px; text-align: right; padding-right: 8px; color: white; font-size: 10px; line-height: 14px;">
                                {int(percentile)}
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
    
    st.info("💡 수치(숫자) 위에 마우스를 올리면 시즌 전체 순위가 나타납니다.")

elif df is None:
    st.info("데이터를 불러오는 중입니다...")
else:
    st.write("왼쪽 설정창에서 연도와 선수를 선택한 후 **Generate**를 눌러주세요.")
