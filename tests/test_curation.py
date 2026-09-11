"""Label semantics: do not convert survival, censored windows, or setup to expertise."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
try:
    from gameboy_agent.curation import label_episode, cohort
except ModuleNotFoundError:
    raise unittest.SkipTest('Optional curation dependencies not installed')


def example(n=160):
    data = dict(step=list(range(n)), skill=['explore']*n, room=[[0,0,1]]*n,
                next_room=[[0,0,1]]*n, x=[i % 120 for i in range(n)], y=[50]*n,
                next_x=[(i+1) % 120 for i in range(n)], next_y=[50]*n,
                health=[24]*n, next_health=[24]*n, sword=[True]*n,
                terminated=[False]*n, truncated=[False]*n)
    return data, dict(rows=n, sword_step=None, status='budget_exhausted')


class CurationTest(unittest.TestCase):
    def test_clean_success_kept_when_later_episode_dies(self):
        d,m=example();d['skill'][:4]=['physical_setup']*4;d['skill'][4:12]=['acquire_sword']*8
        m.update(sword_step=12,status='death');d['next_health'][-1]=0;d['terminated'][-1]=True
        labels=label_episode(d,m)
        success=[x for x in labels if x['imitation_eligible']]
        self.assertEqual(len(success),1)
        self.assertEqual((success[0]['step_start'],success[0]['step_end']),(4,12))
        self.assertFalse(success[0]['contains_setup'])
        self.assertTrue(any(x['label']=='death_context' for x in labels))

    def test_damage_in_guard_excludes_navigation_candidate(self):
        d,m=example();d['next_health'][40]=20
        labels=label_episode(d,m)
        self.assertFalse(any(x['label']=='observed_safe_navigation' and x['step_start']==0 for x in labels))
        self.assertTrue(any(x['label']=='damage_event' for x in labels))

    def test_recovery_safe_and_censored_are_distinct(self):
        d,m=example();d['next_health'][10]=20
        labels=label_episode(d,m)
        self.assertTrue(any(x['label']=='observed_safe_recovery' for x in labels))
        self.assertFalse(any(x['imitation_eligible'] for x in labels))
        d,m=example(40);d['next_health'][10]=20;d['truncated'][-1]=True
        labels=label_episode(d,m)
        self.assertTrue(any(x['label']=='recovery_censored' for x in labels))
        self.assertFalse(any(x['label']=='observed_safe_recovery' for x in labels))

    def test_repeated_damage_and_lethal_hit(self):
        d,m=example();d['next_health'][10]=20;d['next_health'][30]=16
        self.assertTrue(any(x['label']=='recovery_repeat_damage' for x in label_episode(d,m)))
        d,m=example(20);d['next_health'][-1]=0;d['terminated'][-1]=True;m['status']='death'
        labels=label_episode(d,m)
        self.assertTrue(any(x['label']=='damage_event' for x in labels))
        self.assertFalse(any(x['lane']=='recovery' for x in labels))

    def test_variants_share_cohort_and_split(self):
        a=dict(setup_actions=[[0,0]]*20,epsilon=0,seed=1)
        b=dict(setup_actions=[[0,0]]*20,epsilon=.2,seed=90)
        self.assertEqual(cohort(a,'state-hash'),cohort(b,'state-hash'))


if __name__=='__main__':unittest.main()
