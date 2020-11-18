from django.apps import AppConfig, apps
import sys 

class DjangoGroupStatesConfig(AppConfig):
    name = 'django_eveonline_group_states'
    package_name = __import__(name).__package_name__
    version = __import__(name).__version__
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

        if apps.is_installed('packagebinder'):
            from packagebinder.exceptions import BindException
            try:
                bind = apps.get_app_config('packagebinder').get_bind_object(
                    self.package_name, self.version)
                # Required Task Bindings
                bind.add_required_task(
                    name="EVE States: Verify User States",
                    task="django_eveonline_group_states.tasks.update_all_user_states",
                    interval=5,
                    interval_period="minutes",
                )
                bind.add_required_task(
                    name="EVE States: Verify User Groups",
                    task="django_eveonline_group_states.tasks.verify_all_user_state_groups",
                    interval=30,
                    interval_period="minutes",
                )
                bind.save()
            except BindException as e:
                return
            except Exception as e:
                print(e)
                return
            


        
