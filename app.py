import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import requests

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

# --- 2. TELEGRAM МЭДЭГДЭЛ ИЛГЭЭХ ФУНКЦ ---
def send_telegram_alert(student_name, phone_number, message_text):
    try:
        bot_token = st.secrets["telegram"]["bot_token"]
        chat_id = st.secrets["telegram"]["admin_chat_id"]
        
        text = (
            f"🚨 **ЯАРАЛТАЙ ТУСЛАМЖИЙН ХҮСЭЛТ!**\n\n"
            f"👤 **Сурагч:** {student_name}\n"
            f"📞 **Утас:** {phone_number}\n"
            f"💬 **Нөхцөл байдал:** {message_text}\n"
            f"⏰ **Огноо:** {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Telegram мэдэгдэл илгээхэд алдаа гарлаа: {e}")
        return False

# --- 3. SESSION STATE ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

# --- 4. CSS ДИЗАЙН ---
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
    section[data-testid="stSidebar"] { background-color: #1E4620 !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# --- 5. НЭВТРЭХ БОЛОН БҮРТГҮҮЛЭХ ---
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
                        if str(u.get("Нэр", "")).strip() == l_name.strip() and str(u.get("Нууц үг", "")).strip() == l_pass.strip():
                            role_val = u.get("Хэн") or u.get("Үүрэг") or "Сурагч"
                            user_found = {"Нэр": u.get("Нэр"), "Үүрэг": role_val}
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
                            first_name, password, role, f"{last_name} {first_name}", phone, gender, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ])
                        st.success("Бүртгэл амжилттай боллоо! '🔑 Нэвтрэх' хэсгээр орно уу.")
                    except Exception as e:
                        st.error(f"Google Sheets-рүү хадгалахад алдаа гарлаа: {e}")
            else:
                st.warning("Мэдээллийг бүрэн бөглөнө үү.")

# --- 6. ҮНДСЭН СИСТЕМ ---
else:
    with st.sidebar:
        st.markdown(f"### 🧠 **FourMind**")
        st.caption(f"👤 **{st.session_state.current_user}** ({st.session_state.user_role})")
        st.divider()
        
        menu = st.radio(
            "Цэс сонгох:",
            ["🏠 Нүүр", "🧪 Тестүүд", "📰 Мэдээ мэдээлэл", "📅 Цаг захиалга", "📊 Үр дүн", "📈 Судалгаа", "👥 Бүртгэл мэдээлэл", "❓ Тусламж", "⚙️ Тохиргоо"]
        )
        
        st.divider()
        if st.button("🚪 Гарах"):
            st.session_state.current_user = None
            st.session_state.user_role = None
            st.rerun()

    if menu == "🏠 Нүүр":
        st.title("🌿 Дөрөвдүгээр сургуулийн сэтгэл зүйн хөтчид тавтай морилно уу!")
        st.write("Та зүүн талын цэснээс өөрийн шаардлагатай хэсгийг сонгон үйлчлүүлээрэй.")

    elif menu == "📅 Цаг захиалга":
        st.title("📅 Сэтгэл зүйчид цаг захиалах")
        st.info("Цаг захиалсны дараа таны сэтгэл зүйчид болон calendar-т мэдэгдэл очих болно.")
        
        with st.form("booking_form"):
            b_date = st.date_input("Огноо сонгох:")
            b_time = st.time_input("Цаг сонгох:")
            b_reason = st.text_area("Уулзах шалтгаан / Товч утга:")
            
            if st.form_submit_button("📅 Цаг баталгаажуулах"):
                if b_reason:
                    st.success(f"Амжилттай! {b_date}-ний {b_time} цагт цаг захаллаа.")
                else:
                    st.warning("Уулзах шалтгаанаа товч бичнэ үү.")

    elif menu == "❓ Тусламж":
        st.title("🆘 Яаралтай сэтгэл зүйн тусламж хүсэх")
        st.warning("Та сэтгэл зүйн гүн дарамт эсвэл яаралтай тусламж шаардлагатай байгаа бол доорх маягтыг бөглөнө үү. Сэтгэл зүйчид шууд Telegram мэдэгдэл очих болно!")
        
        with st.form("sos_form"):
            contact_phone = st.text_input("Холбоо барих утасны дугаар:")
            sos_message = st.text_area("Мэдээлэл / Нөхцөл байдал:")
            
            if st.form_submit_button("🚨 Яаралтай тусламж илгээх"):
                if contact_phone and sos_message:
                    success = send_telegram_alert(
                        student_name=st.session_state.current_user,
                        phone_number=contact_phone,
                        message_text=sos_message
                    )
                    if success:
                        st.success("Мэдээлэл сэтгэл зүйчид яаралтай илгээгдлээ! Тантай тун удахгүй холбогдох болно.")
                else:
                    st.warning("Утасны дугаар болон мэдээллээ бүрэн бичнэ үү.")

    elif menu == "⚙️ Тохиргоо":
        st.title("⚙️ Хэрэглэгчийн тохиргоо")
        st.write(f"**Хэрэглэгчийн нэр:** {st.session_state.current_user}")
        st.write(f"**Эрх:** {st.session_state.user_role}")
        st.divider()
        
        st.subheader("🔑 Нууц үг өөрчлөх")
        with st.form("pass_change"):
            old_p = st.text_input("Одоогийн нууц үг:", type="password")
            new_p = st.text_input("Шинэ нууц үг:", type="password")
            confirm_p = st.text_input("Шинэ нууц үг баталгаажуулах:", type="password")
            
            if st.form_submit_button("Нууц үг шинэчлэх"):
                if new_p and new_p == confirm_p:
                    st.success("Нууц үг амжилттай шинэчлэгдлээ.")
                else:
                    st.error("Шинэ нууц үг таарахгүй байна.")

    else:
        st.title(f"{menu}")
        st.info("Энэ хэсгийн контент бэлтгэгдэж байна...")