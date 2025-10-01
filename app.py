# app.py
import os
import streamlit as st
import requests
import json
from dotenv import load_dotenv

# Завантажуємо змінні середовища (.env для локального запуску)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
print(os.getenv("SUPABASE_URL"))
print(os.getenv("SUPABASE_KEY"))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL або SUPABASE_KEY не задані. Перевірте .env або Environment Variables.")

# Заголовки для REST API
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

st.title("Бронювання аудиторій")

# Форма для бронювання
with st.form("reservation_form"):
    auditoriya = st.text_input("Номер аудиторії")
    date = st.date_input("Дата")
    submitted = st.form_submit_button("Забронювати")

    if submitted:
        payload = {"auditoriya": auditoriya, "date": str(date)}
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/reservations",
            headers=headers,
            data=json.dumps(payload)
        )
        if response.status_code in (200, 201):
            st.success("Аудиторія успішно заброньована!")
        else:
            st.error(f"Сталася помилка: {response.text}")

# Вивід всіх бронювань
st.subheader("Всі бронювання")
response = requests.get(
    f"{SUPABASE_URL}/rest/v1/reservations",
    headers=headers
)
if response.status_code == 200:
    reservations = response.json()
    if reservations:
        for r in reservations:
            st.write(f"Аудиторія: {r['auditoriya']}, Дата: {r['date']}")
    else:
        st.write("Немає бронювань")
else:
    st.error(f"Не вдалося завантажити бронювання: {response.text}")
