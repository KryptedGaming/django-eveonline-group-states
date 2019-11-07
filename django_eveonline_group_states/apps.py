from django.apps import AppConfig


class DjangoGroupStatesConfig(AppConfig):
    name = 'django_eveonline_group_states'
    verbose_name = "States"

    def ready(self):
        from django.contrib.auth.models import User, Group
        from django.db.models.signals import m2m_changed, pre_delete, post_save
        from .models import EveUserState
        from .signals import global_user_add, user_group_change_update_state, user_state_change_verify_groups
        post_save.connect(global_user_add, sender=User)
        m2m_changed.connect(user_group_change_update_state, sender=User.groups.through)
        m2m_changed.connect(user_state_change_verify_groups, sender=EveUserState)
        