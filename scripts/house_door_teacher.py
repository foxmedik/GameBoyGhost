"""Fresh-house guided controller assembly. Not qualified for training labels."""
from pathlib import Path
from develop_progression_teacher import (living_sword, learned_mushroom_crossing,
    learned_downstream_recovery, learned_tail_cave_key)
from gameboy_agent.live_forest import execute as forest
from gameboy_agent.toadstool_teacher import execute as mushroom
from gameboy_agent.witch_approach import execute as quest
from gameboy_agent.tail_cave_progression import execute_compass_room
from gameboy_agent import dungeon_items as items
from gameboy_agent.feather_return import (return_to_underground,
    underground_return_to_main, return_to_room0e)
from gameboy_agent.nightmare_entry import third_key_and_north_exit
from gameboy_agent.final_dungeon_stages import execute as final_stages
from gameboy_agent.progression import snapshot

ROOT=Path(__file__).resolve().parents[1]
MODELS={
    'mushroom':'runs/progression-dagger-v1-model/candidate.pt',
    'downstream':'runs/progression-downstream-recovery-v1-model/candidate.pt',
    'first_key':'runs/tail-cave-integration-dagger-v5-model/candidate.pt',
}


def execute(env,evidence,*,recovery=False):
    base=env.env
    def milestone(name):
        evidence.append(dict(kind=name,frame=env.frames,state=snapshot(env.pyboy)))
        print(f'Teacher stage {name}: frame={env.frames} health={snapshot(env.pyboy)["health"]}',flush=True)
    living_sword(env,evidence)
    forest(env,evidence)
    mushroom(env,evidence,forest_crossing=learned_mushroom_crossing(ROOT/MODELS['mushroom'],base))
    route=learned_downstream_recovery(ROOT/MODELS['downstream'],base)
    quest(env,evidence,route_controller=route)
    for option in ('exchange','tarin','tail_key','tail_cave'):
        quest(env,evidence,route_controller=route,**{option:True})
    learned_tail_cave_key(ROOT/MODELS['first_key'],base,True)(env,evidence)
    execute_compass_room(env,evidence)
    milestone('room15_cleared')
    for name,run in [
        ('compass_second_key',items.compass_and_second_key),
        ('map',items.acquire_map),
        ('south_worm_entry',items.reach_south_worm_entry),
        ('south_worm_passage',items.cross_south_worm_room),
        ('pushblock_entry',items.reach_pushblock_room),
        ('pushblock',items.solve_pushblock_room),
        ('beetles',items.spiked_beetles_to_stairs),
        ('underground',items.underground_to_ladder_exit),
        ('feather',items.acquire_feather_from_ladder_exit),
        ('feather_return',return_to_underground),
        ('platform_return',underground_return_to_main),
        ('main_return',return_to_room0e),
        ('third_key',third_key_and_north_exit),
        ('boss_door',final_stages),
    ]:
        if name=='underground':run(env,evidence,recovery=recovery)
        else:run(env,evidence)
        milestone(name)
