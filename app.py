import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

# --- 설정 및 데이터베이스 연결 ---
# Streamlit 페이지의 기본 설정 (가장 위에 보이는 제목 등)
st.set_page_config(
    page_title="영어 지문 아카이브 시스템",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 구글 시트 데이터베이스에 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"⚠️ 데이터베이스 연결 오류가 발생했습니다. secrets.toml 파일의 설정을 확인해주세요. 오류: {e}")
    st.stop()

# 모든 데이터를 DataFrame 형태로 미리 불러오기
try:
    existing_data = conn.read(ttl=1) # 1초마다 최신 데이터로 업데이트 (TTL: Time To Live)
    existing_df = existing_data.copy()
    existing_df = existing_df.dropna(how='all') # 전부 비어있는 행은 제거
except Exception:
    # 데이터가 없거나, 연결 문제로 DataFrame 생성 실패 시, 빈 DataFrame을 만듭니다.
    cols = ["등록일", "대분류", "상세1", "상세2", "상세3", "번호", "제목_검색용", "지문내용"]
    existing_df = pd.DataFrame(columns=cols)


# --- 탭 구성 (등록/조회/검색) ---
tab_names = ["✍️ 지문 등록", "📚 지문 조회", "🔍 전체 지문 검색"]
registration_tab, view_tab, search_tab = st.tabs(tab_names)


# ====================================================================================
# [1] ✍️ 지문 등록 탭
# ====================================================================================
with registration_tab:
    st.header("✍️ 새로운 영어 지문 등록")
    st.markdown("---")

    # 1. 대분류 선택
    type_options = ["모의고사 및 수능", "부교재", "외부 지문"]
    selected_type = st.selectbox(
        "1. 지문의 종류를 선택하세요.",
        options=type_options,
        index=None,
        placeholder="분류 선택",
        key="main_category"
    )

    # 이탈 방지 로직을 위한 지문 내용 입력 공간 미리 정의
    passage_content = ""
    
    # 2. 선택된 분류에 따른 세부 입력 항목 생성
    if selected_type == "모의고사 및 수능":
        st.subheader("모의고사/수능 세부 정보")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            grade = st.selectbox("학년", ["고1", "고2", "고3"], key="mock_grade")
        with col2:
            year = st.selectbox("년도", [f"{y}년" for y in range(25, 9, -1)], key="mock_year") # 25년부터 10년까지
        with col3:
            month = st.selectbox("월", ["03월", "04월", "06월", "07월", "09월", "10월", "11월"], key="mock_month")
        with col4:
            mock_num_options = [str(i) for i in range(18, 41)] + ["41~42", "43~45"]
            number = st.selectbox("문항 번호", mock_num_options, key="mock_number")
        
        # 교재 제목 자동 생성
        book_title_for_db = f"{grade} {year} {month}"
        st.info(f"💡 자동으로 저장될 교재 제목: **{book_title_for_db}**")

    elif selected_type == "부교재":
        st.subheader("부교재 세부 정보")
        
        # 기존 부교재 이름 목록 불러오기
        existing_books = existing_df[existing_df['대분류'] == '부교재']['상세1'].unique().tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            # 콤보박스 (드롭다운 + 입력 가능) 구현
            book_name = st.selectbox(
                "교재 이름 (기존 선택 또는 새 교재 입력)",
                options=existing_books,
                index=None,
                placeholder="교재 이름을 선택하거나 아래에 입력하세요",
                key="sub_book_name_select"
            )
            is_new_book = st.checkbox("새 교재 추가", key="new_book_check")
            if is_new_book:
                book_name = st.text_input("새 교재 이름 입력", key="sub_book_name_input")
        
        with col2:
            # 단원 입력 (해당 교재에 대해 등록된 단원 목록 불러오기)
            existing_units = []
            if book_name and not is_new_book:
                existing_units = existing_df[(existing_df['대분류'] == '부교재') & (existing_df['상세1'] == book_name)]['상세2'].unique().tolist()
            
            unit_options = ["+추가하기"] + [u for u in existing_units if u not in ["+추가하기", None, ""]]
            unit_select = st.selectbox(
                "단원 (기존 선택 또는 +추가하기)",
                options=unit_options,
                key="sub_unit_select"
            )
            
            unit = None
            is_new_unit = unit_select == "+추가하기"
            if is_new_unit:
                unit = st.number_input("새 단원 번호 입력", min_value=1, step=1, key="sub_unit_input")
            elif unit_select:
                unit = unit_select
        
        number = st.number_input("문항 번호", min_value=1, step=1, key="sub_number")
        
        book_title_for_db = book_name if book_name else "미지정 부교재" # 교재 이름
        
    elif selected_type == "외부 지문":
        st.subheader("외부 지문 정보")
        source = st.text_input("출처를 입력하세요.", key="external_source")
        number = "1" # 외부지문은 번호가 의미 없으므로 1로 통일
        
        book_title_for_db = source if source else "미지정 외부 지문"
        unit = "N/A"
        grade = "N/A"
        
    else: # 아무것도 선택하지 않은 경우
        st.warning("먼저 지문의 종류를 선택해 주세요.")
        
    
    # 3. 영어 지문 내용 입력
    st.markdown("---")
    
    # 지문 내용 입력 (text_area는 key를 별도로 지정하지 않아도 됨)
    passage_content = st.text_area(
        "3. 영어 지문 내용 [필수 입력]", 
        height=300,
        placeholder="여기에 영어 지문 전체 내용을 붙여넣거나 입력하세요."
    )
    
    # 4. 편의 기능 및 등록 버튼
    col_button1, col_button2, col_check = st.columns([1, 1, 3])
    
    with col_button1:
        if st.button("줄바꿈 정리 (Clean Text)", help="문장 중간의 불필요한 줄바꿈(엔터)을 제거합니다."):
            # 편의 기능 2: 줄바꿈 정리
            if passage_content:
                cleaned_content = passage_content.replace('\n', ' ')
                cleaned_content = cleaned_content.replace('. ', '.\n\n').strip() # 문단 구분은 남김
                st.session_state["st_text_area"] = cleaned_content
                st.rerun() # 정리된 내용을 다시 보여주기 위해 페이지 재실행
            else:
                st.warning("지문 내용이 비어있습니다.")

    with col_button2:
        # 이탈 방지 및 초기화 로직은 Streamlit의 특성상 세부 코딩이 필요하지만, 여기서는 기본 흐름만 잡습니다.
        # 실제 개발 시에는 Streamlit의 Session State와 콜백 함수를 사용해야 합니다.
        pass 
    
    st.markdown("---")
    
    col_register, col_continue = st.columns([1, 4])
    with col_register:
        register_button = st.button("✅ 지문 등록", type="primary")

    with col_continue:
        # 편의 기능 1: 연속 등록 모드
        st.checkbox("분류 유지하고 계속 등록 (연속 등록 모드)", key="continue_registration", value=True)


    # 5. [지문 등록] 버튼 클릭 시 데이터 처리 로직
    if register_button:
        if not selected_type or not passage_content.strip():
            st.error("❌ '지문의 종류'를 선택하고, '영어 지문 내용'을 입력해주세요.")
            
        else:
            # 5-1. 중복 체크 (부교재만 해당)
            is_duplicate = False
            if selected_type == "부교재" and book_name and unit and number:
                # 문항 번호는 숫자로 변환
                number_str = str(int(number))
                
                # 기존 데이터 중 [부교재, 교재 이름, 단원, 문항 번호]가 모두 일치하는 행이 있는지 확인
                match = existing_df[
                    (existing_df['대분류'] == '부교재') & 
                    (existing_df['상세1'] == book_name) & 
                    (existing_df['상세2'] == str(unit)) & 
                    (existing_df['번호'] == number_str)
                ]
                if not match.empty:
                    is_duplicate = True
                    st.error(f"⚠️ 이미 등록된 문항 번호입니다: **{book_name} - {unit}단원 - {number_str}번**")

            # 5-2. 데이터 저장
            if not is_duplicate:
                
                # DB에 저장할 최종 데이터 정리
                new_data = pd.DataFrame([{
                    "등록일": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "대분류": selected_type,
                    # 모의고사 및 수능: 상세1=학년, 상세2=년도, 상세3=월
                    # 부교재: 상세1=교재 이름, 상세2=단원, 상세3=''
                    # 외부 지문: 상세1=출처, 상세2='', 상세3=''
                    "상세1": grade if selected_type == "모의고사 및 수능" else book_name if selected_type == "부교재" else source,
                    "상세2": year if selected_type == "모의고사 및 수능" else str(unit) if selected_type == "부교재" else "",
                    "상세3": month if selected_type == "모의고사 및 수능" else "",
                    "번호": str(number), # 번호는 모두 문자열로 저장
                    "제목_검색용": book_title_for_db, # 교재 목록에 보일 이름
                    "지문내용": passage_content
                }])
                
                # 구
