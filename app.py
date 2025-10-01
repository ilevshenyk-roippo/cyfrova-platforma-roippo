import os
import json
from datetime import date as date_type

from flask import Flask, render_template, request, redirect, url_for, flash
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # Завантажує .env для локального запуску
except ImportError:
    pass  # Якщо dotenv не встановлено, просто пропускаємо


app = Flask(__name__)
# Секрет для flash‑повідомлень (безпечно зберігати як змінну оточення)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")


def get_supabase_headers() -> dict:
    supabase_key = os.getenv("SUPABASE_KEY")
    return {
        "apikey": supabase_key or "",
        "Authorization": f"Bearer {supabase_key}" if supabase_key else "",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def get_supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


@app.route("/", methods=["GET"])  # Головна сторінка зі списком і формою
def index():
    supabase_url = get_supabase_url()
    headers = get_supabase_headers()

    if not supabase_url or not headers.get("apikey"):
        return render_template(
            "index.html",
            reservations=[],
            error_message="SUPABASE_URL або SUPABASE_KEY не налаштовано у змінних оточення.",
        )

    try:
        response = requests.get(f"{supabase_url}/rest/v1/reservations", headers=headers, timeout=20)
        if response.status_code == 200:
            reservations = response.json()
            return render_template("index.html", reservations=reservations, error_message=None)
        else:
            return render_template(
                "index.html",
                reservations=[],
                error_message=f"Не вдалося завантажити бронювання: {response.text}",
            )
    except requests.RequestException as exc:
        return render_template(
            "index.html",
            reservations=[],
            error_message=f"Помилка з'єднання з Supabase: {exc}",
        )


@app.route("/reserve", methods=["POST"])  # Обробка відправки форми
def reserve():
    supabase_url = get_supabase_url()
    headers = get_supabase_headers()

    auditoriya = request.form.get("auditoriya", "").strip()
    date_str = request.form.get("date", "").strip()

    if not supabase_url or not headers.get("apikey"):
        flash("SUPABASE_URL або SUPABASE_KEY не налаштовано.", "error")
        return redirect(url_for("index"))

    if not auditoriya or not date_str:
        flash("Будь ласка, заповніть номер аудиторії і дату.", "error")
        return redirect(url_for("index"))

    try:
        # Валідація дати (YYYY-MM-DD)
        year, month, day = map(int, date_str.split("-"))
        _ = date_type(year, month, day)
    except Exception:
        flash("Невірний формат дати. Використовуйте YYYY-MM-DD.", "error")
        return redirect(url_for("index"))

    payload = {"auditoriya": auditoriya, "date": date_str}

    try:
        response = requests.post(
            f"{supabase_url}/rest/v1/reservations",
            headers=headers,
            data=json.dumps(payload),
            timeout=20,
        )
        if response.status_code in (200, 201):
            flash("Аудиторію заброньовано!", "success")
        else:
            flash(f"Сталася помилка: {response.text}", "error")
    except requests.RequestException as exc:
        flash(f"Помилка з'єднання з Supabase: {exc}", "error")

    return redirect(url_for("index"))


if __name__ == "__main__":
    # Локальний запуск
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
