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
# Увімкнути авто-перезавантаження шаблонів і вимкнути кеш статичних файлів
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


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


def get_site_url() -> str:
    # Вказуйте SITE_URL у змінних оточення (наприклад, Render URL або локально http://localhost:5000)
    # Якщо не задано, спробуємо зібрати з поточного запиту
    site = os.getenv("SITE_URL", "").rstrip("/")
    if site:
        return site
    # fallback на поточний host
    if request:
        return request.host_url.rstrip("/")
    return ""


@app.route("/", methods=["GET"])  # Головна сторінка зі списком і формою
def index():
    supabase_url = get_supabase_url()
    headers = get_supabase_headers()

    if not supabase_url or not headers.get("apikey"):
        return render_template(
            "index.html",
            reservations=[],
            error_message="SUPABASE_URL або SUPABASE_KEY не налаштовано у змінних оточення.",
            logged_in=is_logged_in(),
            user=current_user(),
        )

    # Якщо користувач не увійшов — не звертаємось до Supabase і показуємо заглушку
    if not is_logged_in():
        return render_template(
            "index.html",
            reservations=[],
            error_message=None,
            logged_in=False,
            user={},
        )

    try:
        response = requests.get(f"{get_rest_url()}/reservations", headers=headers, timeout=20)
        if response.status_code == 200:
            reservations = response.json()
            return render_template(
                "index.html",
                reservations=reservations,
                error_message=None,
                logged_in=True,
                user=current_user(),
            )
        else:
            return render_template(
                "index.html",
                reservations=[],
                error_message=f"Не вдалося завантажити бронювання: {response.text}",
                logged_in=True,
                user=current_user(),
            )
    except requests.RequestException as exc:
        return render_template(
            "index.html",
            reservations=[],
            error_message=f"Помилка з'єднання з Supabase: {exc}",
            logged_in=True,
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
            user_obj = data.get("user", {}) or {}
            meta = (user_obj.get("user_metadata") or {})
            session["user"] = {
                "id": user_obj.get("id"),
                "email": user_obj.get("email"),
                "first_name": meta.get("first_name"),
                "last_name": meta.get("last_name"),
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
    confirm_password = request.form.get("confirm_password", "").strip()
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    if not email or not password:
        flash("Вкажіть email і пароль.", "error")
        return redirect(url_for("register"))
    if password != confirm_password:
        flash("Паролі не співпадають.", "error")
        return redirect(url_for("register"))

    try:
        url = f"{get_auth_url()}/signup"
        headers = {
            "apikey": os.getenv("SUPABASE_KEY", ""),
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
            "password": password,
            "data": {
                "first_name": first_name,
                "last_name": last_name
            },
            "gotrue_meta_security": {"captcha_token": None}
        }
        # Додаємо email_redirect_to, щоб Supabase відкрив нашу сторінку підтвердження
        params = f"?email_redirect_to={get_site_url()}/confirm"
        resp = requests.post(url + params, headers=headers, data=json.dumps(payload), timeout=20)
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


@app.route("/confirm", methods=["GET"])  # Сторінка підтвердження email після кліку в листі
def confirm():
    # Supabase відкриє цю сторінку після успішного підтвердження email
    # Можна запропонувати одразу увійти
    return render_template("confirm.html")


@app.route("/schedule", methods=["GET"])  # Заглушка "Електронний розклад"
def schedule():
    return render_template("schedule.html", logged_in=is_logged_in(), user=current_user())


@app.route("/profile", methods=["GET", "POST"])  # Профіль користувача
def profile():
    if not require_login():
        return redirect(url_for("index"))

    if request.method == "GET":
        return render_template("profile.html", logged_in=True, user=current_user())

    # POST: оновлення ім'я/прізвище у user_metadata
    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    access_token = session.get("access_token")
    if not access_token:
        flash("Виконайте вхід повторно.", "error")
        return redirect(url_for("login"))

    try:
        url = f"{get_auth_url()}/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "apikey": os.getenv("SUPABASE_KEY", ""),
            "Content-Type": "application/json",
        }
        payload = {"data": {"first_name": first_name, "last_name": last_name}}
        resp = requests.patch(url, headers=headers, data=json.dumps(payload), timeout=20)
        if resp.status_code in (200, 201):
            # Оновлюємо локальну сесію теж
            user = current_user()
            user.update({"first_name": first_name, "last_name": last_name})
            session["user"] = user
            flash("Профіль оновлено.", "success")
        else:
            flash(f"Не вдалося оновити профіль: {resp.text}", "error")
    except requests.RequestException as exc:
        flash(f"Помилка з'єднання: {exc}", "error")

    return redirect(url_for("profile"))


@app.route("/settings", methods=["GET", "POST"])  # Налаштування акаунта (локально зберігаємо в сесії)
def settings():
    if not require_login():
        return redirect(url_for("index"))

    if request.method == "POST":
        theme = request.form.get("theme", "light")
        email_notifications = True if request.form.get("email_notifications") == "on" else False
        session.setdefault("preferences", {})
        session["preferences"].update({
            "theme": theme,
            "email_notifications": email_notifications,
        })
        flash("Налаштування збережено.", "success")
        return redirect(url_for("settings"))

    prefs = session.get("preferences", {"theme": "light", "email_notifications": False})
    return render_template("settings.html", logged_in=True, user=current_user(), prefs=prefs)


@app.route("/profile/password", methods=["POST"])  # Зміна паролю
def change_password():
    if not require_login():
        return redirect(url_for("index"))

    new_password = request.form.get("new_password", "").strip()
    confirm_new_password = request.form.get("confirm_new_password", "").strip()
    if not new_password or not confirm_new_password:
        flash("Вкажіть новий пароль і підтвердження.", "error")
        return redirect(url_for("profile"))
    if new_password != confirm_new_password:
        flash("Нові паролі не співпадають.", "error")
        return redirect(url_for("profile"))
    if len(new_password) < 6:
        flash("Пароль має містити щонайменше 6 символів.", "error")
        return redirect(url_for("profile"))

    access_token = session.get("access_token")
    if not access_token:
        flash("Сесія завершена. Увійдіть знову.", "error")
        return redirect(url_for("login"))

    try:
        url = f"{get_auth_url()}/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "apikey": os.getenv("SUPABASE_KEY", ""),
            "Content-Type": "application/json",
        }
        payload = {"password": new_password}
        resp = requests.patch(url, headers=headers, data=json.dumps(payload), timeout=20)
        if resp.status_code in (200, 201):
            flash("Пароль оновлено.", "success")
        else:
            flash(f"Не вдалося змінити пароль: {resp.text}", "error")
    except requests.RequestException as exc:
        flash(f"Помилка з'єднання: {exc}", "error")
    return redirect(url_for("profile"))


@app.route("/profile/delete", methods=["POST"])  # Видалення акаунта
def delete_account():
    if not require_login():
        return redirect(url_for("index"))

    confirm_text = request.form.get("confirm_text", "").strip()
    if confirm_text != "DELETE":
        flash("Щоб підтвердити, введіть DELETE у полі підтвердження.", "error")
        return redirect(url_for("profile"))

    user = current_user()
    user_id = user.get("id")
    service_key = os.getenv("SUPABASE_KEY", "")
    if not user_id or not service_key:
        flash("Видалення недоступне. Немає доступу.", "error")
        return redirect(url_for("profile"))

    # Використовуємо адмін-ендпоінт (потребує service_role ключ)
    try:
        url = f"{get_auth_url()}/admin/users/{user_id}"
        headers = {
            "Authorization": f"Bearer {service_key}",
            "apikey": service_key,
        }
        resp = requests.delete(url, headers=headers, timeout=20)
        if resp.status_code in (200, 204):
            session.clear()
            flash("Акаунт видалено.", "success")
            return redirect(url_for("index"))
        else:
            flash(f"Не вдалося видалити акаунт: {resp.text}", "error")
            return redirect(url_for("profile"))
    except requests.RequestException as exc:
        flash(f"Помилка з'єднання: {exc}", "error")
        return redirect(url_for("profile"))


if __name__ == "__main__":
    # Локальний запуск
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
