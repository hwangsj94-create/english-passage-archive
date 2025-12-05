import streamlit as st
import pandas as pd
import datetime
import gspread # GSheetsConnection 대신 직접 gspread 사용
import json # JSON 키 처리를 위해 추가

# --- 설정 및 데이터베이스 연결 ---
st.set_page_config(
    page_title="영어 지문 아카이브 시스템",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🚨 GSheetsConnection 대신 gspread와 st.secrets를 사용하여 연결
@st.cache_resource(ttl=3600) # 1시간마다 연결 갱신
def get_gspread_client():
    try:
        # secrets.toml에서 서비스 계정 정보를 가져옵니다.
        # secrets.toml의 [gsheets.service_account] 섹션 전체를 JSON 형식으로 변환합니다.
        
        # 1. secrets 섹션의 키와 값을 딕셔너리로 만듭니다.
        service_account_info = {
            "type": st.secrets["gsheets.service_account"]["type"],
            "project_id": st.secrets["gsheets.service_account"]["project_id"],
            "private_key_id": st.secrets["gsheets.service_account"]["private_key_id"],
            "private_key": st.secrets["gsheets.service_account"]["private_key"],
            "client_email": st.secrets["gsheets.service_account"]["client_email"],
            "client_id": st.secrets["gsheets.service_account"]["client_id"],
            "auth_uri": st.secrets["gsheets.service_account"]["auth_uri"],
            "token_uri": st.secrets["gsheets.service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gsheets.service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gsheets.service_account"]["client_x509_cert_url"],
        }
        
        # 2. gspread 클라이언트 인증
        gc = gspread.service_account_from_dict(service_account_info)
        
        # 3. 스프레드시트 열기
        spreadsheet_url = st.secrets["gsheets"]["spreadsheet_url"]
        return gc.open_by_url(spreadsheet_url)
    
    except Exception as e:
        st.error(f"⚠️ 데이터베이스 연결 오류가 발생했습니다. secrets.toml 또는 Google Cloud 설정을 확인해주세요. 오류: {e}")
        st.stop()

def load_data(sheet):
    """시트에서 데이터를 불러오고 DataFrame으로 정리합니다."""
    try:
        worksheet = sheet.worksheet("Sheet1") # 'Sheet1' 시트 이름을 사용합니다.
        data = worksheet.get_all_records() # 데이터를 리스트 형태로 가져옵니다.
        df = pd.DataFrame(data)
        return df.dropna(how='all')
    except Exception as e:
        st.warning(f"데이터 로딩 중 오류 발생. 시트 이름이 'Sheet1'이 맞는지 확인해 주세요. 오류: {e}")
        # 오류 시 빈 DataFrame을 반환하여 앱 충돌을 방지합니다.
        cols = ["등록일", "대분류", "상세1", "상세2", "상세3", "번호", "제목_검색용", "지문내용"]
        return pd.DataFrame(columns=cols)


# --- 클라이언트 및 데이터 로드 ---
sheet = get_gspread_client()
existing_df = load_data(sheet)
worksheet_ref = sheet.worksheet("Sheet1")


# --- 탭 구성 (등록/조회/검색) ---
tab_names = ["✍️ 지문 등록", "📚 지문 조회", "🔍 전체 지문 검색"]
registration_tab, view_tab, search_tab = st.tabs(tab_names)


# ====================================================================================
# [1] ✍️ 지문 등록 탭
# ====================================================================================
with registration_tab:
    st.header("✍️ 새로운 영어 지문 등록")
    st.markdown("---")
    
    # 1. 대분류 선택 (기존 코드와 동일)
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
    
    # 2. 선택된 분류에 따른 세부 입력 항목 생성 (기존 코드와 동일)
    if selected_type == "모의고사 및 수능":
        st.subheader("모의고사/수능 세부 정보")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            grade = st.selectbox("학년", ["고1", "고2", "고3"], key="mock_grade")
        with col2:
            year = st.selectbox("년도", [f"{y}년" for y in range(25, 9, -1)], key="mock_year")
        with col3:
            month = st.selectbox("월", ["03월", "04월", "06월", "07월", "09월", "10월", "11월"], key="mock_month")
        with col4:
            mock_num_options = [str(i) for i in range(18, 41)] + ["41~42", "43~45"]
            number = st.selectbox("문항 번호", mock_num_options, key="mock_number")
        
        book_title_for_db = f"{grade} {year} {month}"
        st.info(f"💡 자동으로 저장될 교재 제목: **{book_title_for_db}**")

    elif selected_type == "부교재":
        st.subheader("부교재 세부 정보")
        
        existing_books = existing_df[existing_df['대분류'] == '부교재']['상세1'].unique().tolist()
        
        col1, col2 = st.columns(2)
        with col1:
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
        
        book_title_for_db = book_name if book_name else "미지정 부교재"
        
    elif selected_type == "외부 지문":
        st.subheader("외부 지문 정보")
        source = st.text_input("출처를 입력하세요.", key="external_source")
        number = "1"
        
        book_title_for_db = source if source else "미지정 외부 지문"
        unit = "N/A"
        grade = "N/A"
        
    else:
        st.warning("먼저 지문의 종류를 선택해 주세요.")
        
    
    # 3. 영어 지문 내용 입력 (기존 코드와 동일)
    st.markdown("---")
    
    passage_content = st.text_area(
        "3. 영어 지문 내용 [필수 입력]", 
        height=300,
        placeholder="여기에 영어 지문 전체 내용을 붙여넣거나 입력하세요."
    )
    
    # 4. 편의 기능 및 등록 버튼 (기존 코드와 동일)
    col_button1, col_button2, col_check = st.columns([1, 1, 3])
    
    with col_button1:
        if st.button("줄바꿈 정리 (Clean Text)", help="문장 중간의 불필요한 줄바꿈(엔터)을 제거합니다."):
            if passage_content:
                cleaned_content = passage_content.replace('\n', ' ')
                cleaned_content = cleaned_content.replace('. ', '.\n\n').strip()
                st.session_state["st_text_area"] = cleaned_content
                st.rerun()
            else:
                st.warning("지문 내용이 비어있습니다.")

    st.markdown("---")
    
    col_register, col_continue = st.columns([1, 4])
    with col_register:
        register_button = st.button("✅ 지문 등록", type="primary")

    with col_continue:
        st.checkbox("분류 유지하고 계속 등록 (연속 등록 모드)", key="continue_registration", value=True)


    # 5. [지문 등록] 버튼 클릭 시 데이터 처리 로직 (gspread append 로직으로 변경)
    if register_button:
        if not selected_type or not passage_content.strip():
            st.error("❌ '지문의 종류'를 선택하고, '영어 지문 내용'을 입력해주세요.")
            
        else:
            # 5-1. 중복 체크 (부교재만 해당) - 기존 로직 유지 (existing_df 사용)
            # ... (중복 체크 코드는 생략)

            # 5-2. 데이터 저장 (gspread append 로직으로 변경)
            
            # DB에 저장할 최종 데이터 정리
            row_data = [
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                selected_type,
                grade if selected_type == "모의고사 및 수능" else book_name if selected_type == "부교재" else source,
                year if selected_type == "모의고사 및 수능" else str(unit) if selected_type == "부교재" else "",
                month if selected_type == "모의고사 및 수능" else "",
                str(number),
                book_title_for_db,
                passage_content
            ]
            
            # gspread를 사용하여 데이터 추가
            worksheet_ref.append_row(row_data) # gspread의 append_row 함수 사용
            
            st.success("✅ 지문이 성공적으로 등록되었습니다! (Google Sheets에 저장 완료)")
            
            # 5-3. 입력창 초기화 (기존 로직과 동일)
            # ... (초기화 코드는 생략)

# ====================================================================================
# [2] 📚 지문 조회 탭 (4단계에서 채울 예정)
# ====================================================================================
with view_tab:
    st.header("📚 등록된 지문 목록 및 조회")
    st.warning("⚠️ 4단계에서 이 탭의 코드를 작성할 예정입니다.")

# ====================================================================================
# [3] 🔍 전체 지문 검색 탭 (5단계에서 채울 예정)
# ====================================================================================
with search_tab:
    st.header("🔍 전체 지문 검색")
    st.warning("⚠️ 5단계에서 이 탭의 코드를 작성할 예정입니다.")


# --- 지문 내용 변경 시 분류 초기화 방지 로직 (기존 로직과 동일) ---
# ... (초기화 방지 코드는 생략)
