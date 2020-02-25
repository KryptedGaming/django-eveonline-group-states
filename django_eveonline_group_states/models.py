from django.db import models
from django.contrib.auth.models import User, Group
from django_eveonline_connector.models import EveCorporation, EveAlliance, EveToken

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

    def get_all_enabling_groups(self):
        default_group_pks = list(self.state.default_groups.values_list('pk', flat=True))
        enabled_group_pks = list(self.state.enabling_groups.values_list('pk', flat=True))
        group_pks = default_group_pks + enabled_group_pks
        return Group.objects.filter(pk__in=group_pks)

    def valid(self):
        if self.state.priority == -1:
            return True 

        if self.state.qualifying_groups.all():
            if (self.user.groups.all() & self.state.qualifying_groups.all()).count() == 0:
                return False # user has no groups in qualifying groups

        if self.state.qualifying_corporations.all():     
            if not EveToken.objects.filter(user=self.user, evecharacter__corporation__in=self.state.qualifying_corporations.all()).exists():
                return False # no tokens exist that are in the qualifying corporations

        if self.state.qualifying_alliances.all():
            if not EveToken.objects.filter(user=self.user, evecharacter__corporation__alliance__in=self.state.qualifying_alliances.all()).exists():
                return False # no tokens exist that are in the qualifying alliances

        return True # assumes we're in an open state
    
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
