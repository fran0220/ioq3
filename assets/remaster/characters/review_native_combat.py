"""Actual-engine visual check, not a rules regression. Requires private q3dm1.

Usage: python review_native_combat.py ENGINE PRIVATE_BASEPATH
Uses original console commands and waits for real death logs, not guessed waits.
Review death/respawn/damage screenshots under PRIVATE_BASEPATH/home/demoq3/screenshots.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time


def main():
    engine, base = (Path(p).resolve() for p in sys.argv[1:])
    lines = []
    with (base/'character-death-review.log').open('w') as log:
        process = subprocess.Popen([
            str(engine), '+set','com_basegame','demoq3',
            '+set','fs_basepath',str(base),'+set','fs_homepath',str(base/'home'),
            '+set','r_renderer','opengl2','+set','r_mode','-1',
            '+set','r_customwidth','800','+set','r_customheight','600',
            '+set','r_fullscreen','0','+set','s_initsound','0',
            '+set','com_hunkMegs','256','+set','sv_pure','0',
            '+set','com_blood','0','+set','bot_minplayers','0',
            '+set','fraglimit','0','+devmap','q3dm1'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env={**os.environ,'SDL_VIDEODRIVER':'offscreen'})

        def consume():
            for line in process.stdout:
                log.write(line)
                log.flush()
                lines.append(line.strip())

        reader = threading.Thread(target=consume,daemon=True)
        reader.start()

        def send(command):
            process.stdin.write(command+'\n')
            process.stdin.flush()

        def wait_for(needle, start=0, timeout=20):
            deadline = time.monotonic()+timeout
            while time.monotonic()<deadline:
                if any(needle in line for line in lines[start:]):
                    return
                if process.poll() is not None:
                    raise RuntimeError('Engine exited before '+needle)
                time.sleep(.02)
            raise TimeoutError('No engine evidence for '+needle)

        def screenshot(name):
            start = len(lines)
            send('screenshotJPEG '+name)
            wait_for('Wrote screenshots/'+name+'.jpg',start)

        try:
            wait_for('entered the game')
            send('cg_debugAnim 1; cg_draw2D 0; cg_deferPlayers 0; model sarge; headmodel sarge')
            send('cg_thirdPerson 1; cg_thirdPersonAngle 90; cg_thirdPersonRange 95')
            for number, animation in enumerate((0,2,4),1):
                send('give weapons; give ammo; give health')
                # Server pickup commands must reach a snapshot before selection.
                time.sleep(.5)
                send('weapon 5; setviewpos 600 1250 24 0; +lookdown')
                time.sleep(1.2)
                start = len(lines)
                send('-lookdown; +attack')
                wait_for('blew himself up.',start)
                send('-attack')
                wait_for('Anim: '+str(animation),start)
                time.sleep(1.7)
                screenshot('character-native-verified-death-'+str(number))
                start = len(lines)
                send('+attack')
                time.sleep(.15)
                send('-attack')
                wait_for('Anim: 11',start)
                time.sleep(.3)
                screenshot('character-native-verified-respawn-'+str(number))
                print(f'PASS real death animation {animation} and live torso respawn',flush=True)
            send('model sarge/blue; headmodel sarge/blue; g_debugDamage 1; timescale .2')
            start = len(lines)
            send('addbot sarge 5; addbot sarge 5; addbot sarge 5; addbot sarge 5')
            wait_for('client:0 health:',start,timeout=60)
            time.sleep(.3)
            hits = [match for line in lines[start:]
                    if (match := re.search(r'client:0 health:(-?\d+) damage:(\d+)',line))]
            if not hits or int(hits[-1][1]) <= int(hits[-1][2]):
                raise RuntimeError('Last observed damage was fatal, not a pain-review pose')
            screenshot('character-native-verified-pain')
            print('PASS real nonfatal bot damage; inspect screenshot for pose quality',flush=True)
        finally:
            if process.poll() is None:
                send('-attack; -lookdown; timescale 1; g_debugDamage 0; quit')
            process.wait(timeout=15)
            reader.join(timeout=2)


if __name__ == '__main__':
    main()
