# app.py
import os
import streamlit as st
from supabase import create_client, Client

# Підключення до Supabase через Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Бронювання аудиторій")

# Форма для бронювання
with st.form("reservation_form"):
    auditoriya = st.text_input("Номер аудиторії")
    date = st.date_input("Дата")
    submitted = st.form_submit_button("Забронювати")

    if submitted:
        try:
            response = supabase.table("reservations").insert({
                "auditoriya": auditoriya,
                "date": str(date)
            }).execute()

            if response.status_code in (200, 201):
                st.success("Аудиторія успішно заброньована!")
            else:
                st.error(f"Сталася помилка: {response.data}")

        except Exception as e:
            st.error(f"Помилка під час підключення до Supabase: {e}")

# Вивід всіх бронювань
st.subheader("Всі бронювання")
try:
    reservations = supabase.table("reservations").select("*").execute()
    if reservations.data:
        for r in reservations.data:
            st.write(f"Аудиторія: {r['auditoriya']}, Дата: {r['date']}")
    else:
        st.write("Немає бронювань")
except Exception as e:
    st.error(f"Не вдалося завантажити бронювання: {e}")
