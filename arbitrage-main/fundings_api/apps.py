from django.apps import AppConfig
import threading
import asyncio
import sys
import os

class FundingsApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fundings_api'
    def ready(self):
        if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') == "true":
            from utils.get_fundings import main as get_fundings
            def runner():
                asyncio.run(get_fundings())
            threading.Thread(target=runner, daemon=True).start()
