import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd

# --- 1. GOOGLE SHEETS ХОЛБОЛТ ---
try:
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(credentials)

    spreadsheet = gc.open("FourMind_Data")
    sheet_users = spreadsheet.worksheet("users")
    sheet_results = spreadsheet.worksheet("results")
    
    try:
        sheet_tests = spreadsheet.worksheet("tests")
    except Exception:
        sheet_tests = None

except Exception as e:
    st.error(f"Google Sheets холболтын алдаа: {e}")

# --- 2. SESSION STATE АНХНЫ ТОХИРГОО ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

# --- 3. CSS ДИЗАЙН ---
st.markdown("""
<style>
    .main { background-color: #F7FBF7; }
    .stButton>button {
        background-color: #2E7D32 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        border: none !important;
    }
    .stButton>button:hover { background-color: #1B5E20 !important; }
    .test-card {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 12px;
        border-left: 5px solid #2E7D32;
        margin-bottom: 12px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.05);
    }
    section[data-testid="stSidebar"] {
        background-color: #1E4620 !important;
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. НЭВТРЭХ БОЛОН БҮРТГҮҮЛЭХ ---
if st.session_state.current_user is None:
    st.title("🧠 FourMind - Сэтгэл зүй, Эрүүл ирээдүй")
    tab1, tab2 = st.tabs(["🔑 Нэвтрэх", "📝 Шинээр бүртгүүлэх"])
    
    with tab1:
        st.subheader("Системд нэвтрэх")
        l_name = st.text_input("Хэрэглэгчийн нэр:", key="login_username")
        l_pass = st.text_input("Нууц үг:", type="password", key="login_pass_field")
        
        if st.button("Нэвтрэх", key="login_submit_btn"):
            if l_name and l_pass:
                try:
                    all_users = sheet_users.get_all_records()
                    user_found = None
                    
                    for u in all_users:
                        # "Нэр" болон "Нууц үг" багана таарч байгаа эсэхийг шалгах
                        if str(u.get("Нэр", "")).strip() == l_name.strip() and str(u.get("Нууц үг", "")).strip() == l_pass.strip():
                            # Google Sheet дээрх баганын нэр "Хэн" эсвэл "Үүрэг" байхыг хоёуланг нь дэмжих
                            role_val = u.get("Хэн") or u.get("Үүрэг") or "Сурагч"
                            user_found = {
                                "Нэр": u.get("Нэр"),
                                "Үүрэг": role_val
                            }
                            break
                    
                    if user_found:
                        st.session_state.current_user = user_found.get("Нэр")
                        st.session_state.user_role = user_found.get("Үүрэг")
                        st.success("Амжилттай нэвтэрлээ!")
                        st.rerun()
                    else:
                        st.error("Хэрэглэгчийн нэр эсвэл нууц үг буруу байна.")
                except Exception as e:
                    st.error(f"Нэвтрэхэд алдаа гарлаа: {e}")
            else:
                st.warning("Мэдээллээ бүрэн бөглөнө үү.")

    with tab2:
        st.subheader("Шинэ бүртгэл үүсгэх")
        role = st.selectbox("Та хэн бэ?", ["Сурагч", "Анги удирдсан багш", "Асран хамгаалагч", "Админ"], key="reg_role")
        last_name = st.text_input("Овог:", key="reg_lname")
        first_name = st.text_input("Нэр:", key="reg_fname")
        password = st.text_input("Нууц үг үүсгэх:", type="password", key="reg_pass_field")
        gender = st.selectbox("Хүйс:", ["Эрэгтэй", "Эмэгтэй"], key="reg_gender")
        phone = st.text_input("Утасны дугаар:", key="reg_phone")
        
        if st.button("Бүртгүүлэх", key="reg_submit_btn"):
            if first_name and password and phone:
                if role == "Админ" and password != "admin123":
                    st.error("Админы нууц код буруу байна!")
                else:
                    try:
                        sheet_users.append_row([
                            first_name, 
                            password, 
                            role, 
                            f"{last_name} {first_name}", 
                            phone, 
                            gender, 
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ])
                        st.success("Бүртгэл амжилттай боллоо! '🔑 Нэвтрэх' хэсгээр орно уу.")
                    except Exception as e:
                        st.error(f"Google Sheets-рүү хадгалахад алдаа гарлаа: {e}")
            else:
                st.warning("Мэдээллийг бүрэн бөглөнө үү.")

# --- 5. ҮНДСЭН СИСТЕМ ---
else:
    with st.sidebar:
        st.markdown(f"### 🧠 **FourMind**")
        st.caption(f"👤 **{st.session_state.current_user}** ({st.session_state.user_role})")
        st.divider()
        
        menu = st.radio(
            "Цэс сонгох:",
            [
                "🏠 Нүүр", 
                "🧪 Тестүүд", 
                "📰 Мэдээ мэдээлэл", 
                "📅 Цаг захиалга", 
                "📊 Үр дүн", 
                "📈 Судалгаа", 
                "👥 Бүртгэл мэдээлэл", 
                "❓ Тусламж", 
                "⚙️ Тохиргоо"
            ]
        )
        
        st.divider()
        if st.button("🚪 Гарах"):
            st.session_state.current_user = None
            st.session_state.user_role = None
            st.rerun()

    if menu == "🏠 Нүүр":
        st.title("🌿 Дөрөвдүгээр сургуулийн сэтгэл зүйн хөтчид тавтай морилно уу!")
        st.write("Та зүүн талын цэснээс өөрийн шаардлагатай хэсгийг сонгон үйлчлүүлээрэй.")

    elif menu == "🧪 Тестүүд":
        st.title("🧪 Сэтгэл Зүйн Тестүүд")
        
        if st.session_state.user_role == "Админ":
            with st.expander("➕ Шинэ тест эсвэл Багц нэмэх (Админ хэсэг)"):
                with st.form("add_test_form"):
                    category = st.text_input("Багцын нэр:", value="Мэргэжил сонголт")
                    test_title = st.text_input("Тестийн нэр:")
                    test_desc = st.text_area("Тайлбар:")
                    test_questions = st.text_area("Асуултууд (Таслалаар зааглаж бичнэ үү):", help="Жишээ: Асуулт 1, Асуулт 2")
                    
                    if st.form_submit_button("Тест нийтлэх"):
                        if test_title and test_questions:
                            try:
                                if sheet_tests:
                                    sheet_tests.append_row([
                                        category, test_title, test_desc, test_questions, st.session_state.current_user, datetime.now().strftime("%Y-%m-%d")
                                    ])
                                    st.success("Шинэ тест амжилттай нэмэгдлээ!")
                                    st.rerun()
                                else:
                                    st.error("Google Sheets дээр 'tests' нэртэй worksheet олдсонгүй.")
                            except Exception as e:
                                st.error(f"Алдаа гарлаа: {e}")
                        else:
                            st.warning("Мэдээллийг бүрэн бөглөнө үү.")

        st.subheader("📦 БАГЦУУД")
        
        try:
            if sheet_tests:
                all_tests = sheet_tests.get_all_records()
                if all_tests:
                    categories = list(set([t.get("Багцын нэр", "Ерөнхий") for t in all_tests]))
                    
                    for cat in categories:
                        st.markdown(f"#### 📦 **{cat}**")
                        cat_tests = [t for t in all_tests if t.get("Багцын нэр") == cat]
                        
                        for t in cat_tests:
                            with st.container():
                                st.markdown(f"""
                                <div class="test-card">
                                    <h4>✏️ {t.get('Тестийн нэр')}</h4>
                                    <p style="color: #666;">{t.get('Тайлбар', 'Тайлбаргүй')}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                with st.expander("Тест өгөх"):
                                    questions = str(t.get('Асуултууд', '')).split(',')
                                    answers = []
                                    for i, q in enumerate(questions):
                                        if q.strip():
                                            ans = st.radio(f"{i+1}. {q.strip()}", ["Үгүй", "Заримдаа", "Байнга"], key=f"q_{t.get('Тестийн нэр')}_{i}")
                                            answers.append(ans)
                                    if st.button("Хариу илгээх", key=f"btn_{t.get('Тестийн нэр')}"):
                                        st.success("Хариу амжилттай хадгалагдлаа!")
                else:
                    st.info("Одоогоор нэмэгдсэн тест байхгүй байна.")
            else:
                st.info("Google Sheet дээр 'tests' нэртэй хуудас үүсгээгүй байна.")
        except Exception as e:
            st.info("Тестийн мэдээллийг ачаалахад алдаа гарлаа эсвэл сан хоосон байна.")

    else:
        st.title(f"{menu}")
        st.info("Энэ хэсгийн контент бэлтгэгдэж байна...")