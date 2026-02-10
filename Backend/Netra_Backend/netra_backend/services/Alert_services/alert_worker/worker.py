import json
import os
import time
import pika
import sys
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# RabbitMQ Config
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "NETRA")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "netra@123")

ALERT_DETECTED_QUEUE = os.getenv("ALERT_DETECTED_QUEUE", "alert.detected")
ALERT_NOTIFY_QUEUE = os.getenv("ALERT_NOTIFY_QUEUE", "alert.notify")

# Database Config
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "centraDB")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "root")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# SQLAlchemy Setup
Base = declarative_base()

class Alert(Base):
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String) # Storing original timestamp string
    engine_time = Column(DateTime, default=datetime.utcnow)
    submodule_name = Column(String)
    submodule_id = Column(String)
    metric = Column(String)
    value = Column(Float)
    min_limit = Column(Float)
    max_limit = Column(Float)
    severity = Column(String)
    reason = Column(Text)
    packet_raw = Column(String)
    packet_matched = Column(String)
    status = Column(String)

# Initialize DB connection
def init_db():
    print(f"[ALERT_WORKER] Connecting to database at {DB_HOST}...")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

def connect_rabbitmq():
    creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=creds)
    return pika.BlockingConnection(params)

def main():
    print("[ALERT_WORKER] Starting...")
    
    Session = init_db()

    while True:
        try:
            connection = connect_rabbitmq()
            channel = connection.channel()

            channel.queue_declare(queue=ALERT_DETECTED_QUEUE, durable=True)
            channel.queue_declare(queue=ALERT_NOTIFY_QUEUE, durable=True)

            print(f"[ALERT_WORKER] Waiting for alerts on '{ALERT_DETECTED_QUEUE}'...")

            def callback(ch, method, properties, body):
                try:
                    alert = json.loads(body.decode("utf-8"))
                except Exception as e:
                    print("[ALERT_WORKER] Invalid alert JSON ❌", e)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                # Save to Database using SQLAlchemy
                try:
                    session = Session()
                    db_alert = Alert(
                        timestamp=alert.get('timestamp'),
                        submodule_name=alert.get('submodule_name'),
                        submodule_id=alert.get('submodule_id'),
                        metric=alert.get('metric'),
                        value=alert.get('value'),
                        min_limit=alert.get('min'),
                        max_limit=alert.get('max'),
                        severity=alert.get('severity'),
                        reason=alert.get('reason'),
                        packet_raw=alert.get('raw_packet_name'),
                        packet_matched=alert.get('matched_packet_name'),
                        status=alert.get('status', 'alert_identified')
                    )
                    session.add(db_alert)
                    session.commit()
                    # Capture the auto-generated ID to pass it to the notifier
                    alert["db_id"] = db_alert.id
                    session.close()
                    print(f"[ALERT_WORKER] Saved alert to DB ✅ id={alert['db_id']} metric={alert.get('metric')}")
                except Exception as db_err:
                    print(f"[ALERT_WORKER] Database error ❌ {db_err}")
                    # We continue to notification even if DB fails

                # Add engine metadata
                alert["engine_time"] = time.strftime("%Y-%m-%d %H:%M:%S")

                channel.basic_publish(
                    exchange="",
                    routing_key=ALERT_NOTIFY_QUEUE,
                    body=json.dumps(alert).encode("utf-8"),
                    properties=pika.BasicProperties(delivery_mode=2)
                )

                print(f"[ALERT_WORKER] Forwarded alert -> '{ALERT_NOTIFY_QUEUE}' ✅ severity={alert.get('severity')}")

                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=ALERT_DETECTED_QUEUE, on_message_callback=callback)

            channel.start_consuming()

        except Exception as e:
            print("[ALERT_WORKER] RabbitMQ connection failed, retrying in 3s...", e)
            time.sleep(3)

if __name__ == "__main__":
    main()
