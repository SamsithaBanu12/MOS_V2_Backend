import json
import os
import time
import pika
import sys
sys.stdout.reconfigure(line_buffering=True)

from alert_logic import load_alert_config, build_config_index, evaluate_tm


# -------------------------
# RabbitMQ Config
# -------------------------
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "Netra")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "netra@123")

DECODED_EXCHANGE = "telemetry.decoded"
ALERT_QUEUE = "q.decoded.alerts"
ALERT_DETECTED_QUEUE = "alert.detected"

CONFIG_PATH = "/app/config/TM_alert_config.json"


def connect():
    creds = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)

    return pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=creds,
            heartbeat=0
        )
    )


def main():
    print("[ALERT_BUILDER] Starting (exchange-based)...")

    config = load_alert_config(CONFIG_PATH)
    thresholds = config["thresholds"]
    submodule_index = config.get("submodules", {})
    config_index = build_config_index(config)

    print(f"[ALERT_BUILDER] Config loaded ✅ rules={len(config_index)} queue_ids, submodules={len(submodule_index)}")

    while True:
        try:
            conn = connect()
            ch = conn.channel()

            # Declare exchange
            ch.exchange_declare(
                exchange=DECODED_EXCHANGE,
                exchange_type="topic",
                durable=True
            )

            # Alert input queue
            ch.queue_declare(queue=ALERT_QUEUE, durable=True)

            ch.queue_bind(
                exchange=DECODED_EXCHANGE,
                queue=ALERT_QUEUE,
                routing_key="#"
            )

            # Alert output queue
            ch.queue_declare(queue=ALERT_DETECTED_QUEUE, durable=True)

            print(
                f"[ALERT_BUILDER] Connected to RabbitMQ ({RABBITMQ_HOST}:{RABBITMQ_PORT}) "
                f"Listening on '{DECODED_EXCHANGE}'..."
            )

            def callback(ch, method, properties, body):
                try:
                    tm = json.loads(body.decode("utf-8"))
                except Exception as e:
                    print("[ALERT_BUILDER] Invalid TM JSON ❌", e)
                    ch.basic_ack(method.delivery_tag)
                    return

                alerts = evaluate_tm(tm, config_index, thresholds, submodule_index)

                for alert in alerts:
                    ch.basic_publish(
                        exchange="",
                        routing_key=ALERT_DETECTED_QUEUE,
                        body=json.dumps(alert).encode("utf-8"),
                        properties=pika.BasicProperties(delivery_mode=2)
                    )

                if alerts:
                    print(f"[ALERT_BUILDER] Published {len(alerts)} alert(s) ✅")

                ch.basic_ack(method.delivery_tag)

            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue=ALERT_QUEUE, on_message_callback=callback)
            ch.start_consuming()

        except Exception as e:
            print("[ALERT_BUILDER] RabbitMQ error, retrying in 3s...", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
