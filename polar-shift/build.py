"""Builds PolarShift.sb3 — a pseudo-3D Scratch 3 game with touch controls.   Run:  python3 build.py

Game logic runs on a world floor plane (wx, wz) with height wy; every visible object projects itself
through the same perspective camera used to pre-render the 3D arena backdrop (see art3d.py)."""
import hashlib
import json
import os
import zipfile

import assets as A
import art3d as D
from dsl import *  # noqa: F401,F403

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "PolarShift.sb3")

files = {}


def add_costume(name, art):
    data, cx, cy = art
    raw = data.encode("utf-8")
    md5 = hashlib.md5(raw).hexdigest()
    files[md5 + ".svg"] = raw
    return {"assetId": md5, "name": name, "bitmapResolution": 1, "md5ext": md5 + ".svg",
            "dataFormat": "svg", "rotationCenterX": cx, "rotationCenterY": cy}


def add_sound(name, samples):
    raw, n = A.to_wav(samples)
    md5 = hashlib.md5(raw).hexdigest()
    files[md5 + ".wav"] = raw
    return {"assetId": md5, "name": name, "dataFormat": "wav", "format": "", "rate": A.SR,
            "sampleCount": n, "md5ext": md5 + ".wav"}


# camera constants (rounded; identical to the backdrop's projection)
CF, CC, CH, CH0 = round(D.F, 3), round(D.C, 3), round(D.CAMH, 3), round(D.H0, 3)
PX, PZ = D.XW - 4, D.ZW - 4          # player bounds
EX, EZ = D.XW + 4, D.ZW + 4          # enemy bounds

# =====================================================================  globals
GLOBALS = ["state", "score", "best", "mult", "combo", "wave", "energy", "px", "py", "ppol", "pinv",
           "enemies", "flipT", "fx", "fy", "si", "sn", "sd", "ov",
           "psx", "psy", "gx", "gy", "pk", "jx", "jy", "jcap", "fcap"]
LISTS = ["tx", "ty", "lx", "ly", "shx", "shy", "shw", "sqx", "sqy", "sqc", "sqs",
         "rqx", "rqy", "rqc", "rqs", "pqx", "pqy", "pqc"]

stage = Target("Stage", is_stage=True)
for g in GLOBALS:
    stage.vars[g] = "g_" + g
for l in LISTS:
    stage.lists[l] = "l_" + l


def notplay():
    return not_(eq(V("state"), "play"))


def anykey():
    return or_(key("space"), mousedown())


def clear_lists():
    return [delall(l) for l in LISTS]


def proj_proc(t):
    """per-sprite 'proj': world (wx,wy,wz) -> screen position, size bs*k"""
    t.script(procdef("proj"),
             setv("k", div(CF, add(V("wz"), CC))),
             gotoxy(mul(V("wx"), V("k")), add(CH0, mul(sub(V("wy"), CH), V("k")))),
             setsize(mul(V("bs"), V("k"))))


def depth_sort():
    # nearer objects end up on higher layers
    return [back(), fwd(round_(div(sub(D.ZW + 20, V("wz")), 40)))]


# =====================================================================  STAGE
stage.script(whenflag(),
             setv("state", "title"), setv("score", 0), setv("mult", 1), setv("ppol", 1), setv("ov", 0),
             setv("jx", 0), setv("jy", 0), setv("jcap", 0), setv("fcap", 0),
             *clear_lists(), backdrop("arena"), bcast("title"))
stage.script(whenflag(), setvol(45), forever(playwait("music")))
stage.script(whenrecv("title"),
             wait(0.3), waituntil(not_(anykey())), waituntil(anykey()),
             if_(eq(V("state"), "title"), bcast("start")))
stage.script(whenrecv("start"),
             setv("state", "play"), setv("score", 0), setv("mult", 1), setv("combo", 0), setv("wave", 0),
             setv("enemies", 0), setv("flipT", 99), setv("fx", 0), setv("fy", 0), setv("ov", 0),
             *clear_lists(),
             bcast("go"),
             until(notplay(),
                   chv("wave", 1), bcast("wave"), play("wave"),
                   wait(1.5),
                   setv("sn", add(3, mul(V("wave"), 2))),
                   if_(gt(V("sn"), 26), setv("sn", 26)),
                   setv("sd", sub(1.15, mul(V("wave"), 0.07))),
                   if_(lt(V("sd"), 0.3), setv("sd", 0.3)),
                   setv("si", 0),
                   until(or_(not_(lt(V("si"), V("sn"))), notplay()),
                         clone("Drone"), chv("si", 1), wait(V("sd"))),
                   waituntil(or_(lt(V("enemies"), 1), notplay())),
                   if_(eq(V("state"), "play"),
                       chv("score", mul(V("wave"), 100)),
                       addl("pqx", 0), addl("pqy", 0), addl("pqc", "clear"), play("clear"),
                       wait(1.2))))
stage.script(whenrecv("start"),
             until(notplay(),
                   if_(gt(V("combo"), 0),
                       chv("combo", -1),
                       if_(lt(V("combo"), 1), setv("mult", 1))),
                   chv("flipT", 1)))
stage.script(whenrecv("die"),
             setv("state", "over"),
             if_(gt(V("score"), V("best")), setv("best", V("score"))),
             play("boom"),
             wait(1.5), waituntil(not_(anykey())), waituntil(anykey()),
             if_(eq(V("state"), "over"), bcast("start")))

# =====================================================================  CORE (player)
core = Target("Core", ["vx", "vz", "sp", "wx", "wy", "wz", "k", "bs", "cl"], glob=stage)
proj_proc(core)
core.script(whenflag(), hide(), rotstyle("don't rotate"))
core.script(whenrecv("title"), hide())


def bounce(v, w, lim):
    return [if_(gt(V(w), lim), setv(w, lim), setv(v, mul(V(v), -0.6))),
            if_(lt(V(w), -lim), setv(w, -lim), setv(v, mul(V(v), -0.6)))]


core.script(whenrecv("go"),
            setv("wx", 0), setv("wz", -40), setv("wy", 16), setv("vx", 0), setv("vz", 0), setv("bs", 125),
            setv("ppol", 1), setv("cl", "c"), setv("energy", 100), setv("pinv", 45),
            costume("c1"), cleareff(), show(), setv("sp", 1),
            until(notplay(),
                  if_(or_(key("right arrow"), key("d")), chv("vx", 0.75)),
                  if_(or_(key("left arrow"), key("a")), chv("vx", -0.75)),
                  if_(or_(key("up arrow"), key("w")), chv("vz", 0.75)),
                  if_(or_(key("down arrow"), key("s")), chv("vz", -0.75)),
                  chv("vx", add(mul(V("jx"), 0.8), V("fx"))), chv("vz", add(mul(V("jy"), 0.8), V("fy"))),
                  setv("fx", 0), setv("fy", 0),
                  setv("vx", mul(V("vx"), 0.88)), setv("vz", mul(V("vz"), 0.88)),
                  chv("wx", V("vx")), chv("wz", V("vz")),
                  *bounce("vx", "wx", PX), *bounce("vz", "wz", PZ),
                  setv("px", V("wx")), setv("py", V("wz")),
                  setv("wy", add(16, mul(3, mathop("sin", mul(timer(), 400))))),
                  call("proj"), *depth_sort(),
                  costume(join(V("cl"), add(mod(round_(mul(timer(), 14)), 8), 1))),
                  setv("psx", xpos()), setv("psy", ypos()), setv("pk", V("k")),
                  setv("gx", mul(V("wx"), V("k"))), setv("gy", add(CH0, mul(-CH, V("k")))),
                  if_(lt(V("energy"), 100), chv("energy", 0.4),
                      if_(gt(V("energy"), 100), setv("energy", 100))),
                  ifelse(or_(key("space"), eq(V("fcap"), 1)),
                         [if_(eq(V("sp"), 0),
                              setv("sp", 1),
                              ifelse(lt(V("energy"), 30), [play("denied")], [call("flip")]))],
                         [setv("sp", 0)]),
                  addl("tx", xpos()), addl("ty", ypos()),
                  if_(gt(llen("tx"), 10), dell("tx", 1), dell("ty", 1)),
                  ifelse(gt(V("pinv"), 0),
                         [chv("pinv", -1),
                          ifelse(lt(mod(V("pinv"), 6), 3), [seteff("ghost", 65)], [seteff("ghost", 0)])],
                         [seteff("ghost", 0)])))
core.script(procdef("flip"),
            setv("ppol", sub(0, V("ppol"))), chv("energy", -30), setv("flipT", 0),
            ifelse(eq(V("ppol"), 1), [setv("cl", "c"), play("flipup")], [setv("cl", "m"), play("flipdown")]),
            addl("rqx", V("wx")), addl("rqy", V("wz")), addl("rqc", V("ppol")), addl("rqs", 260))
core.script(whenrecv("die"),
            addl("sqx", V("px")), addl("sqy", V("py")), addl("sqc", 2), addl("sqs", 2),
            addl("rqx", V("px")), addl("rqy", V("py")), addl("rqc", 2), addl("rqs", 420),
            hide())

# =====================================================================  DRONE (enemies)
drone = Target("Drone", ["vx", "vz", "vy", "pol", "kind", "d", "dx", "dy", "a", "age", "sw", "sp", "mx",
                         "acc", "h", "t", "rr", "pts", "wx", "wy", "wz", "k", "bs", "cl", "fr", "ph"], glob=stage)
proj_proc(drone)
drone.script(whenflag(), hide())
drone.script(procdef("skin"), ifelse(eq(V("pol"), 1), [setv("cl", "c")], [setv("cl", "m")]))
drone.script(procdef("anim"),
             ifelse(eq(V("kind"), 3),
                    [setv("h", mathop("atan", div(V("vx"), add(V("vz"), 0.0001)))),
                     if_(lt(V("vz"), 0), chv("h", 180)),
                     setv("fr", add(mod(round_(div(V("h"), 45)), 8), 1))],
                    [setv("fr", add(mod(mathop("floor", div(V("age"), add(V("kind"), 1))), 8), 1))]),
             costume(join(join(V("kind"), V("cl")), V("fr"))))
drone.script(procdef("place"),
             setv("dx", 0), setv("dy", 0),
             until(gt(sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy")))), 200),
                   ifelse(eq(rnd(1, 2), 1),
                          [setv("wx", rnd(-D.XW + 5, D.XW - 5)),
                           ifelse(eq(rnd(1, 2), 1), [setv("wz", D.ZW - 5)], [setv("wz", -D.ZW + 5)])],
                          [setv("wz", rnd(-D.ZW + 5, D.ZW - 5)),
                           ifelse(eq(rnd(1, 2), 1), [setv("wx", D.XW - 5)], [setv("wx", -D.XW + 5)])]),
                   setv("dx", sub(V("px"), V("wx"))), setv("dy", sub(V("py"), V("wz")))))
drone.script(whenclone(),
             chv("enemies", 1),
             setv("kind", 1), setv("pts", 10), setv("rr", 26), setv("bs", 125),
             if_(and_(gt(V("wave"), 2), eq(rnd(1, 4), 1)), setv("kind", 2), setv("pts", 20), setv("rr", 27)),
             if_(and_(gt(V("wave"), 3), eq(rnd(1, 4), 1)), setv("kind", 3), setv("pts", 25), setv("rr", 22), setv("bs", 120)),
             ifelse(eq(rnd(1, 2), 1), [setv("pol", 1)], [setv("pol", -1)]),
             ifelse(eq(rnd(1, 2), 1), [setv("sw", 1)], [setv("sw", -1)]),
             call("skin"), call("place"),
             setv("vx", 0), setv("vz", 0), setv("age", 0), setv("ph", rnd(0, 360)),
             setv("acc", add(0.2, mul(V("wave"), 0.015))),
             setv("mx", add(3, mul(V("wave"), 0.12))),
             if_(gt(V("mx"), 5.5), setv("mx", 5.5)),
             if_(eq(V("kind"), 3), setv("acc", mul(V("acc"), 1.7)), setv("mx", add(V("mx"), 1.6))),
             # telegraph the landing spot, then drop in from the sky
             addl("rqx", V("wx")), addl("rqy", V("wz")), addl("rqc", V("pol")), addl("rqs", 90),
             setv("wy", 300), setv("vy", 0), call("anim"), call("proj"), seteff("ghost", 0), show(),
             until(lt(V("wy"), 15),
                   chv("vy", -1.4), chv("wy", V("vy")), chv("age", 1),
                   call("anim"), call("proj"), *depth_sort()),
             setv("wy", 14),
             addl("rqx", V("wx")), addl("rqy", V("wz")), addl("rqc", V("pol")), addl("rqs", 70),
             until(notplay(), call("step")),
             wait(rnd(0.0, 0.7)),
             addl("sqx", V("wx")), addl("sqy", V("wz")), addl("sqc", V("pol")), addl("sqs", 0),
             chv("enemies", -1), delclone())


def wall(v, w, lim):
    return [if_(gt(V(w), lim), setv(w, lim), setv(v, sub(0, mathop("abs", V(v))))),
            if_(lt(V(w), -lim), setv(w, -lim), setv(v, mathop("abs", V(v))))]


drone.script(procdef("step"),
             setv("dx", sub(V("px"), V("wx"))), setv("dy", sub(V("py"), V("wz"))),
             setv("d", add(sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy")))), 0.1)),
             # likes repel (inside 115) and hover/orbit; opposites home straight in
             ifelse(eq(V("pol"), V("ppol")),
                    [ifelse(lt(V("d"), 115),
                            [setv("a", mul(div(sub(115, V("d")), 115), -0.5))],
                            [setv("a", 0.05)]),
                     chv("vx", sub(mul(V("a"), div(V("dx"), V("d"))), mul(mul(V("sw"), 0.07), div(V("dy"), V("d"))))),
                     chv("vz", add(mul(V("a"), div(V("dy"), V("d"))), mul(mul(V("sw"), 0.07), div(V("dx"), V("d")))))],
                    [setv("a", V("acc")),
                     chv("vx", mul(sub(mul(V("mx"), div(V("dx"), V("d"))), V("vx")), mul(V("acc"), 0.3))),
                     chv("vz", mul(sub(mul(V("mx"), div(V("dy"), V("d"))), V("vz")), mul(V("acc"), 0.3)))]),
             # equal & opposite tug on the player
             if_(lt(V("d"), 200),
                 chv("fx", mul(mul(V("a"), div(V("dx"), V("d"))), -0.12)),
                 chv("fy", mul(mul(V("a"), div(V("dy"), V("d"))), -0.12))),
             setv("vx", mul(V("vx"), 0.975)), setv("vz", mul(V("vz"), 0.975)),
             setv("sp", sqrt(add(mul(V("vx"), V("vx")), mul(V("vz"), V("vz"))))),
             if_(gt(V("sp"), V("mx")),
                 setv("vx", mul(V("vx"), div(V("mx"), V("sp")))),
                 setv("vz", mul(V("vz"), div(V("mx"), V("sp"))))),
             chv("wx", V("vx")), chv("wz", V("vz")),
             *wall("vx", "wx", EX), *wall("vz", "wz", EZ),
             chv("age", 1),
             setv("wy", add(14, mul(4, mathop("sin", add(mul(V("age"), 8), V("ph")))))),
             # prisms flicker white, then swap polarity
             if_(eq(V("kind"), 2),
                 setv("t", mod(V("age"), 150)),
                 if_(gt(V("t"), 120),
                     ifelse(lt(mod(V("age"), 6), 3), [setv("cl", "w")], [call("skin")])),
                 if_(eq(V("t"), 0),
                     setv("pol", sub(0, V("pol"))), call("skin"),
                     addl("rqx", V("wx")), addl("rqy", V("wz")), addl("rqc", V("pol")), addl("rqs", 110))),
             call("anim"), call("proj"), *depth_sort(),
             # floor shadow
             addl("shx", mul(V("wx"), V("k"))), addl("shy", add(CH0, mul(-CH, V("k")))), addl("shw", V("k")),
             # magnetic tether lines (drawn by FX)
             if_(and_(not_(eq(V("pol"), V("ppol"))), lt(V("d"), 180)),
                 addl("lx", xpos()), addl("ly", ypos())),
             # contact
             if_(lt(V("d"), V("rr")),
                 ifelse(eq(V("pol"), V("ppol")),
                        [call("absorb")],
                        [if_(and_(lt(V("d"), sub(V("rr"), 6)), and_(lt(V("pinv"), 1), eq(V("state"), "play"))),
                             setv("state", "over"), bcast("die"))])))
drone.script(procdef("absorb"),
             ifelse(lt(V("flipT"), 13),
                    [chv("score", mul(mul(V("pts"), 2), V("mult"))),
                     addl("pqx", V("wx")), addl("pqy", V("wz")), addl("pqc", "clutch"),
                     chv("energy", 10), addl("sqs", 3)],
                    [chv("score", mul(V("pts"), V("mult"))), addl("sqs", 1)]),
             addl("sqx", V("wx")), addl("sqy", V("wz")), addl("sqc", V("pol")),
             chv("mult", 1), if_(gt(V("mult"), 50), setv("mult", 50)), setv("combo", 75),
             chv("energy", 18), if_(gt(V("energy"), 100), setv("energy", 100)),
             addl("rqx", V("wx")), addl("rqy", V("wz")), addl("rqc", V("pol")), addl("rqs", 150),
             chv("enemies", -1), delclone())

# =====================================================================  SPARK (3D particles + hit sounds)
spark = Target("Spark", ["wx", "wy", "wz", "vx", "vy", "vz", "k", "bs", "s", "kc", "big", "n2", "p", "an", "v"],
               glob=stage)
proj_proc(spark)


def color_costume(var, suffix=None):
    def c(letter_):
        return costume(letter_ if suffix is None else join(letter_, suffix))
    return ifelse(eq(V(var), 1), [c("c")], [ifelse(eq(V(var), -1), [c("m")], [c("w")])])


spark.script(whenflag(), hide(), forever(if_(gt(llen("sqx"), 0), call("burst"))))
spark.script(procdef("burst"),
             until(eq(llen("sqx"), 0),
                   setv("wx", item("sqx", 1)), setv("wz", item("sqy", 1)), setv("wy", 16),
                   setv("kc", item("sqc", 1)), setv("s", item("sqs", 1)),
                   color_costume("kc"),
                   if_(or_(eq(V("s"), 1), eq(V("s"), 3)),
                       setv("p", mul(sub(V("mult"), 1), 14)), if_(gt(V("p"), 280), setv("p", 280)),
                       sndeff("PITCH", V("p")), play("pop")),
                   if_(eq(V("s"), 3), play("clutch")),
                   setv("big", V("s")),
                   setv("n2", 10), if_(eq(V("s"), 2), setv("n2", 36)), if_(eq(V("s"), 0), setv("n2", 5)),
                   repeat(V("n2"), clone()),
                   dell("sqx", 1), dell("sqy", 1), dell("sqc", 1), dell("sqs", 1)))
spark.script(whenclone(),
             setv("an", rnd(0, 360)), setv("v", rnd(1.5, 5.0)), setv("vy", rnd(2.0, 7.0)),
             if_(eq(V("big"), 2), setv("v", rnd(2.0, 9.0)), setv("vy", rnd(3.0, 12.0))),
             setv("vx", mul(V("v"), mathop("cos", V("an")))), setv("vz", mul(V("v"), mathop("sin", V("an")))),
             setv("bs", rnd(50, 110)), call("proj"), front(), show(),
             repeat(20,
                    chv("vy", -0.45), chv("wx", V("vx")), chv("wy", V("vy")), chv("wz", V("vz")),
                    if_(lt(V("wy"), 0), setv("wy", 0), setv("vy", mul(V("vy"), -0.5))),
                    setv("vx", mul(V("vx"), 0.96)), setv("vz", mul(V("vz"), 0.96)),
                    call("proj"), cheff("ghost", 5)),
             delclone())

# =====================================================================  RING (floor shockwaves)
ringt = Target("Ring", ["wx", "wz", "k", "g", "gc", "kc", "band"], glob=stage)
ringt.script(whenflag(), hide(), forever(if_(gt(llen("rqx"), 0), call("spawn"))))
ringt.script(procdef("spawn"),
             until(eq(llen("rqx"), 0),
                   setv("wx", item("rqx", 1)), setv("wz", item("rqy", 1)), setv("kc", item("rqc", 1)),
                   setv("band", 2), if_(lt(V("wz"), -80), setv("band", 1)), if_(gt(V("wz"), 80), setv("band", 3)),
                   color_costume("kc", V("band")),
                   setv("k", div(CF, add(V("wz"), CC))),
                   gotoxy(mul(V("wx"), V("k")), add(CH0, mul(-CH, V("k")))),
                   setv("g", div(item("rqs", 1), 12)), setv("gc", 8), setsize(mul(V("gc"), V("k"))), clone(),
                   dell("rqx", 1), dell("rqy", 1), dell("rqc", 1), dell("rqs", 1)))
ringt.script(whenclone(), back(), seteff("ghost", 0), show(),
             repeat(12, chv("gc", V("g")), setsize(mul(V("gc"), V("k"))), cheff("ghost", 8.5)), delclone())

# =====================================================================  POPUP (floating text)
popup = Target("Popup", ["k"], glob=stage)
popup.script(whenflag(), hide(), forever(if_(gt(llen("pqx"), 0), call("spawn"))))
popup.script(procdef("spawn"),
             until(eq(llen("pqx"), 0),
                   setv("k", div(CF, add(item("pqy", 1), CC))),
                   gotoxy(mul(item("pqx", 1), V("k")), add(CH0, mul(sub(45, CH), V("k")))),
                   costume(item("pqc", 1)), clone(),
                   dell("pqx", 1), dell("pqy", 1), dell("pqc", 1)))
popup.script(whenclone(), setsize(40), seteff("ghost", 0), show(), front(),
             repeat(5, chsize(15)), repeat(4, chsize(-2.5)),
             repeat(20, chy(1.3), cheff("ghost", 5)), delclone())

# =====================================================================  BANNER (title / wave / game over)
banner = Target("Banner", ["w"], glob=stage)
banner.script(whenflag(), gotoxy(0, 0), costume("title"), setsize(100), show(), front())
banner.script(whenrecv("title"),
              costume("title"), seteff("ghost", 0), show(), front(),
              until(not_(eq(V("state"), "title")),
                    setsize(add(100, mul(1.2, mathop("sin", mul(timer(), 200)))))),
              hide())
banner.script(whenrecv("wave"),
              setv("w", V("wave")), if_(gt(V("w"), 30), setv("w", 30)),
              costume(join("wave", V("w"))), setsize(130), seteff("ghost", 100), show(), front(),
              repeat(8, chsize(-3.75), cheff("ghost", -12.5)),
              wait(1.1),
              repeat(10, cheff("ghost", 10), chsize(2)), hide())
banner.script(whenrecv("die"),
              stop("other scripts in sprite"), hide(), wait(0.9),
              costume("over"), seteff("ghost", 0), setsize(70), show(), front(),
              repeat(6, chsize(5)), setv("ov", 1))
banner.script(whenrecv("start"), stop("other scripts in sprite"), hide())

# =====================================================================  DIGITS (7-segment HUD)
digits = Target("Digits", ["grp", "idx", "s", "on"], glob=stage)
digits.script(whenflag(), hide(), call("make"))
digits.script(procdef("make"),
              setv("grp", 1),
              repeat(4, setv("idx", 1), repeat(7, clone(), chv("idx", 1)), chv("grp", 1)))


def centered(spacing, y):
    return gotoxy(mul(sub(V("idx"), div(add(length(V("s")), 1), 2)), spacing), y)


digits.script(whenclone(),
              forever(
                  setv("on", 0),
                  if_(eq(V("grp"), 1),
                      setv("s", V("score")), setsize(100),
                      if_(not_(eq(V("state"), "title")), setv("on", 1)),
                      gotoxy(add(-236, mul(V("idx"), 15)), 160)),
                  if_(eq(V("grp"), 2),
                      setv("s", join("x", V("mult"))), setsize(115),
                      if_(and_(eq(V("state"), "play"), gt(V("mult"), 1)), setv("on", 1)),
                      gotoxy(sub(226, mul(sub(length(V("s")), V("idx")), 17)), 160)),
                  if_(eq(V("grp"), 3),
                      setv("s", V("best")), setsize(100),
                      ifelse(eq(V("state"), "title"),
                             [if_(gt(V("best"), 0), setv("on", 1)),
                              gotoxy(add(-204, mul(V("idx"), 15)), 160)],
                             [if_(eq(V("ov"), 1), setv("on", 1)), centered(15, -66)])),
                  if_(eq(V("grp"), 4),
                      setv("s", V("score")), setsize(170),
                      if_(eq(V("ov"), 1), setv("on", 1)), centered(26, -4)),
                  ifelse(and_(eq(V("on"), 1), not_(gt(V("idx"), length(V("s"))))),
                         [costume(join("d", letter(V("idx"), V("s")))), show(), front()],
                         [hide()])))

# =====================================================================  PAD (touch joystick + flip button)
pad = Target("Pad", ["role", "bx", "by", "ox", "oy", "ln"], glob=stage)
BX, BY, FBX, FBY = -176, -112, 180, -112
pad.script(whenflag(),
           hide(), setv("bx", BX), setv("by", BY),
           setv("role", 1), clone(), setv("role", 2), clone(), setv("role", 0),
           forever(
               ifelse(mousedown(),
                      [setv("ox", sub(mousex(), V("bx"))), setv("oy", sub(mousey(), V("by"))),
                       setv("ln", add(sqrt(add(mul(V("ox"), V("ox")), mul(V("oy"), V("oy")))), 0.001)),
                       if_(and_(eq(V("jcap"), 0), eq(V("fcap"), 0)),
                           ifelse(and_(lt(V("ln"), 85), eq(V("state"), "play")),
                                  [setv("jcap", 1)], [setv("fcap", 1)])),
                       if_(eq(V("jcap"), 1),
                           if_(gt(V("ln"), 50),
                               setv("ox", mul(V("ox"), div(50, V("ln")))),
                               setv("oy", mul(V("oy"), div(50, V("ln"))))),
                           setv("jx", div(V("ox"), 50)), setv("jy", div(V("oy"), 50)))],
                      [setv("jcap", 0), setv("fcap", 0), setv("jx", 0), setv("jy", 0)]),
               ifelse(eq(V("state"), "play"),
                      [gotoxy(V("bx"), V("by")), costume("base"), setsize(100),
                       ifelse(eq(V("jcap"), 1), [seteff("ghost", 15)], [seteff("ghost", 45)]),
                       show(), front()],
                      [hide()])))
pad.script(whenclone(),
           forever(
               ifelse(eq(V("state"), "play"),
                      [ifelse(eq(V("role"), 1),
                              [gotoxy(add(V("bx"), mul(V("jx"), 50)), add(V("by"), mul(V("jy"), 50))),
                               costume("knob"),
                               ifelse(eq(V("jcap"), 1), [seteff("ghost", 0)], [seteff("ghost", 40)])],
                              [gotoxy(FBX, FBY),
                               ifelse(lt(V("energy"), 30), [costume("flipoff")],
                                      [ifelse(eq(V("ppol"), 1), [costume("flipm")], [costume("flipc")])]),
                               ifelse(eq(V("fcap"), 1), [setsize(88), seteff("ghost", 0)],
                                      [setsize(100), seteff("ghost", 30)])]),
                       show(), front()],
                      [hide()])))

# =====================================================================  SPACER (layer padding for depth sorting)
spacer = Target("Spacer", [], glob=stage)
spacer.script(whenflag(), hide(), repeat(16, clone()))
spacer.script(whenclone(), back())

# =====================================================================  FX (pen: floor light, shadows, tethers, trail, HUD bars)
fx = Target("FX", ["i", "ex", "ey", "mx", "my", "w"], glob=stage)
fx.script(whenflag(), hide(), pen_clear())
fx.script(whenrecv("title"), pen_clear())
fx.script(whenrecv("go"), until(notplay(), call("render")), wait(0.15), pen_clear(),
          delall("shx"), delall("shy"), delall("shw"))


def by_pol(var, same):
    a, b = (A.CY, A.MG) if same else (A.MG, A.CY)
    return ifelse(eq(V(var), 1), [pen_color(a)], [pen_color(b)])


def seg(x0, y0, x1, y1):
    return [pen_up(), gotoxy(x0, y0), pen_down(), gotoxy(x1, y1), pen_up()]


def hseg(cx, cy, half):
    return seg(sub(cx, half), cy, add(cx, half), cy)


fx.script(procdef("render"),
          pen_clear(),
          # colored light pool the core casts on the floor
          by_pol("ppol", True),
          pen_param("transparency", 88), pen_size(mul(V("pk"), 70)), *hseg(V("gx"), V("gy"), mul(V("pk"), 22)),
          pen_param("transparency", 75), pen_size(mul(V("pk"), 36)), *hseg(V("gx"), V("gy"), mul(V("pk"), 12)),
          # shadows
          pen_color("#000000"), pen_param("transparency", 45),
          pen_size(mul(V("pk"), 13)), *hseg(V("gx"), V("gy"), mul(V("pk"), 8)),
          setv("i", 1),
          repeat(llen("shx"),
                 setv("w", item("shw", V("i"))), pen_size(mul(V("w"), 13)),
                 *hseg(item("shx", V("i")), item("shy", V("i")), mul(V("w"), 8)),
                 chv("i", 1)),
          delall("shx"), delall("shy"), delall("shw"),
          # crackling magnetic tethers toward incoming killers
          by_pol("ppol", False), setv("i", 1),
          repeat(llen("lx"),
                 setv("ex", item("lx", V("i"))), setv("ey", item("ly", V("i"))),
                 setv("mx", add(div(add(V("psx"), V("ex")), 2), rnd(-9.0, 9.0))),
                 setv("my", add(div(add(V("psy"), V("ey")), 2), rnd(-9.0, 9.0))),
                 pen_param("transparency", 70), pen_size(6),
                 pen_up(), gotoxy(V("psx"), V("psy")), pen_down(), gotoxy(V("mx"), V("my")),
                 gotoxy(V("ex"), V("ey")), pen_up(),
                 pen_param("transparency", 10), pen_size(1.5),
                 gotoxy(V("psx"), V("psy")), pen_down(), gotoxy(V("mx"), V("my")),
                 gotoxy(V("ex"), V("ey")), pen_up(),
                 chv("i", 1)),
          delall("lx"), delall("ly"),
          # comet trail
          by_pol("ppol", True), setv("i", 1), pen_up(),
          repeat(llen("tx"),
                 pen_size(mul(mul(V("i"), 2.6), V("pk"))),
                 pen_param("transparency", add(35, mul(sub(llen("tx"), V("i")), 6))),
                 gotoxy(item("tx", V("i")), item("ty", V("i"))), pen_down(), chv("i", 1)),
          pen_up(),
          # energy bar (top center, 3 notches = 3 flips)
          pen_param("transparency", 0), pen_size(9), pen_color("#1b2238"), *seg(-80, 164, 80, 164),
          ifelse(lt(V("energy"), 30), [pen_color("#ff4d5e")], [by_pol("ppol", True)]),
          *seg(-80, 164, add(-80, mul(V("energy"), 1.6)), 164),
          pen_color("#070912"), pen_size(2),
          *seg(-32, 159, -32, 169), *seg(16, 159, 16, 169), *seg(64, 159, 64, 169),
          # combo timer
          if_(gt(V("mult"), 1),
              pen_color(A.YL), pen_size(3), *seg(sub(226, mul(V("combo"), 1.2)), 145, 226, 145)))

# =====================================================================  FLASH
flash = Target("Flash", [], glob=stage)
flash.script(whenflag(), hide())
flash.script(whenrecv("die"), gotoxy(0, 0), seteff("ghost", 15), show(), front(),
             repeat(17, cheff("ghost", 5)), hide())


# =====================================================================  assemble
def sprite_json(t, costumes, sounds, layer, visible=False):
    return {"isStage": False, "name": t.name,
            "variables": {vid: [n, 0] for n, vid in t.vars.items()},
            "lists": {}, "broadcasts": {}, "blocks": t.blocks, "comments": {},
            "currentCostume": 0, "costumes": costumes, "sounds": sounds, "volume": 100,
            "layerOrder": layer, "visible": visible, "x": 0, "y": 0, "size": 100, "direction": 90,
            "draggable": False, "rotationStyle": "all around"}


def main():
    def trio(f):
        return [add_costume(n, f(c)) for n, c in (("c", A.CY), ("m", A.MG), ("w", A.WH))]

    drone_cos = []
    for k in (1, 2, 3):
        for letter_, col in (("c", A.CY), ("m", A.MG)):
            for i, art in enumerate(D.drone_frames(k, col)):
                drone_cos.append(add_costume("%d%s%d" % (k, letter_, i + 1), art))
    for i, art in enumerate(D.drone_frames(2, "#e8e8ff", white=True)):
        drone_cos.append(add_costume("2w%d" % (i + 1), art))

    core_cos = [add_costume("%s%d" % (l, i + 1), D.core_frame(col, l == "c", i))
                for l, col in (("c", A.CY), ("m", A.MG)) for i in range(8)]

    ring_cos = [add_costume("%s%d" % (l, b + 1), D.ring_ellipse(col, sq))
                for l, col in (("c", A.CY), ("m", A.MG), ("w", A.WH)) for b, sq in enumerate(D.RING_SQUASH)]

    banner_cos = [add_costume("title", D.title_card3d()), add_costume("over", D.over_card3d())]
    banner_cos += [add_costume("wave%d" % n, A.wave_card(n)) for n in range(1, 31)]

    pad_cos = [add_costume("base", D.pad_base()), add_costume("knob", D.pad_knob()),
               add_costume("flipc", D.pad_flip(A.CY)), add_costume("flipm", D.pad_flip(A.MG)),
               add_costume("flipoff", D.pad_flip("#5a6280", "LOW"))]

    targets = [
        {"isStage": True, "name": "Stage",
         "variables": {vid: [n, 0] for n, vid in stage.vars.items()},
         "lists": {lid: [n, []] for n, lid in stage.lists.items()},
         "broadcasts": {bid: n for n, bid in stage.broadcasts.items()},
         "blocks": stage.blocks, "comments": {}, "currentCostume": 0,
         "costumes": [add_costume("arena", D.backdrop3d())],
         "sounds": [add_sound("music", A.snd_music()), add_sound("wave", A.snd_wave()),
                    add_sound("boom", A.snd_boom()), add_sound("clear", A.snd_clear())],
         "volume": 100, "layerOrder": 0, "tempo": 60, "videoTransparency": 50, "videoState": "on",
         "textToSpeechLanguage": None},
        sprite_json(fx, [add_costume("dot", A.blank())], [], 1),
        sprite_json(spacer, [add_costume("dot", A.blank())], [], 2),
        sprite_json(ringt, ring_cos, [], 3),
        sprite_json(drone, drone_cos, [], 4),
        sprite_json(core, core_cos, [add_sound("flipup", A.snd_flip(True)), add_sound("flipdown", A.snd_flip(False)),
                                     add_sound("denied", A.snd_denied())], 5),
        sprite_json(spark, trio(A.spark), [add_sound("pop", A.snd_pop()), add_sound("clutch", A.snd_clutch())], 6),
        sprite_json(popup, [add_costume("clutch", A.popup("CLUTCH! x2", A.YL)),
                            add_costume("clear", A.popup("WAVE CLEAR", A.GR))], [], 7),
        sprite_json(pad, pad_cos, [], 8),
        sprite_json(banner, banner_cos, [], 9, visible=True),
        sprite_json(digits, [add_costume("d" + c, A.digit(c)) for c in "0123456789x"], [], 10),
        sprite_json(flash, [add_costume("white", A.flash())], [], 11),
    ]
    proj = {"targets": targets, "monitors": [], "extensions": ["pen"],
            "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "polar-shift-builder"}}
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(proj, separators=(",", ":")))
        for name, data in files.items():
            z.writestr(name, data)
    nblocks = sum(len(t["blocks"]) for t in targets)
    print("wrote %s  (%d blocks, %d assets, %.0f KB)" % (OUT, nblocks, len(files), os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
