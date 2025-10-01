import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


st.title("Бронювання аудиторій")

# Форма для бронювання
with st.form("reservation_form"):
    auditoriya = st.text_input("Номер аудиторії")
    date = st.date_input("Дата")
    submitted = st.form_submit_button("Забронювати")

    if submitted:
        # Вставка в таблицю Supabase
        response = supabase.table("reservations").insert({
            "auditoriya": auditoriya,
            "date": str(date)
        }).execute()

        if response.status_code == 201:
            st.success("Аудиторія успішно заброньована!")
        else:
            st.error(f"Сталася помилка: {response.data}")

# Вивід всіх бронювань
st.subheader("Всі бронювання")
reservations = supabase.table("reservations").select("*").execute()
if reservations.data:
    for r in reservations.data:
        st.write(f"Аудиторія: {r['auditoriya']}, Дата: {r['date']}")
else:
    st.write("Немає бронювань")
