from flask import Flask
from core.database import db
from core.kernel import load_modules

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///osbiz.db'

db.init_app(app)

# إنشاء الجداول
with app.app_context():
    db.create_all()
    load_modules(app, db)  # تحميل الوحدات

if __name__ == '__main__':
    app.run(debug=True)
