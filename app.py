import streamlit as st
import datetime
import pandas as pd
import random
import string
import time
import io
import os

# --- 1. ХУУДАСНЫ ТОХИРГОО БОЛОН ЛОГОНЫ ӨНГӨ СТИЛЬ ---
st.set_page_config(page_title="MindCare - Сэтгэл Зүйн Дэмжлэг", layout="wide")

# Логоны өнгөнд тохируулсан CSS дизайн (Ногоон & Шар туяа)
st.markdown("""
    <style>
    .main-header { font-size:24px; font-weight:bold; color:#2E7D32; }
    .stButton>button { background-color: #4CAF50; color: white; border-radius: 8px; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #388E3C; color: white; }
    .card-box { background-color: #F1F8E9; padding: 15px; border-radius: 12px; border-left: 5px solid #8BC34A; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. СИСТЕМ ДЭЭРХ ӨГӨГДӨЛ ХАДГАЛАХ САН (SESSION STATE) ---
if "users_db" not in st.session_state:
    st.session_state.users_db = []
if "logs_db" not in st.session_state:
    st.session_state.logs_db = []
if "emergency_alerts" not in st.session_state:
    st.session_state.emergency_alerts = []
if "anonymous_feedbacks" not in st.session_state:
    st.session_state.anonymous_feedbacks = []
if "courses_list" not in st.session_state:
    st.session_state.courses_list = [
        {"Сэдэв": "Стрессээ удирдах нь", "Линк": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    ]
if "course_completions" not in st.session_state:
    st.session_state.course_completions = []
if "group_test_code" not in st.session_state:
    st.session_state.group_test_code = "MIND2026"
if "tests_db" not in st.session_state:
    st.session_state.tests_db = [
        {"id": "T1", "title": "Мэргэжил, ажлаа зөв сонгох — Дж.Холландын тест", "category": "Мэргэжил сонголт", "questions": ["Та багаж зэмсэгтэй ажиллах дуртай юу?", "Та хүмүүст туслах дуртай юу?", "Та логик тооцоолол хийх дуртай юу?"]},
        {"id": "T2", "title": "DASS-21 — Сэтгэл гутрал, Түгшүүр, Стрессийн хэмжүүр", "category": "Сэтгэл зүй", "questions": ["Шалтгаангүйгээр айж түгших мэдрэмж төрдөг үү?", "Тайвширч чадахгүй бухимдах үе гардаг уу?", "Ирээдүйдээ итгэлгүй санагддаг уу?"]},
        {"id": "T3", "title": "MBTI Хувь хүний зан төлөвийг тодорхойлох тест", "category": "Зан төлөв", "questions": ["Олон хүнтэй орчинд эрч хүч авдаг уу?", "Шийдвэр гаргахдаа зөн билэгтээ итгэдэг үү?"]}
    ]
if "test_results_db" not in st.session_state:
    st.session_state.test_results_db = [
        {"Хэрэглэгч": "Баатар", "Анги": "10А", "Тест": "DASS-21 — Сэтгэл гутрал, Түгшүүр", "Үр дүн": "Сэтгэл гутрал: Дунд зэрэг", "Огноо": "2026/08/12 14:30"},
        {"Хэрэглэгч": "Дулмаа", "Анги": "10А", "Тест": "Мэргэжил сонгох — Холланд", "Үр дүн": "Уран сайхны хэв шинж", "Огноо": "2026/08/12 15:10"}
    ]
if "consultations_db" not in st.session_state:
    st.session_state.consultations_db = []
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# --- 3. ТУСЛАХ БОЛОН АНАЛИЗЫН ФУНКЦҮҮД ---
def get_dynamic_age(reg_date_str, initial_age):
    reg_date = datetime.datetime.strptime(reg_date_str, "%Y-%m-%d").date()
    return initial_age + ((datetime.date.today() - reg_date).days // 365)

def get_dynamic_grade(reg_date_str, current_grade):
    try: grade_num = int(current_grade)
    except: return current_grade
    reg_date = datetime.datetime.strptime(reg_date_str, "%Y-%m-%d").date()
    today = datetime.date.today()
    years_passed = sum(1 for y in range(reg_date.year, today.year + 1) if reg_date < datetime.date(y, 8, 25) <= today)
    return "Төгссөн" if grade_num + years_passed > 12 else str(grade_num + years_passed)

def log_action(action_name):
    if st.session_state.current_user and st.session_state.user_role != "Админ":
        username = "Нэргүй Сурагч" if action_name == "Нэргүй санал хүсэлт илгээсэн" else st.session_state.current_user
        user_grade = next((u.get("Анги", "") for u in st.session_state.users_db if u["Нэр"] == st.session_state.current_user), "")
        st.session_state.logs_db.append({
            "Хэрэглэгч": username, "Үүрэг": st.session_state.user_role, "Анги": user_grade,
            "Үйлдэл/Цэс": action_name, "Хугацаа": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

def analyze_mood(text):
    text_lower = text.lower()
    if any(word in text_lower for word in ["гуниг", "уур", "ядарч", "хэцүү", "ганцаард", "айж", "нут"]):
        return {"Баяр баясгалан": "15%", "Стресс/Түгшүүр": "65%", "Амар тайван": "20%", "Төлөв": "⚠️ Сэтгэл зүйн дэмжлэг шаардлагатай байж болзошгүй"}
    elif any(word in text_lower for word in ["баяртай", "гоё", "сайхан", "амжилт", "баярлалаа", "гомдолгүй"]):
        return {"Баяр баясгалан": "75%", "Стресс/Түгшүүр": "10%", "Амар тайван": "15%", "Төлөв": "🌟 Эерэг баяртай мэдрэмж өндөр байна"}
    else:
        return {"Баяр баясгалан": "40%", "Стресс/Түгшүүр": "25%", "Амар тайван": "35%", "Төлөв": "🟢 Дундаж, тогтвортой мэдрэмжтэй байна"}

def analyze_consultation(notes_text):
    text = notes_text.lower()
    if any(w in text for w in ["хүчирхийлэл", "амиа хорлох", "гэр бүлийн асуудал", "гутрал", "гүн айдас", "шаналж"]):
        risk_level = "🔴 ӨНДӨР ЭРСДЭЛТЭЙ"
        rec = "Нэн даруй сургуулийн захиргаа, эцэг эх болон мэргэжлийн сэтгэл засалчид мэдээлэх шаардлагатай."
        t_rec = "Сурагчийн сэтгэл зүйд дарамт болох хүчин зүйлийг багасгаж, халамж анхаарал тавих."
    elif any(w in text for w in ["хичээл хоцрогдол", "найзын маргаан", "бухимдал", "ядарч", "уурлаж"]):
        risk_level = "🟡 ДУНД СЭРЭМЖТЭЙ"
        rec = "1-2 долоо хоногийн дараа давтан уулзаж, сэтгэл зүйн идэвхийг нь дэмжих дасгал даалгах."
        t_rec = "Анги танхимын уур амьсгалд татан оролцуулж, эерэг урамшуулал өгөх."
    else:
        risk_level = "🟢 ХЭВИЙН / ЭРСДЭЛ БАГА"
        rec = "Сурагчийн сэтгэл зүйн байдал тогтвортой байна. Тогтмол уулзалтаа үргэлжлүүлэх."
        t_rec = "Одоогоор онцгой анхаарах шаардлагагүй, сургалтын хэвийн үйл ажиллагааг дэмжих."

    return risk_level, rec, t_rec

# --- 4. ХАЖУУГИЙН МЕНЮ БОЛОН ЛОГО ---
logo_path = "04a88c0f-377e-4245-ac3c-29afcc8c01c0 - Copy.jpg"
with st.sidebar:
    if os.path.exists(logo_path):
        st.image(logo_path, width=130)
    else:
        st.title("🟢 MindCare")
    
    if st.session_state.current_user:
        st.write(f"👤 **{st.session_state.current_user}** ({st.session_state.user_role})")
        if st.button("🚪 Системээс гарах", key="logout_btn"):
            st.session_state.current_user = None
            st.session_state.user_role = None
            st.rerun()

# ==================== 5. БҮРТГҮҮЛЭХ БОЛОН НЭВТРЭХ ====================
if st.session_state.current_user is None:
    st.title("🧠 MindCare - Сэтгэл зүй, Эрүүл ирээдүй")
    tab1, tab2 = st.tabs(["🔑 Нэвтрэх", "📝 Шинээр бүртгүүлэх"])
    
    with tab2:
        st.subheader("Шинэ бүртгэл үүсгэх")
        role = st.selectbox("Та хэн бэ?", ["Сурагч", "Анги удирдсан багш", "Асран хамгаалагч", "Админ"], key="reg_role")
        last_name = st.text_input("Овог:", key="reg_lname")
        first_name = st.text_input("Нэр:", key="reg_fname")
        password = st.text_input("Нууц үг үүсгэх:", type="password", key="reg_pass_field")
        gender = st.selectbox("Хүйс:", ["Эрэгтэй", "Эмэгтэй"], key="reg_gender")
        phone = st.text_input("Утасны дугаар:", key="reg_phone")
        
        extra_info = {}
        if role == "Сурагч":
            extra_info = {
                "Нас": st.number_input("Нас:", min_value=6, max_value=20, value=15, key="reg_age"),
                "Анги": st.selectbox("Анги:", [str(i) for i in range(1, 13)], key="reg_grade"),
                "Бүлэг": st.selectbox("Бүлэг:", ["А", "Б", "В", "Г", "Д"], key="reg_sec")
            }
        elif role == "Асран хамгаалагч":
            extra_info = {
                "Нас": st.number_input("Нас:", min_value=20, max_value=80, value=40, key="p_age"),
                "Яаралтай_утас": st.text_input("Яаралтай утас:", key="p_em_phone"),
                "Хүүхдийн_утас": st.text_input("Хүүхдийн утасны дугаар:", key="p_c_phone")
            }
        elif role == "Анги удирдсан багш":
            extra_info = {
                "Анги": st.selectbox("Удирдсан анги:", [str(i) for i in range(1, 13)], key="t_grade"),
                "Бүлэг": st.selectbox("Удирдсан бүлэг:", ["А", "Б", "В", "Г", "Д"], key="t_sec")
            }

        if st.button("Бүртгүүлэх", key="reg_submit_btn"):
            if first_name and password and phone:
                if role == "Админ" and password != "admin123":
                    st.error("Админы нууц код буруу байна!")
                else:
                    user_data = {
                        "Нэр": first_name, "Овог": last_name, "Нууц үг": password, 
                        "Үүрэг": role, "Хүйс": gender, "Утас": phone, "Бүртгүүлсэн_огноо": str(datetime.date.today())
                    }
                    user_data.update(extra_info)
                    st.session_state.users_db.append(user_data)
                    st.success("Бүртгэл амжилттай боллоо! Нэвтрэх хэсгээр орно уу.")
            else: st.warning("Мэдээллийг бүрэн бөглөнө үү.")
                
    with tab1:
        st.subheader("Системд нэвтрэх")
        l_name = st.text_input("Хэрэглэгчийн нэр:", key="login_username")
        l_pass = st.text_input("Нууц үг:", type="password", key="login_pass_field")
        
        if st.button("Нэвтрэх", key="login_submit_btn"):
            user_found = next((u for u in st.session_state.users_db if u["Нэр"] == l_name and u["Нууц үг"] == l_pass), None)
            if user_found:
                st.session_state.current_user = user_found["Нэр"]
                st.session_state.user_role = user_found["Үүрэг"]
                st.rerun()
            else: st.error("Нэр эсвэл нууц үг буруу байна.")

# ==================== 6. НЭВТЭРСНИЙ ДАРААХ СИСТЕМ ====================
else:
    for u in st.session_state.users_db:
        if "Бүртгүүлсэн_огноо" in u:
            if "Нас" in u: u["Нас"] = get_dynamic_age(u["Бүртгүүлсэн_огноо"], u["Нас"])
            if "Анги" in u: u["Анги"] = get_dynamic_grade(u["Бүртгүүлсэн_огноо"], u["Анги"])

    # ---------------- 👑 АДМИН / СЭТГЭЛ ЗҮЙЧИЙН ХЭСЭГ ----------------
    if st.session_state.user_role == "Админ":
        st.title("🖥️ Админы Нэгдсэн Удирдлагын Самбар")
        
        tab_a1, tab_a2, tab_a3, tab_a4, tab_a5, tab_a6 = st.tabs([
            "📊 Хяналт & Дохио", 
            "📝 Зөвлөгөөний Тэмдэглэл",
            "📝 Тестийн удирдлага & Код", 
            "📈 Тестийн үр дүн", 
            "📺 Сургалтын удирдлага", 
            "📥 Татан авах"
        ])
        
        with tab_a1:
            col_chart, col_alerts = st.columns([3, 2])
            with col_chart:
                st.subheader("📊 Системийн хандалт")
                if st.session_state.logs_db:
                    df = pd.DataFrame(st.session_state.logs_db)
                    st.bar_chart(df["Үйлдэл/Цэс"].value_counts())
                else: st.info("Хандалтын түүх одоогоор хоосон байна.")
            with col_alerts:
                st.subheader("🆘 Яаралтай тусламжийн дохио")
                if st.session_state.emergency_alerts:
                    st.dataframe(pd.DataFrame(st.session_state.emergency_alerts))
                else: st.success("Яаралтай дохио ирээгүй байна.")
                
                st.subheader("🕵️ Нэргүй санал хүсэлтүүд")
                if st.session_state.anonymous_feedbacks:
                    for fb in st.session_state.anonymous_feedbacks:
                        st.warning(f"📩 {fb['Огноо']}: {fb['Мэдээлэл']}")
                else: st.info("Нэргүй санал ирээгүй байна.")

        with tab_a2:
            st.subheader("📋 Сэтгэл зүйн зөвлөгөөний уулзалтын тэмдэглэл & Автомат Дүгнэлт")
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                c_student = st.text_input("Сурагчийн нэр:", key="cons_student")
                c_grade = st.selectbox("Анги:", [f"{i}{sec}" for i in range(1,13) for sec in ["А","Б","В","Г"]], key="cons_grade")
            with col_c2:
                c_topic = st.text_input("Зөвлөгөөний сэдэв:", key="cons_topic")
                c_date = st.date_input("Уулзсан огноо:", datetime.date.today(), key="cons_date")

            c_notes = st.text_area("Ярилцсан зүйлс болон ажиглалтын тэмдэглэл (Нууцлалтай):", height=120, key="cons_notes")

            if st.button("📊 Дүгнэлт гаргуулах & Хадгалах", key="save_cons_btn"):
                if c_student and c_notes:
                    risk, rec, t_rec = analyze_consultation(c_notes)
                    st.session_state.consultations_db.append({
                        "Сурагч": c_student, "Анги": c_grade, "Огноо": str(c_date),
                        "Сэдэв": c_topic, "Тэмдэглэл": c_notes, "Эрсдэл": risk,
                        "Зөвлөмж": rec, "Багшид_өгөх_зөвлөмж": t_rec
                    })
                    st.success("✅ Тэмдэглэл болон автомат дүгнэлт хадгалагдлаа!")
                    st.write(f"**Сэтгэл зүйн төлөв:** {risk}")
                    st.write(f"**Зөвлөмж:** {rec}")
                else: st.warning("Мэдээллийг бүрэн бичнэ үү.")

            st.divider()
            st.subheader("📂 Бүх уулзалтын дэлгэрэнгүй тэмдэглэлийн сан")
            if st.session_state.consultations_db:
                st.dataframe(pd.DataFrame(st.session_state.consultations_db))
            else: st.info("Тэмдэглэл хараахан бичигдээгүй байна.")

        with tab_a3:
            st.subheader("🔑 Олон сурагч нэгэн дээд нэвтрэх 'Нэгдсэн 1 код'")
            new_code = st.text_input("Нэгдсэн тестийн код тохируулах:", value=st.session_state.group_test_code, key="set_grp_code")
            if st.button("Код шинэчлэх", key="save_grp_code"):
                st.session_state.group_test_code = new_code
                st.success(f"Нэгдсэн шинэ код амжилттай тохируулагдлаа: {new_code}")
                
            st.divider()
            st.subheader("➕ Шинэ тест/асуулга нэмэх")
            t_title = st.text_input("Тестийн нэр:", key="add_t_title")
            t_cat = st.selectbox("Ангилал:", ["Мэргэжил сонголт", "Сэтгэл зүй", "Зан төлөв", "Танин мэдэхүй"], key="add_t_cat")
            t_q1 = st.text_input("Асуулт 1:", key="add_t_q1")
            t_q2 = st.text_input("Асуулт 2:", key="add_t_q2")
            if st.button("Тест нийтлэх", key="save_new_test"):
                if t_title and t_q1:
                    st.session_state.tests_db.append({
                        "id": f"T{len(st.session_state.tests_db)+1}",
                        "title": t_title, "category": t_cat,
                        "questions": [t_q1, t_q2] if t_q2 else [t_q1]
                    })
                    st.success("Шинэ тест амжилттай нэмэгдлээ!")

        with tab_a4:
            st.subheader("📈 Сурагчдын бөглөсөн тестийн нэгдсэн хариунууд")
            if st.session_state.test_results_db:
                st.table(pd.DataFrame(st.session_state.test_results_db))
            else: st.info("Тестийн хариу хараахан бичигдээгүй байна.")

        with tab_a5:
            st.subheader("➕ Шинэ цахим сургалт нэмэх")
            c_title = st.text_input("Сургалтын сэдэв/нэр:", key="new_c_title")
            c_link = st.text_input("YouTube бичлэгийн линк (URL):", key="new_c_link")
            
            if st.button("🎬 Сургалт нэмэх", key="add_course_btn"):
                if c_title and c_link:
                    st.session_state.courses_list.append({"Сэдэв": c_title, "Линк": c_link})
                    st.success(f"'{c_title}' сургалт амжилттай нэмэгдлээ!")
                    st.rerun()
                else: st.warning("Сургалтын нэр болон линкийг бүрэн бичнэ үү.")

            st.divider()
            st.subheader("📋 Одоо байгаа сургалтын жагсаалт (Устгах)")
            if st.session_state.courses_list:
                for idx, course in enumerate(st.session_state.courses_list):
                    col_c1, col_c2 = st.columns([4, 1])
                    col_c1.write(f"📌 **{course['Сэдэв']}** ({course['Линк']})")
                    if col_c2.button("🗑️ Устгах", key=f"del_course_{idx}"):
                        st.session_state.courses_list.pop(idx)
                        st.success("Сургалт устгагдлаа!")
                        st.rerun()
            else: st.info("Сургалт байхгүй байна.")

        with tab_a6:
            st.subheader("📥 Тайлан Excel форматаар татах")
            if st.session_state.users_db:
                df_all = pd.DataFrame(st.session_state.users_db)
                df_all["Нууц үг"] = "********"
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_all.to_excel(writer, sheet_name='Хэрэглэгчид', index=False)
                    if st.session_state.test_results_db:
                        pd.DataFrame(st.session_state.test_results_db).to_excel(writer, sheet_name='Тестийн Хариу', index=False)
                st.download_button("📊 Excel Татах", data=output.getvalue(), file_name="MindCare_Тайлан.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ---------------- 👩‍🏫 АНГИ УДИРДСАН БАГШИЙН ХЭСЭГ ----------------
    elif st.session_state.user_role == "Анги удирдсан багш":
        st.title("👩‍🏫 Анги Удирдсан Багшийн Цонх")
        
        # Багшийн удирддаг ангийг олох
        t_user = next((u for u in st.session_state.users_db if u["Нэр"] == st.session_state.current_user), None)
        t_grade = f"{t_user.get('Анги','')}{t_user.get('Бүлэг','')}" if t_user else "10А"
        
        st.info(f"Та **{t_grade}** ангийг хариуцан ажиллаж байна.")

        tab_t1, tab_t2 = st.tabs(["📌 Сэтгэл зүйн зөвлөмжүүд", "📈 Ангийн тестийн дүн"])
        
        with tab_t1:
            st.subheader("💡 Сэтгэл зүйчээс багшид өгсөн анхаарах зөвлөмжүүд")
            st.caption("🔒 Мэргэжлийн ёс зүйн дагуу сурагчийн ярьсан яриа нууцлагдсан бөгөөд зөвхөн авах арга хэмжээний зөвлөмж харагдана.")
            
            # Ангиар нь шүүж харуулах
            class_cons = [c for c in st.session_state.consultations_db if c.get("Анги") == t_grade]
            if class_cons:
                df_teacher = pd.DataFrame(class_cons)[["Сурагч", "Огноо", "Эрсдэл", "Багшид_өгөх_зөвлөмж"]]
                st.dataframe(df_teacher)
            else:
                st.info(f"Одоогоор {t_grade} ангийн сурагчдаас сэтгэл зүйчтэй ганцаарчлан уулзсан бүртгэл байхгүй байна.")

        with tab_t2:
            st.subheader(f"📈 {t_grade} ангийн сурагчдын бөглөсөн тестүүд")
            class_tests = [tr for tr in st.session_state.test_results_db if tr.get("Анги") == t_grade]
            if class_tests:
                st.table(pd.DataFrame(class_tests)[["Хэрэглэгч", "Тест", "Үр дүн", "Огноо"]])
            else:
                st.info(f"{t_grade} ангийн сурагчдын тестийн үр дүн хараахан бичигдээгүй байна.")

    # ---------------- 👨‍👩‍👦 АСРАН ХАМГААЛАГЧИЙН ХЭСЭГ ----------------
    elif st.session_state.user_role == "Асран хамгаалагч":
        st.title("👨‍👩‍👦 Асран хамгаалагчийн Цонх")
        st.info("Хүүхдийн сэтгэл зүйн зөвлөмж, мэдээллийг хүлээн авах боломжтой.")

    # ---------------- 👦 СУРАГЧИЙН ҮНДСЭН ХЭСЭГ ----------------
    else:
        st.title("🧠 MindCare Сурагчийн Цонх")
        
        menu = st.sidebar.radio("📍 Үндсэн цэс", [
            "🏠 Нүүр", 
            "📝 Өдрийн тэмдэглэл & Мэдрэмж", 
            "🧪 Тестүүд & Асуулга", 
            "📈 Миний тестийн түүх", 
            "📺 Цахим сургалт", 
            "📅 Цаг захиалга", 
            "🕵️ Нэргүй санал хүсэх", 
            "🆘 ТУСЛААРАЙ"
        ])

        if menu == "🏠 Нүүр":
            st.subheader("Өөрөө өөрийгөө таньж, сэтгэл зүйгээ дэмжээрэй! 🌟")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                <div class="card-box">
                    <h3>🧪 Тестүүд бөглөх</h3>
                    <p>Өөрийгөө таньцгаая, сонирхсон тестээ сонгон хамрагдаарай.</p>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.markdown("""
                <div class="card-box">
                    <h3>📝 Мэдрэмжийн тэмдэглэл</h3>
                    <p>Өдөрт тохиолдсон зүйлээ бичиж, сэтгэл хөдлөлийн магадлалаа тодорхойлуулаарай.</p>
                </div>
                """, unsafe_allow_html=True)

        elif menu == "📝 Өдрийн тэмдэглэл & Мэдрэмж":
            log_action("Өдрийн тэмдэглэл цэс рүү орсон")
            st.header("📝 Өдрийн тэмдэглэл & Мэдрэмжийн магадлал")
            st.write("Өнөөдөр танд тохиолдсон үйл явдал, мэдрэмжээ чөлөөтэй бичээрэй. Систем таны мэдрэмжийн магадлалыг тооцоолж өгнө.")
            
            user_text = st.text_area("Өнөөдөр юу тохиолдов?...", height=150, key="diary_input")
            if st.button("Шинжлэгчээр боловсруулах", key="analyze_diary_btn"):
                if user_text:
                    res = analyze_mood(user_text)
                    st.success("Мэдрэмжийн магадлал амжилттай тооцоологдлоо!")
                    st.subheader("📊 Тооцоолсон мэдрэмжийн эзлэх хувь:")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("😊 Баяр баясгалан", res["Баяр баясгалан"])
                    col2.metric("😰 Стресс / Түгшүүр", res["Стресс/Түгшүүр"])
                    col3.metric("🌿 Амар тайван", res["Амар тайван"])
                    st.info(f"**Ерөнхий дүгнэлт:** {res['Төлөв']}")
                else: st.warning("Тэмдэглэлээ бичсэний дараа дарна уу.")

        elif menu == "🧪 Тестүүд & Асуулга":
            log_action("Тестүүд цэс рүү орсон")
            st.header("🧪 Өөрийгөө таньцгаая")
            
            st.subheader("🔑 Нэгдсэн 1 кодоор тестэд нэвтрэх")
            input_code = st.text_input("Админаас өгсөн нэгдсэн кодыг оруулна уу:", key="enter_grp_code")
            
            if input_code:
                if input_code == st.session_state.group_test_code:
                    st.success("✅ Код зөв! Нийтээр бөглөх оноогдсон тест нээгдлээ.")
                else: st.error("❌ Код буруу байна.")
                    
            st.divider()
            st.subheader("Сонирхсон тестээ сонгон хамрагдаарай")
            
            for t in st.session_state.tests_db:
                with st.expander(f"📌 {t['title']} ({t['category']})"):
                    st.write("Асуултууд:")
                    answers = []
                    for idx, q in enumerate(t["questions"]):
                        ans = st.radio(f"{idx+1}. {q}", ["Үгүй / Эргэлзэж байна", "Тийм / Заримдаа", "Маш их / Байнга"], key=f"q_{t['id']}_{idx}")
                        answers.append(ans)
                    
                    if st.button(f"Хариу хадгалах ({t['id']})", key=f"btn_save_{t['id']}"):
                        score = random.choice(["Эрсдэл бага (Хэвийн)", "Дунд зэргийн үзүүлэлттэй", "Өндөр шаардлагатай"])
                        u_info = next((u for u in st.session_state.users_db if u["Нэр"] == st.session_state.current_user), {})
                        u_grade = f"{u_info.get('Анги','')}{u_info.get('Бүлэг','')}"
                        
                        st.session_state.test_results_db.append({
                            "Хэрэглэгч": st.session_state.current_user,
                            "Анги": u_grade,
                            "Тест": t["title"],
                            "Үр дүн": score,
                            "Огноо": datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
                        })
                        st.success(f"Тест амжилттай илгээгдлээ! Үр дүн: {score}")

        elif menu == "📈 Миний тестийн түүх":
            log_action("Тестийн түүх харав")
            st.header("📈 Тестийн түүх болон Үр дүн")
            
            user_results = [r for r in st.session_state.test_results_db if r["Хэрэглэгч"] == st.session_state.current_user]
            if user_results:
                st.table(pd.DataFrame(user_results)[["Тест", "Үр дүн", "Огноо"]])
            else: st.info("Та одоогоор ямар нэгэн тест бөглөөгүй байна.")

        elif menu == "📺 Цахим сургалт":
            log_action("Цахим сургалт цэс рүү орсон")
            st.header("📺 Бичлэгээр оруулсан цахим сургалт")
            if st.session_state.courses_list:
                course_dict = {c["Сэдэв"]: c["Линк"] for c in st.session_state.courses_list}
                topic = st.selectbox("Сургалт сонгох:", list(course_dict.keys()))
                st.video(course_dict[topic])
                
                if st.button("⏱️ Бичлэгийг үзэж дууссан гэж тэмдэглэх", key="finish_course_btn"):
                    gen_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    st.session_state.course_completions.append({
                        "Сурагч": st.session_state.current_user,
                        "Сургалт": topic,
                        "Батлах_Код": gen_code,
                        "Огноо": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success(f"Баярлалаа! Баталгаажуулах код үүслээ: **{gen_code}** (Админ бүртгэж авлаа)")
            else: st.info("Одоогоор сургалт нэмэгдээгүй байна.")

        elif menu == "📅 Цаг захиалга":
            log_action("Цаг захиалга цэс рүү орсон")
            st.header("📅 Сэтгэл зүйчтэй уулзах цаг захиалга")
            st.date_input("Уулзах өдөр сонгох:", key="app_date")
            st.selectbox("Боломжит цаг:", ["09:00 - 10:00", "14:00 - 15:00", "16:00 - 17:00"], key="app_time")
            if st.button("Баталгаажуулах", key="book_app_btn"):
                st.success("Уулзалтын цаг амжилттай товлогдлоо. Сэтгэл зүйч тантай холбогдох болно.")

        elif menu == "🕵️ Нэргүй санал хүсэх":
            log_action("Нэргүй санал хүсэлт илгээсэн")
            st.header("🕵️ Нэрээ нууцлан админд мэдээлэл хүргэх")
            anon_msg = st.text_area("Таны мэдээлэл болон нэр бүрэн нууцлагдана...", key="anon_input")
            if st.button("Илгээх", key="send_anon_btn"):
                if anon_msg:
                    st.session_state.anonymous_feedbacks.append({
                        "Мэдээлэл": anon_msg,
                        "Огноо": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    })
                    st.success("Таны мэдээлэл нэрээ нууталсан байдлаар админд амжилттай хүрэх болно.")

        elif menu == "🆘 ТУСЛААРАЙ":
            log_action("🚨 ТУСЛААРАЙ товч дээр дарсан")
            st.error("🚨 ЯАРАЛТАЙ ТУСЛАМЖИЙН ХЭСЭГ")
            st.write("Та сэтгэл зүйн хувьд хүнд нөхцөлд байгаа бол энэ товчийг дарж шууд дохио илгээнэ үү.")
            if st.button("🆘 ОДОО ТУСЛАМЖ ХҮСЭХ", type="primary", key="sos_btn"):
                st.session_state.emergency_alerts.append({
                    "Сурагч": st.session_state.current_user,
                    "Хугацаа": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.error("🆘 Дохио илгээгдлээ! Сургуулийн сэтгэл зүйч танд нэн даруй тусламж үзүүлэх болно.")
