import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import random
from openai import OpenAI

# -----------------------------------------------------------------------------
# 1. 기본 설정 (Page Config & Session State)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI 습관 트래커", page_icon="🔮", layout="wide")

# 세션 상태 초기화
if 'history' not in st.session_state:
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

# 타로 카드 결과 저장용 세션
if 'tarot_result' not in st.session_state:
    st.session_state['tarot_result'] = None

# -----------------------------------------------------------------------------
# 2. 사이드바 (API Key 입력)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 설정")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    weather_api_key = st.text_input("OpenWeatherMap API Key", type="password")
    st.markdown("---")
    st.info("💡 API 키가 있어야 리포트 생성이 가능합니다.")
    st.warning("타로 기능은 습관 60% 이상 달성 시 해금됩니다!")

# -----------------------------------------------------------------------------
# 3. 메인 타이틀 및 UI 구성
# -----------------------------------------------------------------------------
st.title("📊 AI 습관 트래커 & 타로")
st.markdown("매일의 작은 습관이 미래를 만듭니다. 60% 이상 달성하고 운세를 점쳐보세요!")

col_ui, col_chart = st.columns([1, 1])

# --- 왼쪽 컬럼: 습관 체크인 UI ---
with col_ui:
    st.subheader("📝 오늘의 체크인")
    
    habits = [
        ("🌅 기상 미션", "mission_morning"),
        ("💧 물 마시기", "drink_water"),
        ("📚 공부/독서", "study_read"),
        ("💪 운동하기", "workout"),
        ("💤 수면", "sleep_well")
    ]
    
    checked_habits = []
    habit_cols = st.columns(2)
    
    for i, (label, key) in enumerate(habits):
        col_idx = i % 2
        with habit_cols[col_idx]:
            if st.checkbox(label, key=key):
                checked_habits.append(label)

    st.markdown("---")
    
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
    
    m1, m2, m3 = st.columns(3)
    m1.metric("오늘 달성률", f"{completion_rate}%")
    m2.metric("완료한 습관", f"{len(checked_habits)}개")
    m3.metric("오늘의 기분", f"{mood_score}/10")
    
    chart_data = st.session_state['history'].copy()
    chart_data.append({
        "날짜": datetime.now().strftime("%Y-%m-%d"),
        "달성률": completion_rate,
        "기분": mood_score
    })
    
    df_chart = pd.DataFrame(chart_data)
    st.bar_chart(df_chart, x="날짜", y=["달성률", "기분"])

# -----------------------------------------------------------------------------
# 4. API 연동 함수 (Tarot 추가됨)
# -----------------------------------------------------------------------------
def get_weather(city, api_key):
    """OpenWeatherMap API (에러 디버깅 포함)"""
    if not api_key:
        return None
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&lang=kr&units=metric"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": data["main"]["temp"],
                "desc": data["weather"][0]["description"],
                "main": data["weather"][0]["main"]
            }
        else:
            # 디버깅용 에러 출력 (실제 배포 시엔 로그로 변경 권장)
            print(f"Weather API Error: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Weather Connection Error: {e}")
    return None

def get_dog_image():
    """Dog CEO API"""
    url = "https://dog.ceo/api/breeds/image/random"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            img_url = data['message']
            breed = img_url.split('/')[-2].replace('-', ' ').title()
            return img_url, breed
    except Exception as e:
        print(f"Dog API Error: {e}")
    return None, None

def get_tarot_card():
    """Tarot API (무료)"""
    url = "https://tarotapi.dev/api/v1/cards/random?n=1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            card_data = response.json()['cards'][0]
            return {
                "name": card_data['name'],
                "meaning": card_data['meaning_up'],
                "desc": card_data['desc']
            }
    except Exception as e:
        return {"name": "The Fool", "meaning": "새로운 시작 (API 연결 실패로 기본값 제공)", "desc": ""}
    return None

def generate_report(openai_key, style, habits, mood, rate, weather_info, dog_breed, tarot_card):
    """OpenAI API (gpt-4o-mini 수정됨)"""
    client = OpenAI(api_key=openai_key)
    
    system_prompts = {
        "스파르타 코치 🛡️": "당신은 엄격하고 직설적인 스파르타 코치입니다. 변명을 싫어하고 강하게 동기부여합니다.",
        "따뜻한 멘토 🌿": "당신은 다정하고 공감 능력이 뛰어난 심리 상담가이자 멘토입니다. 부드럽게 격려해주세요.",
        "게임 마스터 🎲": "당신은 RPG 게임의 마스터입니다. 사용자는 모험가이며, 습관은 퀘스트입니다. 판타지 톤으로 말해주세요."
    }
    
    weather_str = f"{weather_info['temp']}도, {weather_info['desc']}" if weather_info else "정보 없음"
    dog_str = f"파트너 강아지: {dog_breed}" if dog_breed else ""
    tarot_str = f"오늘의 타로: {tarot_card['name']} (의미: {tarot_card['meaning']})" if tarot_card else "타로 안 뽑음"
    
    prompt = f"""
    [사용자 정보]
    - 달성 습관: {', '.join(habits) if habits else '없음'} ({rate}%)
    - 기분: {mood}/10
    - 날씨: {weather_str}
    - {dog_str}
    - {tarot_str}

    위 정보를 바탕으로 리포트 작성:
    1. 컨디션 등급 (S~D)
    2. 습관 분석
    3. 타로 운세 해석 (오늘의 노력과 타로 카드의 의미를 연결해서 해석해줘)
    4. 내일 미션
    5. 오늘의 한마디
    """

    try:
        # 모델명 gpt-4o-mini로 변경 (안정성 확보)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompts.get(style, "당신은 AI 코치입니다.")},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"리포트 생성 오류: {str(e)}"

# -----------------------------------------------------------------------------
# 5. 타로 카드 & 결과 표시 섹션
# -----------------------------------------------------------------------------
st.markdown("---")

# [NEW] 타로 카드 섹션
st.header("🔮 오늘의 신비한 타로")

# 달성률 60% 체크
if completion_rate >= 60:
    st.success(f"축하합니다! 습관을 {completion_rate}% 달성하여 타로 카드가 해금되었습니다.")
    
    # 타로 뽑기 버튼
    if st.button("운명의 카드 뽑기 🃏"):
        with st.spinner("우주의 기운을 모으는 중..."):
            card = get_tarot_card()
            st.session_state['tarot_result'] = card
            
    # 뽑은 결과가 있으면 표시
    if st.session_state['tarot_result']:
        card = st.session_state['tarot_result']
        t_col1, t_col2 = st.columns([1, 3])
        with t_col1:
            st.image("https://upload.wikimedia.org/wikipedia/commons/d/de/RWS_Tarot_01_Magician.jpg", 
                     caption="Tarot Card (예시 이미지)", use_container_width=True) 
            # 실제 API는 이미지를 잘 안 줘서, 분위기용 이미지를 넣거나 카드 이름에 맞는 이미지를 매핑해야 함.
            # 여기서는 편의상 고정 이미지를 사용하거나 텍스트 위주로 보여줍니다.
        with t_col2:
            st.subheader(f"🎴 {card['name']}")
            st.markdown(f"**의미:** {card['meaning']}")
            st.info(f"**상세:** {card['desc'][:200]}...") # 너무 길면 자르기

else:
    st.warning(f"🔒 현재 달성률 {completion_rate}%입니다. 60% 이상 달성해야 타로 카드를 뽑을 수 있습니다!")
    st.session_state['tarot_result'] = None # 조건 미달 시 리셋

st.markdown("---")
st.header("📢 AI 코칭 리포트")

# 리포트 생성 버튼
if st.button("종합 리포트 생성 ✨", type="primary"):
    if not openai_api_key:
        st.error("⚠️ 사이드바에 OpenAI API Key를 입력해주세요.")
    else:
        with st.spinner("AI가 데이터를 분석 중입니다..."):
            weather_data = get_weather(selected_city, weather_api_key)
            dog_url, dog_breed = get_dog_image()
            
            # 타로 결과가 있으면 같이 보냄
            current_tarot = st.session_state.get('tarot_result')
            
            report_text = generate_report(
                openai_api_key, coach_style, checked_habits, 
                mood_score, completion_rate, weather_data, dog_breed, current_tarot
            )
            
            res_col1, res_col2 = st.columns([1, 2])
            
            with res_col1:
                if weather_data:
                    st.info(f"📍 {selected_city}\n\n🌡️ {weather_data['temp']}°C\n☁️ {weather_data['desc']}")
                
                if dog_url:
                    st.image(dog_url, caption=f"오늘의 파트너: {dog_breed}", use_container_width=True)
            
            with res_col2:
                st.markdown(f"### {coach_style}의 분석")
                st.markdown(report_text)
                
                st.caption("📋 공유 텍스트")
                share_text = f"[습관 트래커] 달성률: {completion_rate}% | 타로: {current_tarot['name'] if current_tarot else '미확인'}"
                st.code(share_text)

# -----------------------------------------------------------------------------
# 6. 하단 안내
# -----------------------------------------------------------------------------
with st.expander("ℹ️ API 및 기능 안내"):
    st.markdown("""
    - **OpenAI**: gpt-4o-mini 모델을 사용합니다.
    - **타로 기능**: 습관 달성률 60% 이상일 때 '타로 뽑기' 버튼이 활성화됩니다.
    - **날씨 오류 시**: API Key가 활성화되었는지 확인하거나 도시 이름을 영어로 정확히 입력했는지 확인하세요.
    """)
