"""Compile the actual read-only observer against engine types; inspect JSON independently."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ObserverTest(unittest.TestCase):
    def test_snapshot_fields_escaping_ring_and_read_only(self):
        fixture = r'''
#include "code/client/cl_web_test.c"
clientActive_t cl;
clientConnection_t clc;
int Key_GetCatcher(void) { return KEYCATCH_CONSOLE; }
int main(void) {
    playerState_t *ps = &cl.snap.ps;
    clc.state = CA_ACTIVE;
    cl.snap.valid = qtrue; cl.snap.messageNum = 17; cl.snap.serverTime = 2350;
    ps->clientNum = 2; ps->origin[0] = -12.25f; ps->origin[1] = 31.5f; ps->origin[2] = 87;
    ps->velocity[2] = 270; ps->viewangles[1] = 73.25f;
    ps->stats[STAT_HEALTH] = 83; ps->stats[STAT_ARMOR] = 21; ps->stats[STAT_WEAPONS] = 68;
    ps->persistant[PERS_SCORE] = -3; ps->persistant[PERS_KILLED] = 4; ps->persistant[PERS_HITS] = 97;
    for (int i = 0; i < MAX_WEAPONS; i++) ps->ammo[i] = i * 3 - 1;
    cl.gameState.stringOffsets[CS_SERVERINFO] = 1;
    strcpy(cl.gameState.stringData + 1, "\\mapname\\q3dm1\"\n\t\200");
    cl.snap.parseEntitiesNum = MAX_PARSE_ENTITIES - 1;
    cl.snap.numEntities = 3; cl.parseEntitiesNum = MAX_PARSE_ENTITIES + 2;
    cl.parseEntities[MAX_PARSE_ENTITIES - 1].eType = ET_ITEM;
    cl.parseEntities[0].eType = ET_PLAYER; cl.parseEntities[0].number = 7;
    cl.parseEntities[0].pos.trBase[1] = -9.75f; cl.parseEntities[0].weapon = 5;
    cl.parseEntities[1].eType = ET_PLAYER; cl.parseEntities[1].number = 8;
    playerState_t before = *ps;
    puts(OG_WebTestSnapshot());
    if (memcmp(&before, ps, sizeof(before))) return 2;
    cl.parseEntitiesNum = cl.snap.parseEntitiesNum + MAX_PARSE_ENTITIES;
    puts(OG_WebTestSnapshot());
    cl.snap.valid = qfalse;
    puts(OG_WebTestSnapshot());
    memset(cl.gameState.stringData + 1, '\001', MAX_GAMESTATE_CHARS - 2);
    cl.gameState.stringData[MAX_GAMESTATE_CHARS - 1] = 0;
    cl.gameState.stringOffsets[CS_INTERMISSION] = 1;
    cl.gameState.stringOffsets[CS_SCORES1] = 1;
    cl.gameState.stringOffsets[CS_SCORES2] = 1;
    puts(OG_WebTestSnapshot());
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "observer.c"
            source.write_text(fixture)
            binary = Path(tmp) / "observer"
            subprocess.run(["cc", "-std=c99", "-DIOQ3_WEB_TEST_OBSERVER=1", "-I", str(ROOT),
                            str(source), "-o", str(binary)], check=True)
            rows = subprocess.check_output([str(binary)], text=True).splitlines()
        data, stale, invalid, large = map(json.loads, rows)
        self.assertEqual(data["keyCatcher"], 1)
        self.assertEqual(data["snap"]["messageNum"], 17)
        self.assertEqual(data["snap"]["serverTime"], 2350)
        ps = data["snap"]["ps"]
        self.assertEqual(ps["origin"], [-12.25, 31.5, 87])
        self.assertEqual(ps["stats"], {"health": 83, "armor": 21, "weapons": 68})
        self.assertEqual(ps["persistant"], {"score": -3, "killed": 4, "hits": 97})
        self.assertEqual(ps["ammo"], [i * 3 - 1 for i in range(16)])
        self.assertEqual(data["configstrings"]["serverInfo"], '\\mapname\\q3dm1"\n\t\x80')
        self.assertEqual([p["number"] for p in data["players"]], [7, 8])
        self.assertEqual(data["players"][0]["origin"], [0, -9.75, 0])
        self.assertEqual(stale["players"], [])
        self.assertFalse(invalid["snap"]["valid"])
        self.assertEqual(invalid["players"], [])
        self.assertTrue(all(s == '\x01' * 15998 for s in large["configstrings"].values()))


if __name__ == "__main__":
    unittest.main()
