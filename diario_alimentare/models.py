#from django.conf import settings
from django.db import models
from django.utils import timezone

class Pasto(models.Model):
    ora = models.DateTimeField(default=timezone.now)
    title  = models.CharField ( default=" ", max_length=100)
    situazione = models.CharField(max_length=100)   
    cibo = models.TextField()
    sensazione = models.CharField(max_length=150)

    def __str__(self):
        return str(self.ora.strftime(format='%d/%m/%Y - %H:%M')) + " " + self.title

    def data(self):
        return str(self.ora.strftime(format='%d/%m/%Y'))   

    def orario(self):
        return  str(self.ora.strftime(format='%H:%M'))  
    # Create your models here.
