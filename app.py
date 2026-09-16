import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import requests
import pandas as pd
import os

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
    
    # Мэдрэмж хадгалах хуудас
    try:
        sheet_feelings = spreadsheet.worksheet("feelings")
    except Exception:
        sheet_feelings = None

    # Админы тест хадгалах хуудас
    try:
        sheet_tests = spreadsheet.worksheet("tests")
    except Exception:
        sheet_tests = spreadsheet.add_worksheet(title="tests", rows="100", cols="10")
        sheet_tests.append_row(["Тестийн нэр", "Төрөл", "Асуулт", "Сонголтууд", "Үүсгэсэн огноо"])

    # Мэдээ мэдээллийн хуудас
    try:
        sheet_news = spreadsheet.worksheet("news")
    except Exception:
        sheet_news = spreadsheet.add_worksheet(title="news", rows="100", cols="5")
        sheet_news.append_row(["Гарчиг", "Агуулга", "Огноо", "Нийтэлсэн"])

    # Зайн сургалтын хуудас
    try:
        sheet_courses = spreadsheet.worksheet("courses")
    except Exception:
        sheet_courses = spreadsheet.add_worksheet(title="courses", rows="100", cols="6")
        sheet_courses.append_row(["Гарчиг", "Таргет", "Хичээлийн_холбоос", "Тайлбар", "Үүсгэсэн_огноо"])

except Exception as e:
    st.error(f"Google Sheets холболтын алдаа: {e}")

# --- 2. 9 САРЫН 1-НД АНГИ АХИУЛАХ & АРХИВЛАХ АВТОМАТ ЛОГИК ---
def auto_update_grades():
    """9 сарын 1 гарахад сурагчдын ангийг +1 ахиулах, 12-р анги төгссөн бол Архивлах"""
    try:
        now = datetime.now()
        current_year = now.year
        academic_year = current_year if now.month >= 9 else current_year - 1

        all_users = sheet_users.get_all_records()
        for idx, user in enumerate(all_users, start=2):
            role = str(user.get("Үүрэг") or user.get("Хэн") or "")
            status = str(user.get("Төлөв", "Идэвхтэй"))
            
            if role == "Сурагч" and status == "Идэвхтэй":
                last_updated_year = int(user.get("Шинэчлэгдсэн_жил") or 0)
                grade = int(user.get("Анги") or 0)

                if grade > 0 and last_updated_year < academic_year:
                    new_grade = grade + 1
                    if new_grade > 12:
                        sheet_users.update_cell(idx, 9, "Төгссөн")
                    else:
                        sheet_users.update_cell(idx, 7, new_grade)
                        sheet_users.update_cell(idx, 10, academic_year)
    except Exception:
        pass

auto_update_grades()

# --- 3. TELEGRAM МЭДЭГДЭЛ ИЛГЭЭХ ФУНКЦ ---
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

# --- 4. МЭДРЭМЖИЙН АНАЛИЗ ХИЙХ ФУНКЦ ---
def analyze_feeling(text_input, selected_mood):
    text_lower = text_input.lower()
    if any(w in text_lower for w in ["ядарч", "цуцаж", "унтмаар", "сульдаж"]):
        return "Ядарсан / Сульдсан"
    elif any(w in text_lower for w in ["айж", "сандарч", "түгшиж", "бүтэхгүй"]):
        return "Түгшүүртэй / Сандарсан"
    elif any(w in text_lower for w in ["уурлаж", "ууртай", "бухимдаж", "дургүй"]):
        return "Ууртай / Бухимдалтай"
    elif any(w in text_lower for w in ["гомдож", "гуниглаж", "хэцүү", "ганцаардаж"]):
        return "Гунигтай / Сэтгэлээр унасан"
    elif any(w in text_lower for w in ["баяртай", "сайхан", "жаргалтай", "гоё"]):
        return "Баяртай / Урам зоригтой"
    else:
        return selected_mood

def get_student_info(username):
    try:
        all_users = sheet_users.get_all_records()
        for u in all_users:
            if str(u.get("Нэр", "")).strip() == username.strip():
                return u
    except Exception:
        pass
    return {}

def calculate_verification_code(phone_num):
    digits_only = ''.join(filter(str.isdigit, str(phone_num)))
    last_4 = int(digits_only[-4:]) if len(digits_only) >= 4 else 1234
    now = datetime.now()
    day_sum = now.month + now.day
    return str((last_4 * 2) + day_sum)

# --- 5. SESSION STATE ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_grade" not in st.session_state:
    st.session_state.user_grade = None
if "user_group" not in st.session_state:
    st.session_state.user_group = None
if "child_phone" not in st.session_state:
    st.session_state.child_phone = None

# --- 6. CSS ДИЗАЙН ---
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
    section[data-testid="stSidebar"] { background-color: #1E4620 !important; }
    section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
    .cert-box {
        border: 8px double #1B5E20;
        padding: 30px;
        text-align: center;
        background-color: #F9FFF9;
        border-radius: 12px;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 7. НЭВТРЭХ БОЛОН БҮРТГҮҮЛЭХ ---
if st.session_state.current_user is None:
    st.title("🧠 FourMind - Эрүүл сэтгэл зүй, Эрүүл ирээдүй")
    tab1, tab2 = st.tabs(["🔑 Нэвтрэх", "📝 Шинээр бүртгүүлэх"])
    
    with tab1:
        st.subheader("Системд нэвтрэх")
        l_name = st.text_input("Хэрэглэгчийн нэр:", key="login_username")
        l_pass = st.text_input("Нууц үг:", type="password", key="login_pass_field")
        
        if st.button("Нэвтрэх", key="login_submit_btn"):
            if l_name and l_pass:
                try:
                    all_rows = sheet_users.get_all_values()
                    user_found = None
                    if len(all_rows) > 1:
                        for row in all_rows[1:]:
                            if not row or len(row) < 3:
                                continue
                            
                            u_name = str(row[0]).strip()
                            u_pass = str(row[1]).strip()
                            u_role = str(row[2]).strip()
                            
                            if u_name == l_name.strip() and u_pass == l_pass.strip():
                                u_status = str(row[8]).strip() if len(row) > 8 else "Идэвхтэй"
                                if u_status == "Төгссөн":
                                    st.error("❌ Энэ бүртгэл сургууль төгссөн тул идэвхгүй болсон байна.")
                                    break
                                
                                user_found = {
                                    "Нэр": u_name, 
                                    "Үүрэг": u_role if u_role else "Сурагч",
                                    "Анги": row[6] if len(row) > 6 else "",
                                    "Бүлэг": row[7] if len(row) > 7 else "",
                                    "Хүүхдийн_утас": row[12] if len(row) > 12 else ""
                                }
                                break
                    
                    if user_found:
                        st.session_state.current_user = user_found["Нэр"]
                        st.session_state.user_role = user_found["Үүрэг"]
                        st.session_state.user_grade = user_found["Анги"]
                        st.session_state.user_group = user_found["Бүлэг"]
                        st.session_state.child_phone = user_found["Хүүхдийн_утас"]
                        st.success(f"Амжилттай нэвтэрлээ! Таны эрх: {user_found['Үүрэг']}")
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
        age = st.number_input("Нас:", min_value=6, max_value=100, value=15, step=1, key="reg_age")
        gender = st.selectbox("Хүйс:", ["Эрэгтэй", "Эмэгтэй"], key="reg_gender")
        phone = st.text_input("Өөрийн утасны дугаар:", key="reg_phone")
        
        child_phone_input, reg_grade, reg_group = "", "", ""
        
        if role in ["Сурагч", "Анги удирдсан багш"]:
            col_g, col_b = st.columns(2)
            with col_g:
                reg_grade = st.selectbox("Анги:" if role == "Сурагч" else "Хариуцсан Анги:", list(range(1, 13)), index=8, key="reg_grade")
            with col_b:
                reg_group = st.selectbox("Бүлэг:" if role == "Сурагч" else "Хариуцсан Бүлэг:", ["А", "Б", "В", "Г", "Д", "Е", "Ж", "З"], key="reg_group")
            if role == "Сурагч":
                child_phone_input = st.text_input("Асран хамгаалагчийн утасны дугаар:", key="reg_parent_phone")
        elif role == "Асран хамгаалагч":
            child_phone_input = st.text_input("Хүүхдийн утасны дугаар:", key="reg_child_phone")

        if st.button("Бүртгүүлэх", key="reg_submit_btn"):
            if first_name and password and phone:
                if role == "Админ" and password != "admin123":
                    st.error("Админы нууц код буруу байна!")
                else:
                    try:
                        academic_year = datetime.now().year if datetime.now().month >= 9 else datetime.now().year - 1
                        sheet_users.append_row([
                            first_name, password, role, f"{last_name} {first_name}", phone, gender, reg_grade, reg_group, "Идэвхтэй", academic_year, age, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), child_phone_input
                        ])
                        st.success("Бүртгэл амжилттай боллоо! '🔑 Нэвтрэх' хэсгээр орно уу.")
                    except Exception as e:
                        st.error(f"Google Sheets-рүү хадгалахад алдаа гарлаа: {e}")
            else:
                st.warning("Мэдээллийг бүрэн бөглөнө үү.")

# --- 8. ҮНДСЭН СИСТЕМ ---
else:
    with st.sidebar:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=120)
        else:
            st.markdown("🏫", unsafe_allow_html=True)

        st.markdown("### **FourMind**")
        st.caption(f"👤 **{st.session_state.current_user}** ({st.session_state.user_role})")
        if st.session_state.user_grade and st.session_state.user_group:
            st.caption(f"🏫 **Анги бүлэг:** {st.session_state.user_grade}-{st.session_state.user_group}")
        st.divider()
        
        menu_items = ["🏠 Нүүр", "🧪 Тестүүд", "🎓 Зайн сургалт", "📝 Өдрийн мэдрэмж", "📰 Мэдээ мэдээлэл", "📅 Цаг захиалга", "📊 Үр дүн", "📈 Судалгаа болон Анализ"]
        
        if st.session_state.user_role == "Асран хамгаалагч":
            menu_items.append("👶 Миний хүүхэд")
            
        menu_items.append("👥 Бүртгэл мэдээлэл")
        menu_items.append("❓ Тусламж")
        
        if st.session_state.user_role in ["Админ", "Анги удирдсан багш"]:
            menu_items.append("⚙️ Тест удирдлага (Админ)")
            
        menu_items.append("⚙️ Тохиргоо")
        
        menu = st.radio("Цэс сонгох:", menu_items)
        
        st.divider()
        if st.button("🚪 Гарах"):
            st.session_state.current_user = None
            st.session_state.user_role = None
            st.session_state.user_grade = None
            st.session_state.user_group = None
            st.session_state.child_phone = None
            st.rerun()

    if menu == "🏠 Нүүр":
        col_logo, col_title = st.columns([1, 4])
        with col_logo:
            if os.path.exists("logo.png"):
                st.image("logo.png", width=100)
            else:
                st.title("🏫")
        with col_title:
            st.title("Дөрөвдүгээр сургуулийн цахим сэтгэл зүйн үйлчилгээнд тавтай морилно уу!")
        st.write("Та зүүн талын цэснээс өөрт хэрэгцээтэй хэсгийг сонгон үйлчлүүлээрэй.")

    # --- 🎓 ЗАЙН СУРГАЛТ БОЛОН БАТЛАМЖ ХЭСЭГ ---
    elif menu == "🎓 Зайн сургалт":
        st.title("🎓 Зайн сэтгэл зүйн сургалтууд & Батламж")
        
        # Админ сургалт оруулах хэсэг
        if st.session_state.user_role == "Админ":
            with st.expander("➕ Шинэ зайн сургалт нэмэх (Админ хэсэг)"):
                c_title = st.text_input("Сургалтын сэдэв / Гарчиг:")
                c_target = st.selectbox("Хэнд зориулсан:", ["Бүгдэд", "Сурагч", "Асран хамгаалагч"])
                c_link = st.text_input("Видео хичээлийн линк (YouTube болон бусад):", placeholder="https://www.youtube.com/watch?v=...")
                c_desc = st.text_area("Сургалтын тайлбар / Зорилго:")
                
                if st.button("💾 Сургалт хадгалах"):
                    if c_title and c_link:
                        try:
                            sheet_courses.append_row([c_title, c_target, c_link, c_desc, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                            st.success("✅ Шинэ зайн сургалт амжилттай нэмэгдлээ!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Алдаа гарлаа: {e}")
                    else:
                        st.warning("Гарчиг болон линкийг заавал оруулна уу.")
            st.divider()

        # Сургалтуудыг харуулах
        try:
            courses = sheet_courses.get_all_records()
            filtered_courses = [c for c in courses if c.get("Таргет") in ["Бүгдэд", st.session_state.user_role]]
            
            if filtered_courses:
                for idx, c in enumerate(filtered_courses):
                    st.subheader(f"📖 {c.get('Гарчиг')} ({c.get('Таргет')}-д зориулсан)")
                    st.write(c.get("Тайлбар"))
                    
                    link = c.get("Хичээлийн_холбоос", "")
                    if "youtube.com" in link or "youtu.be" in link:
                        st.video(link)
                    else:
                        st.markdown(f"🔗 [Энд дарж хичээл үзнэ үү]({link})")
                    
                    # Батламж авах хэсэг
                    if st.button(f"📜 'Course #{idx+1}' Сургалт дуусгаж Батламж авах", key=f"cert_btn_{idx}"):
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        st.balloons()
                        st.markdown(f"""
                        <div class="cert-box">
                            <h2>🎓 БАТЛАМЖ</h2>
                            <p>Сэтгэл зүйн зайн сургалт амжилттай дүүргэсэн тул</p>
                            <h3><b>{st.session_state.current_user}</b></h3>
                            <p>түүнд <b>"{c.get('Гарчиг')}"</b> сэдэвт сэтгэл зүйн сургалтыг амжилттай суралцаж дүүргэснийг батлан эгүүлэв.</p>
                            <br>
                            <p><b>Огноо:</b> {today_str}</p>
                            <p><b>Дөрөвдүгээр Сургуулийн Сэтгэл Зүйн Төв</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown("---")
            else:
                st.info("Одоогоор идэвхтэй зайн сургалт байхгүй байна.")
        except Exception as e:
            st.error(f"Сургалтын мэдээлэл авахад алдаа гарлаа: {e}")

    # --- 📰 МЭДЭЭ МЭДЭЭЛЭЛ ХЭСЭГ ---
    elif menu == "📰 Мэдээ мэдээлэл":
        st.title("📰 Зөвлөмж & Мэдээ мэдээлэл")

        if st.session_state.user_role == "Админ":
            with st.expander("➕ Шинэ мэдээ, зөвлөмж нэмэх (Админ хэсэг)"):
                news_title = st.text_input("Мэдээний гарчиг:")
                news_content = st.text_area("Агуулга / Сэтгэл зүйн зөвлөмж:")
                
                if st.button("Шууд нийтлэх"):
                    if news_title and news_content:
                        try:
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sheet_news.append_row([news_title, news_content, now_str, st.session_state.current_user])
                            st.success("Мэдээ амжилттай нийтлэгдлээ!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Алдаа гарлаа: {e}")
                    else:
                        st.warning("Гарчиг болон агуулгыг бүрэн бөглөнө үү.")
            st.divider()

        try:
            news_list = sheet_news.get_all_records()
            if news_list:
                for n in reversed(news_list):
                    with st.container():
                        st.subheader(f"📌 {n.get('Гарчиг')}")
                        st.caption(f"🗓 Огноо: {n.get('Огноо')} | 👤 Нийтэлсэн: {n.get('Нийтэлсэн')}")
                        st.write(n.get('Агуулга'))
                        st.markdown("---")
            else:
                st.info("Одоогоор нийтлэгдсэн мэдээ, зөвлөмж байхгүй байна.")
        except Exception as e:
            st.error(f"Мэдээлэл татахад алдаа гарлаа: {e}")

    # --- 👶 АСРАН ХАМГААЛАГЧИД ЗОРИУЛСАН "МИНИЙ ХҮҮХЭД" ХЭСЭГ ---
    elif menu == "👶 Миний хүүхэд":
        st.title("👶 Хүүхдийн сэтгэл зүйн төлөв байдал & Анализ")
        child_phone = st.session_state.child_phone
        if not child_phone:
            st.warning("⚠️ Таны бүртгэлд хүүхдийн утасны дугаар холбогдоогүй байна.")
        else:
            try:
                all_users = sheet_users.get_all_records()
                child_user = None
                for u in all_users:
                    u_phone = str(u.get("Утасны дугаар") or u.get("Утас") or "").strip()
                    if u_phone and u_phone == str(child_phone).strip():
                        child_user = u
                        break
                        
                if child_user:
                    c_name = child_user.get("Нэр")
                    c_grade = child_user.get("Анги")
                    c_group = child_user.get("Бүлэг")
                    
                    st.success(f"👨‍👩‍👧 **Холбогдсон хүүхэд:** {c_name} ({c_grade}-{c_group} бүлэг)")
                    tab_c_feel, tab_c_test = st.tabs(["📊 Мэдрэмжийн төлөв", "📝 Тестийн үр дүн"])
                    
                    with tab_c_feel:
                        if sheet_feelings:
                            f_records = sheet_feelings.get_all_records()
                            df_f = pd.DataFrame(f_records)
                            if not df_f.empty and "Нэр" in df_f.columns:
                                df_child_f = df_f[df_f["Нэр"].astype(str) == str(c_name)]
                                if not df_child_f.empty:
                                    st.subheader("📊 Хүүхдийн сүүлийн үеийн мэдрэмжийн харьцаа:")
                                    st.bar_chart(df_child_f["Шинжилсэн_төлөв"].value_counts())
                                else:
                                    st.info("Хүүхэд одоогоор мэдрэмжийн тэмдэглэл бичээгүй байна.")
                                    
                    with tab_c_test:
                        res_records = sheet_results.get_all_records()
                        df_r = pd.DataFrame(res_records)
                        if not df_r.empty and "Нэр" in df_r.columns:
                            df_child_r = df_r[df_r["Нэр"].astype(str) == str(c_name)]
                            if not df_child_r.empty:
                                st.subheader("📋 Бөглөсөн тестүүдийн жагсаалт:")
                                st.dataframe(df_child_r)
                            else:
                                st.info("Хүүхэд одоогоор тест бөглөөгүй байна.")
                else:
                    st.error(f"❌ Холбогдсон дугаартай ({child_phone}) сурагч одоогоор системд бүртгэгдээгүй байна.")
            except Exception as e:
                st.error(f"Алдаа гарлаа: {e}")

    # --- ⚙️ АДМИНЫ ТЕСТ УДИРДЛАГА ХЭСЭГ ---
    elif menu == "⚙️ Тест удирдлага (Админ)":
        st.title("⚙️ Админы тест болон асуулга удирдах хэсэг")
        st.info("Энд админ шинэ тест оруулах бөгөөд оруулангуут '🧪 Тестүүд' хэсэгт автоматаар харагдана.")
        
        tab_add, tab_list = st.tabs(["➕ Шинэ тест нэмэх", "📋 Үүсгэсэн тестүүдийн жагсаалт"])
        
        with tab_add:
            with st.form("admin_create_test"):
                t_name = st.text_input("Тестийн нэр/Гарчиг:", placeholder="Жишээ: 9-р ангийн сэтгэл түгшилтийн сорил")
                t_type = st.selectbox("Тестийн төрөл:", ["🔒 Заавал бөглөх оношилгоо", "🔓 Нээлттэй тест (Сонголтоор)"])
                t_question = st.text_area("Асуултын бичвэр:", placeholder="Жишээ: Та сүүлийн үед хичээлдээ анхаарал тавьж чадаж байна уу?")
                t_options = st.text_input("Хариултын сонголтууд (Таслалаар тусгаарлана уу):", value="Үгүй, Магадгүй, Тийм")
                
                if st.form_submit_button("💾 Тест хадгалах"):
                    if t_name and t_question:
                        try:
                            sheet_tests.append_row([
                                t_name, t_type, t_question, t_options, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ])
                            st.success("✅ Шинэ тест амжилттай хадгалагдлаа!")
                        except Exception as e:
                            st.error(f"Хадгалахад алдаа гарлаа: {e}")
                    else:
                        st.warning("Тестийн нэр болон асуултыг заавал бичнэ үү.")
                        
        with tab_list:
            try:
                tests_data = sheet_tests.get_all_records()
                if tests_data:
                    df_tests = pd.DataFrame(tests_data)
                    st.dataframe(df_tests)
                else:
                    st.write("Одоогоор шинээр үүсгэсэн тест байхгүй байна.")
            except Exception as e:
                st.error(f"Мэдээлэл уншихад алдаа гарлаа: {e}")

    # --- 🧪 ТЕСТҮҮД ХЭСЭГ ---
    elif menu == "🧪 Тестүүд":
        st.title("🧪 Сэтгэл зүйн онлайнаар өгөх тестүүд")
        all_tests = []
        try:
            all_tests = sheet_tests.get_all_records()
        except Exception:
            pass

        if not all_tests:
            st.warning("Одоогоор идэвхтэй тест байхгүй байна.")
        else:
            test_names = list(set([t.get("Тестийн нэр") for t in all_tests if t.get("Тестийн нэр")]))
            selected_test_name = st.selectbox("Бөглөх тестээ сонгоно уу:", test_names)
            current_test_questions = [t for t in all_tests if t.get("Тестийн нэр") == selected_test_name]
            
            if current_test_questions:
                test_type = current_test_questions[0].get("Төрөл", "🔓 Нээлттэй тест")
                st.subheader(f"📝 {selected_test_name} ({test_type})")
                
                answers = {}
                with st.form("student_test_form"):
                    for idx, q in enumerate(current_test_questions):
                        q_text = q.get("Асуулт")
                        opts = [o.strip() for o in str(q.get("Сонголтууд", "Үгүй, Тийм")).split(",")]
                        answers[f"q_{idx}"] = st.radio(f"{idx+1}. {q_text}", opts, key=f"q_ans_{idx}")
                    
                    st.divider()
                    user_code_input = ""
                    if "🔒 Заавал" in test_type:
                        st.info("💡 Энэ бол заавал бөглөх тест тул баталгаажуулах кодоо оруулна уу.")
                        user_code_input = st.text_input("Баталгаажуулах кодоо оруулна уу:", type="password")
                    
                    submit_test = st.form_submit_button("📤 Тест дуусгах & Хадгалах")
                    
                    if submit_test:
                        student_info = get_student_info(st.session_state.current_user)
                        user_phone = str(student_info.get("Утасны дугаар") or student_info.get("Утас") or "")
                        user_grade = str(student_info.get("Анги", ""))
                        user_group = str(student_info.get("Бүлэг", ""))

                        if "🔒 Заавал" in test_type:
                            expected_code = calculate_verification_code(user_phone)
                            if user_code_input.strip() != expected_code:
                                st.error("❌ Баталгаажуулах код буруу байна!")
                            else:
                                sheet_results.append_row([
                                    st.session_state.current_user, selected_test_name, str(answers),
                                    "Баталгаажсан", "Кодоор шалгагдсан", user_grade, user_group, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                ])
                                st.success("✅ Тест амжилттай баталгаажиж хадгалагдлаа!")
                        else:
                            sheet_results.append_row([
                                st.session_state.current_user, selected_test_name, str(answers),
                                "Хэвийн", "Нээлттэй сорил", user_grade, user_group, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ])
                            st.success("✅ Сэтгэл зүйн тест амжилттай хадгалагдлаа!")

    # --- 📝 ӨДРИЙН МЭДРЭМЖ ---
    elif menu == "📝 Өдрийн мэдрэмж":
        st.title("📝 Өнөөдрийн мэдрэмжийн тэмдэглэл")
        st.info("💡 Таны бичсэн хувийн тэмдэглэлийг хэн ч харахгүй. Зөвхөн таны мэдрэмжийн ерөнхий төлөвийг нэгтгэн анализдаа ашиглана.")
        
        with st.form("feeling_form"):
            selected_mood = st.selectbox(
                "Өнөөдөр голлон ямар мэдрэмжтэй байна вэ?",
                ["Баяртай / Жаргалтай", "Тайван / Тогтвортой", "Түгшүүртэй / Сандарсан", "Гунигтай / Сэтгэлээр унасан", "Ууртай / Бухимдалтай", "Ядарсан / Сульдсан"]
            )
            diary_text = st.text_area("Өнөөдөр юу тохиолдсон бэ? (Товч бичнэ үү):", placeholder="Энд бичсэн бичвэр нууцлагдана...")
            
            if st.form_submit_button("💾 Мэдрэмж хадгалах"):
                analyzed_state = analyze_feeling(diary_text, selected_mood)
                if sheet_feelings:
                    try:
                        student_info = get_student_info(st.session_state.current_user)
                        user_grade = str(student_info.get("Анги", ""))
                        user_group = str(student_info.get("Бүлэг", ""))
                        
                        sheet_feelings.append_row([
                            st.session_state.current_user, selected_mood, analyzed_state,
                            user_grade, user_group, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ])
                        st.success(f"Амжилттай хадгалагдлаа! Таны өнөөдрийн голлон мэдэрсэн мэдрэмж: **{analyzed_state}** байна.")
                    except Exception as e:
                        st.error(f"Хадгалахад алдаа гарлаа: {e}")

    # --- 📈 СУДАЛГАА БОЛОН АНАЛИЗ ---
    elif menu == "📈 Судалгаа болон Анализ":
        st.title("📈 Сэтгэл зүй & Мэдрэмжийн нэгдсэн статистик")
        is_teacher = (st.session_state.user_role == "Анги удирдсан багш")
        t_grade = str(st.session_state.user_grade or "")
        t_group = str(st.session_state.user_group or "")
        
        if is_teacher:
            st.success(f"🏫 **Таны хариуцсан анги:** {t_grade}-{t_group} бүлэг")
        else:
            st.info("Энд сурагчдын бөглөсөн тест болон өдрийн мэдрэмжийн нэгдсэн дашборд харагдана.")
        
        tab_feel, tab_res = st.tabs(["📊 Мэдрэмжийн статистик", "📝 Тестийн нэгдсэн үр дүн"])
        
        with tab_feel:
            if sheet_feelings:
                try:
                    records = sheet_feelings.get_all_records()
                    if records:
                        df = pd.DataFrame(records)
                        if is_teacher and "Анги" in df.columns and "Бүлэг" in df.columns:
                            df = df[(df["Анги"].astype(str) == t_grade) & (df["Бүлэг"].astype(str) == t_group)]
                        if not df.empty and "Шинжилсэн_төлөв" in df.columns:
                            st.subheader(f"📊 Мэдрэмжийн харьцаа ({len(df)} бичлэг)")
                            st.bar_chart(df["Шинжилсэн_төлөв"].value_counts())
                        else:
                            st.warning("Тухайн ангид хамаарах дата одоогоор байхгүй байна.")
                    else:
                        st.write("Одоогоор мэдрэмжийн дата байхгүй байна.")
                except Exception as e:
                    st.error(f"Алдаа: {e}")
                    
        with tab_res:
            try:
                res_records = sheet_results.get_all_records()
                if res_records:
                    df_res = pd.DataFrame(res_records)
                    if is_teacher and "Анги" in df_res.columns and "Бүлэг" in df_res.columns:
                        df_res = df_res[(df_res["Анги"].astype(str) == t_grade) & (df_res["Бүлэг"].astype(str) == t_group)]
                    if not df_res.empty:
                        st.subheader("📋 Бөглөгдсөн тестүүдийн жагсаалт")
                        st.dataframe(df_res)
                    else:
                        st.warning("Тухайн ангид бөглөгдсөн тестийн үр дүн байхгүй байна.")
                else:
                    st.write("Бөглөсөн тестийн үр дүн байхгүй байна.")
            except Exception as e:
                st.error(f"Алдаа: {e}")

    # --- 👥 БҮРТГЭЛ МЭДЭЭЛЭЛ ---
    elif menu == "👥 Бүртгэл мэдээлэл":
        st.title("👥 Сурагчдын бүртгэл & Ангийн жагсаалт")
        if st.session_state.user_role in ["Админ", "Анги удирдсан багш"]:
            try:
                all_users = sheet_users.get_all_records()
                if all_users:
                    df_u = pd.DataFrame(all_users)
                    if st.session_state.user_role == "Анги удирдсан багш":
                        t_grade = str(st.session_state.user_grade or "")
                        t_group = str(st.session_state.user_group or "")
                        if "Анги" in df_u.columns and "Бүлэг" in df_u.columns:
                            df_u = df_u[(df_u["Анги"].astype(str) == t_grade) & (df_u["Бүлэг"].astype(str) == t_group)]
                            st.subheader(f"🏫 Таны {t_grade}-{t_group} ангийн сурагчдын жагсаалт:")
                    else:
                        st.subheader("🏫 Системийн нэгдсэн хэрэглэгчдийн жагсаалт:")

                    cols_to_drop = [c for c in ["Нууц үг"] if c in df_u.columns]
                    if cols_to_drop:
                        df_u = df_u.drop(columns=cols_to_drop)
                    st.dataframe(df_u)
                else:
                    st.info("Бүртгэлтэй хэрэглэгч байхгүй байна.")
            except Exception as e:
                st.error(f"Мэдээлэл авахад алдаа гарлаа: {e}")
        else:
            st.warning("🔒 Энэ хэсэгт зөвхөн Сургуулийн админ болон Анги удирдсан багш нар нэвтрэх боломжтой.")

    # --- 📅 ЦАГ ЗАХИАЛГА ---
    elif menu == "📅 Цаг захиалга":
        st.title("📅 Сэтгэл зүйн ганцаарчилсан зөвлөгөөний цаг захиалах")
        with st.form("booking_form"):
            b_date = st.date_input("Огноо сонгох:")
            b_time = st.time_input("Цаг сонгох:")
            b_reason = st.text_area("Уулзах шалтгаан / Товч утга:")
            if st.form_submit_button("📅 Цагаа баталгаажуулах"):
                st.success(f"Амжилттай! {b_date}-ний {b_time} цагт цаг захиаллаа.")

    # --- ❓ ТУСЛАМЖ ---
    elif menu == "❓ Тусламж":
        st.title("🆘 Одоо л сэтгэлдээ туслах цаг")
        st.warning("Яаралтай мэргэжлийн дэмжлэг шаардлагатай үед доорх маягтыг бөглөнө үү.")
        
        with st.form("sos_form"):
            contact_phone = st.text_input("Холбоо барих утасны дугаар:")
            sos_message = st.text_area("Мэдээлэл / Нөхцөл байдал:")
            
            if st.form_submit_button("🚨 Тусламжийн хүсэлтээ илгээх"):
                if contact_phone and sos_message:
                    success = send_telegram_alert(
                        student_name=st.session_state.current_user,
                        phone_number=contact_phone,
                        message_text=sos_message
                    )
                    if success:
                        st.success("Мэдээлэл сэтгэл зүйчид илгээгдлээ! Боломжит хамгийн богино хугацаанд холбогдох болно.")
                else:
                    st.warning("Утасны дугаар болон мэдээллээ бүрэн бөглөнө үү.")

    # --- ⚙️ ТОХИРГОО ---
    elif menu == "⚙️ Тохиргоо":
        st.title("⚙️ Хэрэглэгчийн тохиргоо")
        st.write(f"**Хэрэглэгчийн нэр:** {st.session_state.current_user}")
        st.write(f"**Эрх:** {st.session_state.user_role}")
        if st.session_state.user_grade and st.session_state.user_group:
            st.write(f"**Анги бүлэг:** {st.session_state.user_grade}-{st.session_state.user_group}")
        st.divider()
        
        st.subheader("🔑 Нууц үг өөрчлөх")
        with st.form("pass_change"):
            old_p = st.text_input("Одоогийн нууц үг:", type="password")
            new_p = st.text_input("Шинэ нууц үг:", type="password")
            confirm_p = st.text_input("Шинэ нууц үг баталгаажуулах:", type="password")
            
            if st.form_submit_button("Нууц үг шинэчлэх"):
                if new_p and new_p == confirm_p:
                    try:
                        all_users = sheet_users.get_all_records()
                        user_row_idx = None
                        for idx, u in enumerate(all_users, start=2):
                            if str(u.get("Нэр", "")).strip() == st.session_state.current_user.strip():
                                if str(u.get("Нууц үг", "")).strip() == old_p.strip():
                                    user_row_idx = idx
                                    break
                        
                        if user_row_idx:
                            sheet_users.update_cell(user_row_idx, 2, new_p)
                            st.success("✅ Нууц үг амжилттай шинэчлэгдлээ.")
                        else:
                            st.error("❌ Одоогийн нууц үг буруу байна!")
                    except Exception as e:
                        st.error(f"Алдаа гарлаа: {e}")
                else:
                    st.error("❌ Шинэ нууц үг зөрж байна.")