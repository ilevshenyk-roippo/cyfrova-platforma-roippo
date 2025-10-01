import os
import json
from datetime import date as date_type

from flask import Flask, render_template, request, redirect, url_for, flash, session
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


def get_auth_url() -> str:
    base = get_supabase_url()
    return f"{base}/auth/v1"


def get_rest_url() -> str:
    base = get_supabase_url()
    return f"{base}/rest/v1"


def is_logged_in() -> bool:
    return bool(session.get("access_token") and session.get("user"))


def current_user() -> dict:
    return session.get("user") or {}


def require_login():
    if not is_logged_in():
        flash("Потрібен вхід до системи.", "error")
        return False
    return True


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
        response = requests.get(f"{get_rest_url()}/reservations", headers=headers, timeout=20)
        if response.status_code == 200:
            reservations = response.json()
            return render_template(
                "index.html",
                reservations=reservations,
                error_message=None,
                logged_in=is_logged_in(),
                user=current_user(),
            )
        else:
            return render_template(
                "index.html",
                reservations=[],
                error_message=f"Не вдалося завантажити бронювання: {response.text}",
                logged_in=is_logged_in(),
                user=current_user(),
            )
    except requests.RequestException as exc:
        return render_template(
            "index.html",
            reservations=[],
            error_message=f"Помилка з'єднання з Supabase: {exc}",
            logged_in=is_logged_in(),
            user=current_user(),
        )


@app.route("/reserve", methods=["POST"])  # Обробка відправки форми
def reserve():
    supabase_url = get_supabase_url()
    headers = get_supabase_headers()

    auditoriya = request.form.get("auditoriya", "").strip()
    date_str = request.form.get("date", "").strip()

    if not require_login():
        return redirect(url_for("index"))

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

    # Прив'язуємо бронювання до користувача
    user = current_user()
    payload = {"auditoriya": auditoriya, "date": date_str, "user_id": user.get("id")}

    try:
        response = requests.post(
            f"{get_rest_url()}/reservations",
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


@app.route("/login", methods=["GET", "POST"])  # Логін через email+password
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    if not email or not password:
        flash("Вкажіть email і пароль.", "error")
        return redirect(url_for("login"))

    try:
        url = f"{get_auth_url()}/token?grant_type=password"
        headers = {
            "apikey": os.getenv("SUPABASE_KEY", ""),
            "Content-Type": "application/json",
        }
        payload = {"email": email, "password": password}
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            # Збереження токена та інформації про користувача
            session["access_token"] = data.get("access_token")
            session["refresh_token"] = data.get("refresh_token")
            session["user"] = {
                "id": data.get("user", {}).get("id"),
                "email": data.get("user", {}).get("email"),
            }
            flash("Вхід виконано.", "success")
            return redirect(url_for("index"))
        else:
            flash(f"Помилка входу: {resp.text}", "error")
            return redirect(url_for("login"))
    except requests.RequestException as exc:
        flash(f"Помилка з'єднання: {exc}", "error")
        return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])  # Реєстрація користувача
def register():
    if request.method == "GET":
        return render_template("register.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    if not email or not password:
        flash("Вкажіть email і пароль.", "error")
        return redirect(url_for("register"))

    try:
        url = f"{get_auth_url()}/signup"
        headers = {
            "apikey": os.getenv("SUPABASE_KEY", ""),
            "Content-Type": "application/json",
        }
        payload = {"email": email, "password": password}
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
        if resp.status_code in (200, 201):
            flash("Реєстрація успішна. Увійдіть за допомогою ваших даних.", "success")
            return redirect(url_for("login"))
        else:
            flash(f"Помилка реєстрації: {resp.text}", "error")
            return redirect(url_for("register"))
    except requests.RequestException as exc:
        flash(f"Помилка з'єднання: {exc}", "error")
        return redirect(url_for("register"))


@app.route("/logout", methods=["POST"])  # Вихід (очистка сесії)
def logout():
    session.clear()
    flash("Вихід виконано.", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Локальний запуск
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
