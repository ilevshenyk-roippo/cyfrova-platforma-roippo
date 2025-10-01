import streamlit as st

st.set_page_config(page_title="Цифрова платформа", page_icon="🖥️")

st.title("Цифрова платформа для викладачів")
st.write("Ласкаво просимо! Тут ви зможете займати аудиторії та планувати заняття.")

# Приклад форми бронювання аудиторії
st.header("Забронювати аудиторію")
auditorii = ["Аудиторія 101", "Аудиторія 102", "Аудиторія 103"]
auditoriya = st.selectbox("Виберіть аудиторію", auditorii)
date = st.date_input("Дата заняття")
st.write(f"Ви обрали: {auditoriya} на {date}")
