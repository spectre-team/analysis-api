import os
from celery import Celery

env=os.environ
CELERY_BROKER_URL=env.get('CELERY_BROKER_URL','amqp://guest:guest@rabbitmq'),
CELERY_RESULT_BACKEND=env.get('CELERY_RESULT_BACKEND','db+postgresql://guest:guest@postgresql/celery')

app = Celery('spectre-analyzes',
             broker=CELERY_BROKER_URL,
             backend=CELERY_RESULT_BACKEND)

if __name__ == '__main__':
    print(app.conf.humanize(with_defaults=False, censored=True))
    app.start()
