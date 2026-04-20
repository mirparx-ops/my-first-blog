from django import forms
from .models import Pasto

class PastoForm(forms.ModelForm):

    class Meta:
        model = Pasto
        fields = ('ora', 'title','luogo','cibo','conChi','come_sento_prima','come_sento_dopo', 'sensazione')
