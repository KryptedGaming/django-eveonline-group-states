from django.test import TestCase
from django.contrib.auth.models import User, Group
from django_eveonline_connector.models import EveToken, EveCharacter, EveCorporation, EveAlliance
from django_eveonline_group_states.models import EveGroupState, EveUserState
from django_eveonline_group_states.tasks import *

# Create your tests here.
class EveUserStateModelTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="ModelTest", password="TestPassword", email="test")
        Group.objects.create(name="ModelTest")
        EveToken.objects.create(user=User.objects.all()[0])
        EveCharacter.objects.create(name="ModelTest", external_id=0, token=EveToken.objects.all()[0])
        EveCorporation.objects.create(name="ModelTest", external_id=1)
        EveAlliance.objects.create(name="ModelTest", external_id=2)
        EveGroupState.objects.create(name="DefaultState", priority=-1)
        EveGroupState.objects.create(name="TestState", priority=1)
        EveGroupState.objects.create(name="TestStateHigher", priority=2)
        EveGroupState.objects.create(name="TestStateLower", priority=0)

    def test_valid(self):
        print("test_qualify: starting test")
        
        user = User.objects.get(username="ModelTest")
        group = Group.objects.get(name="ModelTest")
        character = EveCharacter.objects.all()[0]
        corporation = EveCorporation.objects.all()[0]
        alliance = EveAlliance.objects.all()[0]
        state = EveGroupState.objects.get(name="TestState")
        user_state = EveUserState.objects.create(user=user, state=state)

        # test qualifying group
        user_state.state.qualifying_groups.add(group)
        self.assertFalse(user_state.valid())
        user.groups.add(group)
        self.assertTrue(user_state.valid())

        # test qualifying corporation
        user_state.state.qualifying_corporations.add(corporation)
        self.assertFalse(user_state.valid())
        character.corporation = corporation
        character.save()
        state.qualifying_corporations.add(corporation)
        self.assertTrue(user.state.valid())
        state.qualifying_corporations.remove(corporation)

        # test qualifying alliance
        user_state.state.qualifying_alliances.add(alliance)
        self.assertFalse(user_state.valid())
        corporation.alliance = alliance 
        corporation.save()
        self.assertTrue(user.state.valid())

        user_state.delete()
        
    def test_get_higher_qualifying_state(self):
        user = User.objects.get(username="ModelTest")
        group = Group.objects.get(name="ModelTest")
        character = EveCharacter.objects.all()[0]
        corporation = EveCorporation.objects.all()[0]
        alliance = EveAlliance.objects.all()[0]
        state_lower = EveGroupState.objects.get(name="TestState")
        state_higher = EveGroupState.objects.get(name="TestStateHigher")

        user_state = EveUserState.objects.create(user=user, state=state_lower)
        
        # add qualifying group
        state_lower.qualifying_groups.add(group)
        state_higher.qualifying_groups.add(group)
        user.groups.add(group)

        self.assertTrue(user_state.get_higher_qualifying_state().name == "TestStateHigher")

        # clean up 
        state_lower.qualifying_groups.remove(group)
        state_higher.qualifying_groups.remove(group)
        user.groups.remove(group)
    
    def test_get_lower_qualifying_state(self):
        user = User.objects.get(username="ModelTest")
        group = Group.objects.get(name="ModelTest")
        character = EveCharacter.objects.all()[0]
        corporation = EveCorporation.objects.all()[0]
        alliance = EveAlliance.objects.all()[0]
        state_lower = EveGroupState.objects.get(name="TestState")
        state_higher = EveGroupState.objects.get(name="TestStateHigher")

        user_state = EveUserState.objects.create(user=user, state=state_higher)
        
        # add qualifying group
        state_higher.qualifying_groups.add(group)

        self.assertTrue(user_state.get_lower_qualifying_state().name == "TestState")
        
        
        
class EveUserStateTaskTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="TaskTest", password="TestPassword", email="test")
        group_a = Group.objects.create(name="QualifyingGroupA")
        group_b = Group.objects.create(name="QualifyingGroupB")
        group_c = Group.objects.create(name="QualifyingGroupC")
        Group.objects.create(name="DefaultGroupA")
        Group.objects.create(name="DefaultGroupB")
        Group.objects.create(name="EnablingGroupA")
        Group.objects.create(name="EnablingGroupB")
        default = EveGroupState.objects.create(name="DEFAULT", priority=-1)
        a = EveGroupState.objects.create(name="StateA", priority=1)
        b = EveGroupState.objects.create(name="StateB", priority=10)
        c = EveGroupState.objects.create(name="StateC", priority=20)
        a.qualifying_groups.add(group_a)
        b.qualifying_groups.add(group_b)
        c.qualifying_groups.add(group_c)
        EveUserState.objects.create(user=user, state=default)

    def test_update_user_state(self):
        user = User.objects.get(username="TaskTest")
        group_a = Group.objects.get(name="QualifyingGroupA")
        group_b = Group.objects.get(name="QualifyingGroupB")
        group_c = Group.objects.get(name="QualifyingGroupC")

        # test middle qualifier 
        user.groups.add(group_b)
        update_user_state(user.pk)
        user = User.objects.get(username="TaskTest")
        self.assertTrue(user.state.state.name == "StateB")

        # test traverse down - no change
        user.groups.add(group_a)
        update_user_state(user.pk)
        user = User.objects.get(username="TaskTest")
        self.assertTrue(user.state.state.name == "StateB")

        # test traverse down 
        user.groups.remove(group_b)
        update_user_state(user.pk)
        user = User.objects.get(username="TaskTest")
        self.assertTrue(user.state.state.name == "StateA")

        # test traverse up
        user.groups.add(group_c)
        update_user_state(user.pk)
        user = User.objects.get(username="TaskTest")
        self.assertTrue(user.state.state.name == "StateC")

        # test default state
        user.groups.clear()
        update_user_state(user.pk)
        user = User.objects.get(username="TaskTest")
        self.assertTrue(user.state.state.name == "DEFAULT")

    def test_verify_state_groups(self):
        user = User.objects.get(username="TaskTest")
        user_state = user.state 
        user_state.state = EveGroupState.objects.get(name="StateA")
        user_state.save()
        group_a = Group.objects.get(name="QualifyingGroupA")
        group_b = Group.objects.get(name="QualifyingGroupB")
        group_c = Group.objects.get(name="QualifyingGroupC")
        user.groups.add(group_a, group_c)
        state = EveGroupState.objects.get(name="StateA", priority=1)
        state.default_groups.add(group_b)
        state.enabling_groups.add(group_a)

        verify_user_state_groups(user.pk)

        user = User.objects.get(username="TaskTest")
        self.assertTrue(group_a in user.groups.all())
        self.assertTrue(group_b in user.groups.all())
        self.assertFalse(group_c in user.groups.all())


