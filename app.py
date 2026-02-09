import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import random
from openai import OpenAI

# -----------------------------------------------------------------------------
# 1. 기본 설정 (Page Config & Session State)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI 습관 트래커", page_icon="📊", layout="wide")

# 세션 상태 초기화 (기록 저장용)
if 'history' not in st.session_state:
    # 데모용 6일 샘플 데이터 생성
    today = datetime.now().date()
    sample_data = []
    for i in range(6, 0, -1):
        date = today - timedelta(days=i)
        sample_data.append({
            "날짜": date.strftime("%Y-%m-%d"),
            "달성률": random.randint(20, 100),
            "기분": random.randint(3, 9)
        })
    st.session_state['history'] = sample_data

# -----------------------------------------------------------------------------
# 2. 사이드바 (API Key 입력)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설정")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    weather_api_key = st.text_input("OpenWeatherMap API Key", type="password")
    st.markdown("---")
    st.info("💡 API 키가 있어야 리포트 생성이 가능합니다.")

# -----------------------------------------------------------------------------
# 3. 메인 타이틀 및 UI 구성
# -----------------------------------------------------------------------------
st.title("📊 AI 습관 트래커")
st.markdown("매일의 작은 습관이 미래를 만듭니다. AI 코치와 함께 성장하세요!")

col_ui, col_chart = st.columns([1, 1])

# --- 왼쪽 컬럼: 습관 체크인 UI ---
with col_ui:
    st.subheader("📝 오늘의 체크인")
    
    # 습관 리스트
    habits = [
        ("🌅 기상 미션", "mission_morning"),
        ("💧 물 마시기", "drink_water"),
        ("📚 공부/독서", "study_read"),
        ("💪 운동하기", "workout"),
        ("💤 수면", "sleep_well")
    ]
    
    # 체크박스 2열 배치
    checked_habits = []
    habit_cols = st.columns(2)
    
    for i, (label, key) in enumerate(habits):
        col_idx = i % 2
        with habit_cols[col_idx]:
            if st.checkbox(label, key=key):
                checked_habits.append(label)

    st.markdown("---")
    
    # 기분, 도시, 코치 스타일
    mood_score = st.slider("오늘의 기분은?", 1, 10, 5)
    
    cities = ["Seoul", "Busan", "Incheon", "Daegu", "Daejeon", "Gwangju", "Suwon", "Ulsan", "Jeju", "Gangneung"]
    selected_city = st.selectbox("현재 도시 선택", cities)
    
    coach_style = st.radio(
        "AI 코치 스타일 선택",
        ("스파르타 코치 🛡️", "따뜻한 멘토 🌿", "게임 마스터 🎲"),
        horizontal=True
    )

# --- 오른쪽 컬럼: 달성률 + 차트 ---
with col_chart:
    st.subheader("📈 나의 성장 그래프")
    
    # 달성률 계산
    completion_rate = int((len(checked_habits) / 5) * 100)
    
    # Metric 카드 3개
    m1, m2, m3 = st.columns(3)
    m1.metric("오늘 달성률", f"{completion_rate}%")
    m2.metric("완료한 습관", f"{len(checked_habits)}개")
    m3.metric("오늘의 기분", f"{mood_score}/10")
    
    # 차트 데이터 구성 (과거 6일 + 오늘)
    chart_data = st.session_state['history'].copy()
    chart_data.append({
        "날짜": datetime.now().strftime("%Y-%m-%d"),
        "달성률": completion_rate,
        "기분": mood_score
    })
    
    df_chart = pd.DataFrame(chart_data)
    
    # 바 차트 표시
    st.bar_chart(df_chart, x="날짜", y=["달성률", "기분"])

# -----------------------------------------------------------------------------
# 4. API 연동 함수
# -----------------------------------------------------------------------------
def get_weather(city, api_key):
    """OpenWeatherMap API에서 날씨 정보 가져오기"""
    if not api_key:
        return None
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&lang=kr&units=metric"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": data["main"]["temp"],
                "desc": data["weather"][0]["description"],
                "main": data["weather"][0]["main"]
            }
    except Exception as e:
        print(f"Weather API Error: {e}")
    return None

def get_dog_image():
    """Dog CEO API에서 랜덤 강아지 사진 및 품종 가져오기"""
    url = "https://dog.ceo/api/breeds/image/random"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            img_url = data['message']
            # URL에서 품종 추출 (예: .../breeds/retriever-golden/...)
            breed = img_url.split('/')[-2].replace('-', ' ').title()
            return img_url, breed
    except Exception as e:
        print(f"Dog API Error: {e}")
    return None, None

def generate_report(openai_key, style, habits, mood, rate, weather_info, dog_breed):
    """OpenAI API를 사용하여 코칭 리포트 생성"""
    client = OpenAI(api_key=openai_key)
    
    system_prompts = {
        "스파르타 코치 🛡️": "당신은 엄격하고 직설적인 스파르타 코치입니다. 변명을 싫어하고 강하게 동기부여합니다.",
        "따뜻한 멘토 🌿": "당신은 다정하고 공감 능력이 뛰어난 심리 상담가이자 멘토입니다. 부드럽게 격려해주세요.",
        "게임 마스터 🎲": "당신은 RPG 게임의 마스터입니다. 사용자는 모험가이며, 습관은 퀘스트입니다. 판타지 톤으로 말해주세요."
    }
    
    weather_str = f"{weather_info['temp']}도, {weather_info['desc']}" if weather_info else "날씨 정보 없음"
    dog_str = f"함께하는 파트너 강아지: {dog_breed}" if dog_breed else ""
    
    prompt = f"""
    [사용자 정보]
    - 달성한 습관: {', '.join(habits) if habits else '없음'}
    - 달성률: {rate}%
    - 기분 점수: {mood}/10
    - 현재 날씨: {weather_str}
    - {dog_str}

    위 정보를 바탕으로 다음 형식에 맞춰 리포트를 작성해줘:
    1. 컨디션 등급: (S, A, B, C, D 중 하나)
    2. 습관 분석: (현재 상태에 대한 피드백)
    3. 날씨 코멘트: (날씨와 기분을 연결한 조언)
    4. 내일 미션: (구체적인 행동 제안)
    5. 오늘의 한마디: (스타일에 맞는 명언이나 대사)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",  # 요청하신 모델명
            messages=[
                {"role": "system", "content": system_prompts.get(style, "당신은 도움이 되는 AI 코치입니다.")},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"리포트 생성 중 오류가 발생했습니다: {str(e)}"

# -----------------------------------------------------------------------------
# 5. 결과 표시 및 리포트 생성 섹션
# -----------------------------------------------------------------------------
st.markdown("---")
st.header("📢 AI 코칭 리포트")

if st.button("컨디션 리포트 생성 ✨", type="primary"):
    if not openai_api_key:
        st.error("⚠️ 사이드바에 OpenAI API Key를 입력해주세요.")
    else:
        with st.spinner("AI 코치가 데이터를 분석하고 강아지를 부르고 있습니다... 🐶"):
            # 1. API 호출
            weather_data = get_weather(selected_city, weather_api_key)
            dog_url, dog_breed = get_dog_image()
            
            # 2. 리포트 생성
            report_text = generate_report(
                openai_api_key, coach_style, checked_habits, 
                mood_score, completion_rate, weather_data, dog_breed
            )
            
            # 3. 결과 화면 출력
            res_col1, res_col2 = st.columns([1, 2])
            
            with res_col1:
                # 날씨 카드
                if weather_data:
                    st.info(f"📍 {selected_city}\n\n🌡️ {weather_data['temp']}°C\n☁️ {weather_data['desc']}")
                else:
                    st.warning("날씨 정보를 가져오지 못했습니다.")
                
                # 강아지 카드
                if dog_url:
                    st.image(dog_url, caption=f"오늘의 파트너: {dog_breed}", use_container_width=True)
                else:
                    st.warning("강아지 사진 로딩 실패")
            
            with res_col2:
                # AI 리포트 출력
                st.markdown(f"### {coach_style}의 분석")
                st.markdown(report_text)
                
                # 공유용 텍스트
                st.caption("📋 복사해서 공유하기")
                share_text = f"[AI 습관 트래커] {datetime.now().strftime('%Y-%m-%d')}\n달성률: {completion_rate}% | 기분: {mood_score}\n코치: {coach_style}"
                st.code(share_text)

# -----------------------------------------------------------------------------
# 6. 하단 API 안내
# -----------------------------------------------------------------------------
with st.expander("ℹ️ API 키 발급 안내"):
    st.markdown("""
    - **OpenAI API Key**: [OpenAI Platform](https://platform.openai.com/)에서 발급 가능합니다.
    - **OpenWeatherMap API Key**: [OpenWeatherMap](https://openweathermap.org/)에서 무료 키를 발급받으세요.
    - **Dog CEO API**: 별도의 키 없이 무료로 사용 가능합니다.
    """)
