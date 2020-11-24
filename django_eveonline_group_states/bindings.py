from django.apps import apps 
from django.urls import reverse
from django.conf import settings
from packagebinder.bind import PackageBinding, SettingsBinding, TaskBinding, SidebarBinding
import logging 

logger = logging.getLogger(__name__)

app_config = apps.get_app_config('django_eveonline_group_states')

package_binding = PackageBinding(
    package_name=app_config.name, 
    version=app_config.version, 
    url_slug='eveonline', 
)

task_binding = TaskBinding(
    package_name=app_config.name, 
    required_tasks = [
        {
            "name": "EVE States: Verify User States",
            "task_name": "django_eveonline_group_states.tasks.update_all_user_states",
            "interval": 5,
            "interval_period": "minutes",
        },
        {
            "name": "EVE States: Verify User Groups",
            "task_name": "django_eveonline_group_states.tasks.verify_all_user_state_groups",
            "interval": 30,
            "interval_period": "minutes",
        }
    ],
    optional_tasks = [
    ]
)


def create_bindings():
    try:
        package_binding.save()
        task_binding.save()
    except Exception as e:
        if settings.DEBUG:
            raise(e)
        else:
            logger.error(f"Failed package binding step for {app_config.name}: {e}")