#!/usr/bin/env python3
"""Build an offline, explicitly map-assisted reference; never infer collision."""
import argparse
import hashlib
import html
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(source, output):
    output.mkdir(parents=True, exist_ok=True)
    for sub in ('sources', 'rooms', 'tiles'):
        (output / sub).mkdir(exist_ok=True)
    inventory = []
    for path in sorted(source.iterdir()):
        if path.suffix.lower() not in ('.png', '.gif'):
            continue
        with Image.open(path) as im:
            record = dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()),
                          size=list(im.size), mode=im.mode, frames=getattr(im, 'n_frames', 1))
            # Keep all source credits and annotations; no inferred slicing of irregular sheets.
            name = path.stem.split(' - ', 2)[-1]
            dest = f'sources/{name}.png'
            im.convert('RGBA').save(output / dest)
            record['reference'] = dest
            inventory.append(record)
    world_record = next(a for a in inventory if 'Koholint Island (GBC)' in a['path'])
    world = Image.open(ROOT / world_record['path']).convert('RGB')
    # Visually inspected layout; fail closed if any of the 34 separator lines differ.
    assert world.size == (2577, 2640), 'Unexpected island sheet dimensions'
    green = (0, 128, 0)
    for x in range(0, 2577, 161):
        assert set(world.crop((x, 0, x + 1, 2065)).getdata()) <= {green, (0, 191, 0)}
    for y in range(0, 2065, 129):
        assert set(world.crop((0, y, 2577, y + 1)).getdata()) == {green}
    rooms, appearances = [], {}
    labeled = Image.new('RGB', (16 * 162, 16 * 146), '#15202b')
    draw = ImageDraw.Draw(labeled)
    for room_id in range(256):
        col, row = room_id % 16, room_id // 16
        x, y = 1 + col * 161, 1 + row * 129
        box = [x, y, x + 160, y + 128]
        crop = world.crop(box)
        filename = f'rooms/{room_id:02X}.png'
        crop.save(output / filename)
        cells = []
        for ty in range(8):
            line = []
            for tx in range(10):
                tile = crop.crop((tx * 16, ty * 16, (tx + 1) * 16, (ty + 1) * 16))
                key = sha(tile.tobytes())
                if key not in appearances:
                    tile.save(output / f'tiles/{key}.png')
                    appearances[key] = dict(id=key, image=f'tiles/{key}.png',
                        semantics='unlabeled', passability='unknown', occurrences=[])
                appearances[key]['occurrences'].append([room_id, tx, ty])
                line.append(key)
            cells.append(line)
        rooms.append(dict(room_id=room_id, room_hex=f'{room_id:02X}', grid=[col, row],
                          image=filename, source_box=box, appearance_grid=cells,
                          mapping_status='sheet_grid_inferred_not_live_verified',
                          transitions_status='unknown'))
        labeled.paste(crop, (col * 162, row * 146 + 16))
        draw.text((col * 162 + 3, row * 146 + 2), f'{room_id:02X}', fill='white')
    labeled.save(output / 'overworld-index.png')
    # Focus reference, not an action route or an assertion of connectivity.
    focus_ids = [0x40, 0x41, 0x42, 0x43, 0x50, 0x51, 0x52, 0x53,
                 0xC2, 0xC3, 0xD2, 0xD3, 0xE1, 0xE2, 0xE3, 0xF3]
    focus = Image.new('RGB', (4 * 324, 4 * 286), '#15202b')
    fd = ImageDraw.Draw(focus)
    for i, rid in enumerate(focus_ids):
        ox, oy = i % 4 * 324, i // 4 * 286
        fd.text((ox + 5, oy + 4), f'Overworld {rid:02X}', fill='white')
        with Image.open(output / rooms[rid]['image']) as crop:
            focus.paste(crop.resize((320, 256), Image.Resampling.NEAREST), (ox, oy + 22))
    focus.save(output / 'progression-reference.png')
    atlas = Image.new('RGB', (16 * 68, ((len(appearances) + 15) // 16) * 54), '#15202b')
    ad = ImageDraw.Draw(atlas)
    for i, entry in enumerate(appearances.values()):
        ax, ay = i % 16 * 68, i // 16 * 54
        with Image.open(output / entry['image']) as tile:
            atlas.paste(tile.resize((32, 32), Image.Resampling.NEAREST), (ax, ay))
        ad.text((ax, ay + 34), entry['id'][:8], fill='white')
    atlas.save(output / 'appearance-atlas.png')
    manifest = dict(schema_version=1, assistance='provided_full_map_and_artwork',
        runtime_integrated=False, source_assets=inventory,
        geometry=dict(origin=[1, 1], stride=[161, 129], room_size=[160, 128],
                      grid=[16, 16], separator_colors=[[0, 128, 0], [0, 191, 0]], separator_lines_verified=34,
                      tile_size=[16, 16], tile_grid=[10, 8]),
        limitations=['Room IDs inferred from row-major overworld grid; verify in live emulator.',
                     'Static maps may depict a different quest state or palette; blank placeholders are not terrain.',
                     'Appearance IDs are pixel hashes, not ROM tile IDs or collision labels.',
                     'No passability, one-way ledges, doors, or transitions inferred.',
                     'Interior Maps sheet is GB, not GBC; retained as reference only.',
                     'Map footer/alternate scenes retained in source but excluded from room grid.'],
        counts=dict(assets=len(inventory), rooms=len(rooms), tile_occurrences=20480,
                    unique_appearances=len(appearances)), rooms=rooms,
        appearances=list(appearances.values()))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    options = ''.join(f'<option value="{r["room_hex"]}">{r["room_hex"]}</option>' for r in rooms)
    links = ''.join(f'<li><a href="{html.escape(a["reference"], quote=True)}">{html.escape(Path(a["reference"]).stem)}</a></li>' for a in inventory)
    page = '''<!doctype html><meta charset="utf-8"><title>Tail Key asset reference</title>
<style>body{font:17px system-ui;background:#15202b;color:#eee;max-width:1200px;margin:32px auto;padding:0 20px}a{color:#8fdcff}img{image-rendering:pixelated;max-width:100%}#room{width:640px}select{font:inherit}li{margin:8px}small{color:#bbc}</style>
<h1>Tail Key → Tail Cave asset reference</h1>
<p>Provided-map assistance. Geometry checked; room IDs await live verification. Tile appearance does not establish collision or a usable transition.</p>
<label>Overworld room <select id="choice">OPTIONS</select></label>
<p><img id="room" src="rooms/41.png" alt="Selected overworld room"></p>
<p id="coords"></p><small>160 × 128 map pixels; no HUD. Match emulator coordinate offsets before setting movement targets.</small>
<p><a href="manifest.json">Machine-readable manifest</a> · <a href="overworld-index.png">All 256 indexed rooms</a></p>
<h2>Progression area references</h2><img src="progression-reference.png" alt="Indexed forest and southern overworld rooms">
<p><a href="appearance-atlas.png">Tile appearance atlas (hash labels)</a></p><h2>Original artwork references</h2><ul>LINKS</ul>
<script>const choice=document.getElementById('choice');function show(){const id=choice.value,n=parseInt(id,16);document.getElementById('room').src='rooms/'+id+'.png';document.getElementById('coords').textContent='Room '+id+' • sheet column '+(n%16)+', row '+Math.floor(n/16)+' • passability unverified';}choice.value='41';choice.onchange=show;show();</script>'''
    (output / 'index.html').write_text(page.replace('OPTIONS', options).replace('LINKS', links))
    return manifest['counts']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'runs/progression-assets-v2')
    args = parser.parse_args()
    print(json.dumps(build(ROOT / 'docs/reference/tilesets', args.output), indent=2))
