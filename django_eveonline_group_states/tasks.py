from celery import task, shared_task
from django.contrib.auth.models import User
from .models import EveGroupState, EveUserState

import logging
logger = logging.getLogger(__name__)

"""
Global Tasks
These are cronjob-like tasks
"""

@shared_task
def update_all_user_states():
    for user in User.objects.all():
        update_user_state.apply_async(args=[user.pk])

@shared_task
def verify_all_user_state_groups():
    for user in User.objects.all():
        verify_user_state_groups.apply_async(args=[user.pk])

"""
User Tasks
"""
@shared_task
def update_user_state(user_id):
    # gather information about user
    user = User.objects.get(pk=user_id)
    states = EveGroupState.objects.all().order_by('priority')

    try:
        default_state = EveGroupState.objects.get(priority=-1)
    except Exception as e:
        logger.warning("Attempted to set default state, but failed. Create an EveGroupState with priority -1.")
        default_state = None
    
    try:
        user_state = user.state
    except Exception as e:
        user_state = None

    logger.debug("Current user state: %s" % user_state)
    logger.debug("Current default state: %s" % default_state)


    if user_state:
        pre_state = user_state.state

    if user_state and user_state.valid():
        logger.debug("Searching for higher state for %s" % user)
        user_state.state = user_state.get_higher_qualifying_state()
        logger.debug("Highest state: %s" % user_state.state)
    elif user_state and not user_state.valid():
        logger.debug("Searching for lower state for %s" % user)
        user_state.state = user_state.get_lower_qualifying_state()
        logger.debug("Lowest state: %s" % user_state.state)
        logger.debug(user.state)
    elif not user_state:
        if default_state:
            EveUserState.objects.create(user=user, state=default_state)
    else:
        if default_state:
            EveUserState.objects.create(user=user, state=default_state)
        elif user_state:
            user_state.delete()

    if pre_state != user_state.state:
        logger.debug("State change: %s to %s" % (pre_state, user_state.state))
        user_state.save() 

@shared_task
def verify_user_state_groups(user_id):
    user = User.objects.get(pk=user_id)

    try:
        user_state = user.state
    except EveGroupState.DoesNotExist:
        logger.debug("update_user_state_groups: Skipping %s due to state=None" % user)
        return 

    for group in user_state.state.default_groups.all():
        if group not in user.groups.all():
            logger.debug("Adding default group %s to user %s" % (group, user))
            user.groups.add(group)
    
    for group in user.groups.all():
        valid_group = group in user_state.state.qualifying_groups.all() or group in user_state.state.default_groups.all() or group in user_state.state.enabling_groups.all()
        if not valid_group:
            user.groups.remove(group)

    
@shared_task
def verify_user_state_and_groups(user_id):
    update_user_state(user_id)
    verify_user_state_groups.apply_async(args=[user_id])