from django.contrib import admin
from .models import EveGroupState

@admin.register(EveGroupState)
class EveGroupStateAdmin(admin.ModelAdmin):
    list_display = ('name', 'priority')
