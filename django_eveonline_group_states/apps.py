from django.apps import AppConfig
import sys 

class DjangoGroupStatesConfig(AppConfig):
    name = 'django_eveonline_group_states'
    verbose_name = "States"

    def ready(self):
        from django.contrib.auth.models import User, Group
        from django.db.models.signals import m2m_changed, pre_delete, post_save
        from .models import EveUserState, EveGroupState
        from django_eveonline_connector.models import EveToken
        from .signals import global_user_add, user_group_change_verify_state, user_state_update, user_token_update
        post_save.connect(global_user_add, sender=User)
        post_save.connect(user_state_update, sender=EveUserState)
        post_save.connect(user_token_update, sender=EveToken)
        m2m_changed.connect(user_group_change_verify_state, sender=User.groups.through)
        
        try:
            # check for default state, create if doesn't exist
            if not EveGroupState.objects.filter(priority=-1).exists():
                EveGroupState.objects.create(name="Guest", priority=-1)

            # add users to default state
            if User.objects.filter(state__isnull=True).count() > 0:
                
                default_state = EveGroupState.objects.get(priority=-1)
                users_to_update = User.objects.filter(state__isnull=True) 
                for user in users_to_update:
                    EveUserState(
                        user=user,
                        state=default_state
                    ).save()
        except Exception as e:
            print(e)


        