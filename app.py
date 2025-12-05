import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="최종 연결 테스트", layout="wide")
st.title("📌 Google Sheets 최종 연결 테스트")

try:
    # 1. 연결 객체 생성만 시도 (데이터 읽기 시도 없음)
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 연결 객체 생성 성공 시 이 메시지가 떠야 합니다.
    st.success("🎉 데이터베이스 연결 객체 생성 성공! (secrets.toml 설정 완벽)")
    st.balloons()
    
except Exception as e:
    # 연결 객체 생성 실패 시 이 오류 메시지가 뜹니다.
    st.error(f"❌ 최종 연결 실패! (Secrets 또는 IAM 문제): {e}")

st.markdown("---")
st.markdown("이 테스트 성공 시, 원래의 복잡한 코드로 돌아가도 정상적으로 앱이 실행될 것입니다.")
