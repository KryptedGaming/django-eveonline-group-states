from django.db import models
from django.contrib.auth.models import User, Group
from django_eveonline_connector.models import EveCorporation, EveAlliance

import logging
logger = logging.getLogger(__name__)

class EveGroupState(models.Model):
    name = models.CharField(max_length=32)
    qualifying_groups = models.ManyToManyField(Group, blank=True, related_name="qualifying_groups")
    qualifying_corporations = models.ManyToManyField(EveCorporation, blank=True) 
    qualifying_alliances = models.ManyToManyField(EveAlliance, blank=True)
    default_groups = models.ManyToManyField(Group, blank=True, related_name="default_groups")
    enabling_groups = models.ManyToManyField(Group, blank=True, related_name="enabling_groups") 
    priority = models.IntegerField(unique=True, default=0)

    def __str__(self):
        return self.name


class EveUserState(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="state")
    state = models.ForeignKey("EveGroupState", on_delete=models.CASCADE, related_name="user_set")

    def __str__(self):
        return "<%s:%s>" % (self.user.username, self.state.name)

    def valid(self):
        if self.state.priority == -1:
            return True 

        for group in self.user.groups.all():
            if group in self.state.qualifying_groups.all():
                return True 
        
        if not self.user.eve_tokens:
            return False 

        for token in self.user.eve_tokens.all():
            character = token.evecharacter
            corporation = character.corporation
            if corporation:
                alliance = character.corporation.alliance
            else:
                alliance = None
        
            if corporation in self.state.qualifying_corporations.all():
                return True 
            
            if alliance and alliance in self.state.qualifying_alliances.all():
                return True 

        return False 
    
    def get_higher_qualifying_state(self):
        states = EveGroupState.objects.filter(priority__gte=self.state.priority).order_by('-priority')
        last_valid_state = self.state
        for state in states:
            self.state = state 
            if self.valid():
                return state
            else:
                continue 
            
    def get_lower_qualifying_state(self):
        states = EveGroupState.objects.filter(priority__lte=self.state.priority).order_by('-priority')
        for state in states:
            self.state = state
            if self.valid():
                return state 
        return None 