import json
import os
import time
import pika
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

sys.stdout.reconfigure(line_buffering=True)

# RabbitMQ Config
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "NETRA")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "netra@123")

ALERT_NOTIFY_QUEUE = os.getenv("ALERT_NOTIFY_QUEUE", "alert.notify")

# Email Config
SMTP_HOST = os.getenv("SMTP_HOST", "mock")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "alerts@netra.local")
EMAIL_TO = os.getenv("EMAIL_TO", "mission_ops@netra.local")

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
    __tablename__ = 'alert'
    id = Column(Integer, primary_key=True)
    status = Column(String)

# Initialize DB connection
def init_db():
    print(f"[NOTIFIER] Connecting to database at {DB_HOST}...")
    engine = create_engine(DATABASE_URL)
    return sessionmaker(bind=engine)

def update_db_status(Session, db_id, new_status):
    try:
        session = Session()
        session.execute(
            update(Alert)
            .where(Alert.id == db_id)
            .values(status=new_status)
        )
        session.commit()
        session.close()
        print(f"[NOTIFIER] Updated DB status to '{new_status}' for ID {db_id} ✅")
    except Exception as e:
        print(f"[NOTIFIER] Failed to update DB status: {e}")

def connect():
    creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=creds)
    return pika.BlockingConnection(params)

def send_email(alert: dict):
    if SMTP_HOST == "mock":
        print(f"[NOTIFIER] (MOCK EMAIL) Would send to {EMAIL_TO}: {alert.get('severity')} Alert on {alert.get('metric')}")
        return

    try:
        subject = f"[NETRA ALERT] {alert.get('severity')} - {alert.get('metric')}"
        body = f"""
 NETRA ALERT DETECTED 

Details:
-----------------------------------------
Severity       : {alert.get('severity')}
Metric         : {alert.get('metric')}
Value          : {alert.get('value')}
Submodule      : {alert.get('submodule_name')} (ID: {alert.get('submodule_id')})
Min Limit      : {alert.get('min')}
Max Limit      : {alert.get('max')}
Reason         : {alert.get('reason')}
Timestamp      : {alert.get('timestamp')}
Packet (raw)   : {alert.get('raw_packet_name')}
Packet (match) : {alert.get('matched_packet_name')}
-----------------------------------------
Status         : {alert.get('status')}
"""
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        
        print(f"[NOTIFIER] Email sent successfully to {EMAIL_TO} ✅")

    except Exception as e:
        # Re-raise so the caller can decide to retry
        raise e

def pretty_print(alert: dict):
    print("\n NETRA ALERT")
    print(f"Time           : {alert.get('timestamp')}")
    print(f"Severity       : {alert.get('severity')}")
    print(f"Queue ID       : {alert.get('queue_id')}")
    print(f"Submodule      : {alert.get('submodule_name')} ({alert.get('submodule_id')})")
    print(f"Metric         : {alert.get('metric')}")
    print(f"Value          : {alert.get('value')}")
    print(f"Min            : {alert.get('min')}")
    print(f"Max            : {alert.get('max')}")
    print(f"Reason         : {alert.get('reason')}")
    print(f"Packet(raw)    : {alert.get('raw_packet_name')}")
    print(f"Packet(matched): {alert.get('matched_packet_name')}")
    print(f"Status         : {alert.get('status')}")
    print("=====================================================\n")

def main():
    print("[NOTIFIER] Starting...")
    
    Session = init_db()

    while True:
        try:
            connection = connect()
            channel = connection.channel()

            channel.queue_declare(queue=ALERT_NOTIFY_QUEUE, durable=True)

            print(f"[NOTIFIER] Waiting for notify alerts on '{ALERT_NOTIFY_QUEUE}'...")

            def callback(ch, method, properties, body):
                try:
                    alert = json.loads(body.decode("utf-8"))
                    print(f"[NOTIFIER] Received alert for {alert.get('metric')}...")
                except Exception as e:
                    print("[NOTIFIER] Invalid notify JSON ❌", e)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                pretty_print(alert)
                
                # Attempt to send email with a small retry if rate limited
                success = False
                for attempt in range(2):
                    try:
                        send_email(alert)
                        success = True
                        break
                    except Exception as e:
                        if "Too many emails" in str(e) or "550" in str(e):
                            print(f"[NOTIFIER] Rate limited, retrying in 2s... (Attempt {attempt+1})")
                            time.sleep(2)
                        else:
                            print(f"[NOTIFIER] Email failed: {e}")
                            break
                
                # If email succeeded, update the status in the DB
                if success and alert.get("db_id"):
                    update_db_status(Session, alert.get("db_id"), "alert_notified")
                            
                # Small gap to prevent overwhelming the server
                time.sleep(1.5)
                
                sys.stdout.flush()
                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=ALERT_NOTIFY_QUEUE, on_message_callback=callback)

            channel.start_consuming()

        except Exception as e:
            print("[NOTIFIER] RabbitMQ connection failed, retrying in 3s...", e)
            time.sleep(3)

if __name__ == "__main__":
    main()

