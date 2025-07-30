from flask_sqlalchemy import SQLAlchemy

def register_models(db):
    class Table(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(50), nullable=False)
        status = db.Column(db.String(20))  # free, occupied

    class Order(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        table_id = db.Column(db.Integer, db.ForeignKey('table.id'))
        items = db.Column(db.Text)
        total = db.Column(db.Float) 
