from flask import Flask, jsonify

app = Flask(__name__)

# Тестові дані (поки без бази)
schedule = [
    {"day": "Poniedilok", "time": "8:30 - 9:50", "subject": "Matematika", "auditory": "101"},
    {"day": "Poniedilok", "time": "10:00 - 11:20", "subject": "Fizyka", "auditory": "205"},
    {"day": "Vivtorok", "time": "8:30 - 9:50", "subject": "Informatyka", "auditory": "302"},
]

@app.route("/")
def home():
    return """
    <h1>Cyfrova platforma ROIPPO</h1>
    <p>Vitajemo na platformi dlya vykladachiv! API pratsyuye.</p>
    <p>Shchob perehliadty rozklad, vidkriyte <a href='/schedule'>/schedule</a></p>
    """

@app.route("/schedule")
def get_schedule():
    return jsonify(schedule)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
