import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import percentileofscore

# 페이지 설정
st.set_page_config(page_title="KBO Bat Profiler", layout="wide")

# 1. 데이터 로드 (캐싱을 통해 속도 향상)
@st.cache_data
def load_data():
    df = pd.read_csv('data/batters_all_advanced_saber.csv')
    # 날짜 형식 변환 및 전처리
    df['날짜'] = pd.to_datetime(df['날짜'])
    return df

df = load_data()

# --- 사이드바 UI ---
st.title("⚾ KBO Bat Profiler")
st.markdown("Developed by Your Name")

with st.sidebar:
    st.header("설정 (Settings)")
    
    # 연도 선택
    years = sorted(df['연도'].unique(), reverse=True)
    selected_year = st.selectbox("연도 선택 (Select Year)", years)
    
    # 해당 연도 팀 리스트
    year_df = df[df['연도'] == selected_year]
    teams = sorted(year_df['팀'].unique())
    selected_team = st.selectbox("팀 선택 (Select Team)", ["ALL Teams"] + teams)
    
    # 선수 선택
    if selected_team != "ALL Teams":
        player_list = sorted(year_df[year_df['팀'] == selected_team]['선수명'].unique())
    else:
        player_list = sorted(year_df['선수명'].unique())
        
    selected_player = st.selectbox("선수 선택 (Select Player)", player_list)
    
    generate_btn = st.button("생성 (Generate) !")

# --- 메인 로직 ---
if generate_btn:
    # 1. 해당 시즌 모든 선수의 '마지막 날짜' 기준 성적 추출
    # 시즌 중 은퇴하거나 말소된 선수도 포함하기 위해 선수별 마지막 기록 추출
    season_final = year_df.sort_values('날짜').groupby('선수명').tail(1)
    
    # 2. 선택한 선수의 데이터 추출
    player_data = season_final[season_final['선수명'] == selected_player].iloc[0]
    
    st.header(f"📊 {selected_player} ({player_data['팀']}) - {selected_year} Season")
    
    # 3. 표시할 주요 지표 리스트
    metrics = {
        "타율 (AVG)": "타율",
        "출루율 (OBP)": "출루율",
        "장타율 (SLG)": "장타율",
        "OPS": "OPS",
        "wOBA": "wOBA",
        "wRC+": "wRC+",
        "BABIP": "BABIP",
        "HR% (홈런율)": "홈런" # 예시로 홈런수 사용, 필요시 계산
    }
    
    # 4. 백분위 시각화 레이아웃 (3열 배치)
    cols = st.columns(3)
    
    for i, (label, col_name) in enumerate(metrics.items()):
        with cols[i % 3]:
            # 전체 선수 중 해당 지표의 값 리스트 (NaN 제외)
            all_values = season_final[col_name].dropna().values
            val = player_data[col_name]
            
            # 백분위 계산 (0~100)
            percentile = percentileofscore(all_values, val, kind='rank')
            
            # 순위 계산
            rank = season_final[col_name].rank(ascending=False, method='min').loc[player_data.name]
            total_players = len(all_values)
            
            # 시각화 바 (NPB 사이트 느낌 재현)
            color = "#e74c3c" if percentile > 50 else "#3498db"
            
            st.markdown(f"""
                <div style="margin-bottom: 20px;">
                    <div style="display: flex; justify-content: space-between;">
                        <span style="font-weight: bold;">{label}</span>
                        <span title="순위: {int(rank)}위 / {total_players}명">{val:.3f}</span>
                    </div>
                    <div style="background-color: #eee; border-radius: 10px; height: 12px; width: 100%;">
                        <div style="background-color: {color}; width: {percentile}%; height: 12px; border-radius: 10px; text-align: right; padding-right: 5px; color: white; font-size: 10px;">
                            {int(percentile)}
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    st.info("💡 지표 값 위에 마우스를 올리면 시즌 전체 순위가 나타납니다.")

else:
    st.write("왼쪽 사이드바에서 선수를 선택하고 '생성' 버튼을 눌러주세요.")
