from celery import Celery, Task

"""
    This file contains the Celery configuration
    It is used to configure Celery for background tasks
"""

def celery_init_app(app):

    class FlaskTask(Task):

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(
        app.name,
        task_cls=FlaskTask
    )


    celery.config_from_object({
        "broker_url": app.config["CELERY_BROKER_URL"],
        "result_backend": app.config["CELERY_RESULT_BACKEND"],
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serilizer": "json",
        "timezone": "UTC",
        "enable_utc": True,
        "task_ignore_result": True
    })

    celery.set_default()

    app.extensions["celery"] = celery

    return celery