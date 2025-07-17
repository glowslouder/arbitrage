from django.db import models
from mongoengine import Document, StringField, FloatField, DateTimeField, DictField
from datetime import datetime

class MainFundingModel(Document):
    time = DateTimeField(default=datetime.now)
    fundings = DictField(
        field=DictField(
            field=DictField()
        )
    )

# Create your models here.
