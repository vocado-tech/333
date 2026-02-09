import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import random
from openai import OpenAI

# -----------------------------------------------------------------------------
# 1. 기본 설정 (Page Config & Session State)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="AI 습관 & 타로 오라클", page_icon="🔮", layout="wide")

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

# 타로 카드 결과 저장용
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
    st.info("💡 습관 달성률 60% 이상이면 타로 카드를 뽑을 수 있습니다!")

# -----------------------------------------------------------------------------
# 3. 메인 타이틀 및 UI 구성
# -----------------------------------------------------------------------------
st.title("🔮 AI 습관 오라클")
st.markdown("습관을 달성하고 운명을 점쳐보세요. 당신의 노력에 따라 운세가 달라집니다.")

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
        "AI 점술가 스타일 선택",
        ("냉철한 예언가 👁️", "다정한 마녀 🧙‍♀️", "운명의 장난꾸러기 🃏"),
        horizontal=True
    )

# --- 오른쪽 컬럼: 달성률 + 차트 ---
with col_chart:
    st.subheader("📈 운명의 흐름")
    
    # 달성률 계산
    completion_rate = int((len(checked_habits) / 5) * 100)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("운명 개척도(달성률)", f"{completion_rate}%")
    m2.metric("완료한 과업", f"{len(checked_habits)}개")
    m3.metric("내면의 상태(기분)", f"{mood_score}/10")
    
    chart_data = st.session_state['history'].copy()
    chart_data.append({
        "날짜": datetime.now().strftime("%Y-%m-%d"),
        "달성률": completion_rate,
        "기분": mood_score
    })
    
    df_chart = pd.DataFrame(chart_data)
    st.bar_chart(df_chart, x="날짜", y=["달성률", "기분"])

# -----------------------------------------------------------------------------
# 4. API 연동 함수
# -----------------------------------------------------------------------------
def get_weather(city, api_key):
    if not api_key: return None
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&lang=kr&units=metric"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {"temp": data["main"]["temp"], "desc": data["weather"][0]["description"]}
    except: pass
    return None

def get_dog_image():
    try:
        response = requests.get("https://dog.ceo/api/breeds/image/random", timeout=5)
        if response.status_code == 200:
            data = response.json()
            breed = data['message'].split('/')[-2].replace('-', ' ').title()
            return data['message'], breed
    except: pass
    return None, None

def get_tarot_card():
    try:
        response = requests.get("https://tarotapi.dev/api/v1/cards/random?n=1", timeout=5)
        if response.status_code == 200:
            return response.json()['cards'][0]
    except: pass
    return {"name": "The Fool", "meaning_up": "새로운 시작, 모험, 순수함", "desc": "기본 카드"}

def generate_fortune_report(openai_key, style, habits, mood, rate, weather, dog, tarot):
    client = OpenAI(api_key=openai_key)
    
    system_prompts = {
        "냉철한 예언가 👁️": "당신은 미래를 꿰뚫어 보는 냉철한 예언가입니다. 듣기 좋은 말보다는 사실적이고 분석적인 어조로 운세를 해석하세요.",
        "다정한 마녀 🧙‍♀️": "당신은 숲속의 지혜롭고 다정한 마녀입니다. 타로 카드의 의미를 따뜻하게 풀어서 용기를 주세요.",
        "운명의 장난꾸러기 🃏": "당신은 수수께끼를 좋아하는 광대입니다. 유머러스하고 재치 있게 운세를 풀어주세요."
    }
    
    tarot_info = "타로 카드를 뽑지 않았습니다."
    if tarot:
        tarot_info = f"뽑은 카드: {tarot['name']}\n기본 의미: {tarot['meaning_up']}"

    weather_desc = weather['desc'] if weather else '알 수 없음'

    prompt = f"""
    [사용자 데이터]
    - 달성 습관: {', '.join(habits) if habits else '없음'} (달성률: {rate}%)
    - 기분: {mood}/10
    - 날씨: {weather_desc}
    - {tarot_info}

    위 정보를 바탕으로 아래 형식에 맞춰 서술형 리포트를 작성해 주세요.
    특히 **타로 카드의 의미를 사용자의 오늘 하루 습관 및 기분과 연결하여 상세히 해석**해야 합니다.

    [출력 형식]
    1. 🔮 **오늘의 영적 컨디션**: (S~F 등급과 짧은 총평)
    2. 🃏 **타로 정밀 해석**:
       - **종합 운세**: (카드가 암시하는 오늘의 흐름)
       - **💰 재물운**: (카드와 오늘 행동을 연관 지어 금전적 행운 예측)
       - **❤️ 애정/대인운**: (주변 사람과의 관계 예측)
    3. ⚡ **내일의 행동 지침**: (운세를 좋게 만들기 위한 구체적 행동 1가지)
    4. 📜 **오늘의 예언**: (스타일에 맞는 인상 깊은 한 문장)
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompts.get(style, "당신은 AI 점술가입니다.")},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"운세를 점치는 중 수정 구슬에 금이 갔습니다... (오류: {str(e)})"

# -----------------------------------------------------------------------------
# 5. 타로 카드 & 결과 표시 섹션
# -----------------------------------------------------------------------------
st.markdown("---")
st.header("🃏 오늘의 타로 뽑기")

if completion_rate >= 60:
    if st.session_state['tarot_result'] is None:
        st.info(f"오늘 할 일의 {completion_rate}%를 달성하여 운명의 카드가 해금되었습니다!")
        if st.button("운명의 카드 뒤집기 👆"):
            with st.spinner("우주의 기운을 모으는 중..."):
                st.session_state['tarot_result'] = get_tarot_card()
                st.rerun()
    
    # 카드가 뽑힌 상태라면
    else:
        card = st.session_state['tarot_result']
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image("https://upload.wikimedia.org/wikipedia/commons/d/de/RWS_Tarot_01_Magician.jpg", 
                     caption="Tarot Card", use_container_width=True)
        with c2:
            st.subheader(f"🎴 {card['name']}")
            st.markdown(f"**핵심 의미:** {card['meaning_up']}")
            st.info("아래 '종합 운세 분석' 버튼을 눌러 AI의 상세 해석(재물운, 애정운)을 확인하세요!")
            if st.button("다시 뽑기 (테스트용)"):
                st.session_state['tarot_result'] = None
                st.rerun()

else:
    st.warning(f"🔒 현재 달성률 {completion_rate}%입니다. 60%를 넘기면 타로 카드를 뽑을 수 있습니다.")
    st.session_state['tarot_result'] = None

# -----------------------------------------------------------------------------
# 6. 종합 리포트 생성
# -----------------------------------------------------------------------------
st.markdown("---")
if st.button("✨ 종합 운세 분석 결과 보기", type="primary"):
    if not openai_api_key:
        st.error("⚠️ 정확한 점괘를 보려면 OpenAI API Key가 필요합니다.")
    else:
        with st.spinner("AI 점술가가 카드를 읽고 별자리를 관측하고 있습니다..."):
            weather_data = get_weather(selected_city, weather_api_key)
            dog_url, dog_breed = get_dog_image()
            tarot_card = st.session_state.get('tarot_result')
            
            report = generate_fortune_report(
                openai_api_key, coach_style, checked_habits, 
                mood_score, completion_rate, weather_data, dog_breed, tarot_card
            )
            
            r_col1, r_col2 = st.columns([1, 2])
            
            with r_col1:
                # [수정됨] 날씨 정보 표시 박스 복구
                if weather_data:
                    st.info(f"📍 {selected_city}\n\n🌡️ {weather_data['temp']}°C\n☁️ {weather_data['desc']}")
                else:
                    st.warning("날씨 정보 없음")
                
                # 강아지 이미지
                if dog_url:
                    st.image(dog_url, caption=f"행운의 파트너: {dog_breed}", use_container_width=True)
            
            with r_col2:
                st.markdown(f"### {coach_style}의 해석")
                st.markdown(report)
                
                # 깔끔한 복사용 텍스트
                st.text_area("친구에게 공유하기", value=report, height=100)

# -----------------------------------------------------------------------------
# 7. 하단 안내
# -----------------------------------------------------------------------------
with st.expander("ℹ️ 사용 가이드"):
    st.markdown("""
    1. **습관 체크**: 위에서 오늘 한 일을 체크하세요.
    2. **타로 해금**: 60% 이상 달성하면 타로 카드를 뽑을 수 있습니다.
    3. **운세 분석**: '종합 운세 분석' 버튼을 누르면 AI가 뽑은 카드와 오늘의 행동을 연결해 **재물운, 애정운** 등을 해석해줍니다.
    """)
