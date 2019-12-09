from django.contrib.auth.models import User, Group
from django_eveonline_group_states.models import EveUserState, EveGroupState
from django.dispatch import receiver
from django.db.models.signals import m2m_changed, pre_delete, post_save
from django.db import transaction
from django_eveonline_group_states.tasks import verify_user_state_and_groups
from django.core.exceptions import PermissionDenied

import logging
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def global_user_add(sender, **kwargs):
    def call():
        user = kwargs.get('instance')
        if kwargs.get('created'):
            # TODO: cache for speedup
            logger.debug("global_user_add: setting user's default state")
            try:
                EveUserState.objects.create(user=user, state=EveGroupState.objects.get(priority=-1))
            except Exception as e:
                logger.warning("Attempted to set default state, but failed. Create an EveGroupState with priority -1.")
    transaction.on_commit(call)

@receiver(m2m_changed, sender=User.groups.through)
def user_group_change_verify_state(sender, **kwargs):
    django_user = kwargs.get('instance')
    if "post" in kwargs.get('action'):
        verify_user_state_and_groups.apply_async(args=[django_user.pk])