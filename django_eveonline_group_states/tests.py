from django.test import TestCase
from django.contrib.auth.models import User, Group
from django_eveonline_connector.models import *
from django_eveonline_group_states.models import EveGroupState, EveUserState
from django_eveonline_group_states.tasks import *

# Create your tests here.
class EveUserStateModelTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="ModelTest", password="TestPassword", email="test")
        User.objects.create_user(username="ModelTestFail", password="TestPassword", email="test")
        User.objects.create_user(username="ModelTestHigher", password="TestPassword", email="test")
        User.objects.create_user(username="ModelTestLower", password="TestPassword", email="test")
        Group.objects.create(name="ModelTest")
        EveToken.objects.create(user=User.objects.all()[0])
        EveCharacter.objects.create(name="ModelTest", external_id=0, token=EveToken.objects.all()[0])
        EveCorporation.objects.create(name="ModelTest", external_id=1)
        EveAlliance.objects.create(name="ModelTest", external_id=2)
        EveGroupState.objects.create(name="ModelTestState", priority=-2)

        group_a = Group.objects.create(name="QualifyingGroupA")
        group_b = Group.objects.create(name="QualifyingGroupB")
        group_c = Group.objects.create(name="QualifyingGroupC")
        state_a = EveGroupState.objects.create(name="StateA", priority=-1)
        state_b = EveGroupState.objects.create(name="StateB", priority=10)
        state_c = EveGroupState.objects.create(name="StateC", priority=20)
        state_a.qualifying_groups.add(group_a)
        state_b.qualifying_groups.add(group_b)
        state_c.qualifying_groups.add(group_c)

    def tearDown(self):
        User.objects.all().delete()
        Group.objects.all().delete()
        EveToken.objects.all().delete()
        EveCharacter.objects.all().delete()
        EveCorporation.objects.all().delete()
        EveAlliance.objects.all().delete()
        EveGroupState.objects.all().delete()
        

    def test_valid(self):
        print("test_qualify: starting test")
        user = User.objects.get(username="ModelTest")
        group = Group.objects.get(name="ModelTest")
        character = EveCharacter.objects.all()[0]
        corporation = EveCorporation.objects.all()[0]
        alliance = EveAlliance.objects.all()[0]
        state = EveGroupState.objects.all()[0]
        user_state = EveUserState.objects.create(user=user, state=state)

        # test qualifying group
        self.assertFalse(user.state.valid())
        user.groups.add(group)
        state.qualifying_groups.add(group)
        self.assertTrue(user.state.valid())
        state.qualifying_groups.remove(group)
        user.groups.remove(group)

        # test qualifying corporation
        self.assertFalse(user.state.valid())
        character.corporation = corporation
        character.save()
        state.qualifying_corporations.add(corporation)
        self.assertTrue(user.state.valid())
        state.qualifying_corporations.remove(corporation)

        # test qualifying alliance
        self.assertFalse(user.state.valid())
        corporation.alliance = alliance 
        corporation.save()
        state.qualifying_alliances.add(alliance)
        self.assertTrue(user.state.valid())

        # test no token failure
        user = User.objects.get(username="ModelTestFail")
        user_state = EveUserState.objects.create(user=user, state=state)
        self.assertFalse(user.state.valid())
        
    def test_get_higher_qualifying_state(self):
        user = User.objects.get(username="ModelTestHigher")
        user.groups.clear()
        user.groups.add(Group.objects.get(name="QualifyingGroupB"))
        user_state = EveUserState.objects.create(user=user, state=EveGroupState.objects.get(name="StateA"))
        self.assertTrue(user_state.get_higher_qualifying_state().name == "StateB")
    
    def test_get_lower_qualifying_state(self):
        user = User.objects.get(username="ModelTestLower")
        user.groups.clear()
        user_state = EveUserState.objects.create(user=user, state=EveGroupState.objects.get(name="StateB"))
        self.assertTrue(user_state.get_lower_qualifying_state().name == "StateA")
        
        
        
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


