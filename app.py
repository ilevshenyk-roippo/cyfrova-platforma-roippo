# app.py
import streamlit as st
from supabase import create_client, Client

# Вставляємо ваші дані
SUPABASE_URL = "https://ecnzxejyssbakotctyqn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVjbnp4ZWp5c3NiYWtvdGN0eXFuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTkzMTU5MTIsImV4cCI6MjA3NDg5MTkxMn0.dhsy_aaLzVWDsRiWXH7zEFi8JSSCcQcowsIiVoiRLKY"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
