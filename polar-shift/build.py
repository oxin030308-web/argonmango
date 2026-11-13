"""Builds PolarShift.sb3 — a Scratch 3 game.  Run:  python3 build.py"""
import hashlib
import json
import os
import zipfile

import assets as A
from dsl import *  # noqa: F401,F403

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "PolarShift.sb3")

files = {}  # md5ext -> bytes


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


# =====================================================================  globals
GLOBALS = ["state", "score", "best", "mult", "combo", "wave", "energy", "px", "py", "ppol", "pinv",
           "enemies", "flipT", "fx", "fy", "si", "sn", "sd", "ov"]
LISTS = ["tx", "ty", "lx", "ly", "sqx", "sqy", "sqc", "sqs", "rqx", "rqy", "rqc", "rqs", "pqx", "pqy", "pqc"]

stage = Target("Stage", is_stage=True)
for g in GLOBALS:
    stage.vars[g] = "g_" + g
for l in LISTS:
    stage.lists[l] = "l_" + l

ACTION = lambda: or_(key("space"), mousedown())  # noqa: E731


def notplay():
    return not_(eq(V("state"), "play"))


def clear_lists():
    return [delall(l) for l in LISTS]


# =====================================================================  STAGE
stage.script(whenflag(),
             setv("state", "title"), setv("score", 0), setv("mult", 1), setv("ppol", 1), setv("ov", 0),
             *clear_lists(), backdrop("grid"), bcast("title"))
stage.script(whenflag(), setvol(45), forever(playwait("music")))
stage.script(whenrecv("title"),
             wait(0.3), waituntil(not_(ACTION())), waituntil(ACTION()),
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
                   if_(gt(V("sn"), 28), setv("sn", 28)),
                   setv("sd", sub(1.15, mul(V("wave"), 0.07))),
                   if_(lt(V("sd"), 0.3), setv("sd", 0.3)),
                   setv("si", 0),
                   until(or_(not_(lt(V("si"), V("sn"))), notplay()),
                         clone("Drone"), chv("si", 1), wait(V("sd"))),
                   waituntil(or_(lt(V("enemies"), 1), notplay())),
                   if_(eq(V("state"), "play"),
                       chv("score", mul(V("wave"), 100)),
                       addl("pqx", 0), addl("pqy", 40), addl("pqc", "clear"), play("clear"),
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
             wait(1.5), waituntil(not_(ACTION())), waituntil(ACTION()),
             if_(eq(V("state"), "over"), bcast("start")))

# =====================================================================  CORE (player)
core = Target("Core", ["vx", "vy", "sp"], glob=stage)
core.script(whenflag(), hide(), gotoxy(0, 0), rotstyle("don't rotate"))
core.script(whenrecv("title"), hide())


def bounce(axis, lim):
    pos, setp, v = (xpos, setx, "vx") if axis == "x" else (ypos, sety, "vy")
    return [if_(gt(pos(), lim), setp(lim), setv(v, mul(V(v), -0.6))),
            if_(lt(pos(), -lim), setp(-lim), setv(v, mul(V(v), -0.6)))]


core.script(whenrecv("go"),
            gotoxy(0, 0), setv("vx", 0), setv("vy", 0), setv("ppol", 1), setv("energy", 100),
            setv("pinv", 45), costume("cyan"), setsize(100), cleareff(), show(), front(), setv("sp", 1),
            until(notplay(),
                  if_(or_(key("right arrow"), key("d")), chv("vx", 0.75)),
                  if_(or_(key("left arrow"), key("a")), chv("vx", -0.75)),
                  if_(or_(key("up arrow"), key("w")), chv("vy", 0.75)),
                  if_(or_(key("down arrow"), key("s")), chv("vy", -0.75)),
                  chv("vx", V("fx")), chv("vy", V("fy")), setv("fx", 0), setv("fy", 0),
                  setv("vx", mul(V("vx"), 0.88)), setv("vy", mul(V("vy"), 0.88)),
                  chx(V("vx")), chy(V("vy")),
                  *bounce("x", 226), *bounce("y", 166),
                  setv("px", xpos()), setv("py", ypos()),
                  if_(lt(V("energy"), 100), chv("energy", 0.4),
                      if_(gt(V("energy"), 100), setv("energy", 100))),
                  ifelse(ACTION(),
                         [if_(eq(V("sp"), 0),
                              setv("sp", 1),
                              ifelse(lt(V("energy"), 30), [play("denied")], [call("flip")]))],
                         [setv("sp", 0)]),
                  addl("tx", xpos()), addl("ty", ypos()),
                  if_(gt(llen("tx"), 10), dell("tx", 1), dell("ty", 1)),
                  ifelse(gt(V("pinv"), 0),
                         [chv("pinv", -1),
                          ifelse(lt(mod(V("pinv"), 6), 3), [seteff("ghost", 65)], [seteff("ghost", 0)])],
                         [seteff("ghost", 0)]),
                  setsize(add(100, mul(5, mathop("sin", mul(timer(), 500)))))))
core.script(procdef("flip"),
            setv("ppol", sub(0, V("ppol"))), chv("energy", -30), setv("flipT", 0),
            ifelse(eq(V("ppol"), 1), [costume("cyan"), play("flipup")], [costume("magenta"), play("flipdown")]),
            addl("rqx", xpos()), addl("rqy", ypos()), addl("rqc", V("ppol")), addl("rqs", 260))
core.script(whenrecv("die"),
            addl("sqx", V("px")), addl("sqy", V("py")), addl("sqc", 2), addl("sqs", 2),
            addl("rqx", V("px")), addl("rqy", V("py")), addl("rqc", 2), addl("rqs", 420),
            hide())

# =====================================================================  DRONE (enemies)
drone = Target("Drone", ["vx", "vy", "pol", "kind", "d", "dx", "dy", "a", "age", "sw", "sp", "mx",
                         "acc", "h", "t", "rr", "pts"], glob=stage)
drone.script(whenflag(), hide())
drone.script(procdef("skin"),
             ifelse(eq(V("pol"), 1), [costume(join(V("kind"), "c"))], [costume(join(V("kind"), "m"))]))
drone.script(procdef("place"),
             setv("dx", 0), setv("dy", 0),
             until(gt(sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy")))), 170),
                   ifelse(eq(rnd(1, 2), 1),
                          [setx(rnd(-225, 225)), ifelse(eq(rnd(1, 2), 1), [sety(165)], [sety(-165)])],
                          [sety(rnd(-165, 165)), ifelse(eq(rnd(1, 2), 1), [setx(225)], [setx(-225)])]),
                   setv("dx", sub(V("px"), xpos())), setv("dy", sub(V("py"), ypos()))))
drone.script(whenclone(),
             chv("enemies", 1),
             setv("kind", 1), setv("pts", 10), setv("rr", 26),
             if_(and_(gt(V("wave"), 2), eq(rnd(1, 4), 1)), setv("kind", 2), setv("pts", 20), setv("rr", 27)),
             if_(and_(gt(V("wave"), 3), eq(rnd(1, 4), 1)), setv("kind", 3), setv("pts", 25), setv("rr", 22)),
             ifelse(eq(rnd(1, 2), 1), [setv("pol", 1)], [setv("pol", -1)]),
             ifelse(eq(rnd(1, 2), 1), [setv("sw", 1)], [setv("sw", -1)]),
             call("skin"), call("place"),
             setv("vx", 0), setv("vy", 0), setv("age", 0),
             setv("acc", add(0.2, mul(V("wave"), 0.015))),
             setv("mx", add(3, mul(V("wave"), 0.12))),
             if_(gt(V("mx"), 5.5), setv("mx", 5.5)),
             setsize(100),
             if_(eq(V("kind"), 2), setsize(110)),
             if_(eq(V("kind"), 3), setsize(85), setv("acc", mul(V("acc"), 1.7)), setv("mx", add(V("mx"), 1.6))),
             addl("rqx", xpos()), addl("rqy", ypos()), addl("rqc", V("pol")), addl("rqs", 90),
             pointdir(rnd(0, 360)), seteff("ghost", 100), show(),
             repeat(12, cheff("ghost", -8.4), turn(15)),
             seteff("ghost", 0),
             until(notplay(), call("step")),
             wait(rnd(0.0, 0.7)),
             addl("sqx", xpos()), addl("sqy", ypos()), addl("sqc", V("pol")), addl("sqs", 0),
             chv("enemies", -1), delclone())


def wall(axis, lim):
    pos, setp, v = (xpos, setx, "vx") if axis == "x" else (ypos, sety, "vy")
    return [if_(gt(pos(), lim), setp(lim), setv(v, sub(0, mathop("abs", V(v))))),
            if_(lt(pos(), -lim), setp(-lim), setv(v, mathop("abs", V(v))))]


drone.script(procdef("step"),
             setv("dx", sub(V("px"), xpos())), setv("dy", sub(V("py"), ypos())),
             setv("d", add(sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy")))), 0.1)),
             # likes repel (inside 115px) and hover/orbit; opposites home straight in
             ifelse(eq(V("pol"), V("ppol")),
                    [ifelse(lt(V("d"), 115),
                            [setv("a", mul(div(sub(115, V("d")), 115), -0.5))],
                            [setv("a", 0.05)]),
                     chv("vx", sub(mul(V("a"), div(V("dx"), V("d"))), mul(mul(V("sw"), 0.07), div(V("dy"), V("d"))))),
                     chv("vy", add(mul(V("a"), div(V("dy"), V("d"))), mul(mul(V("sw"), 0.07), div(V("dx"), V("d")))))],
                    [setv("a", V("acc")),
                     chv("vx", mul(sub(mul(V("mx"), div(V("dx"), V("d"))), V("vx")), mul(V("acc"), 0.3))),
                     chv("vy", mul(sub(mul(V("mx"), div(V("dy"), V("d"))), V("vy")), mul(V("acc"), 0.3)))]),
             # equal & opposite tug on the player
             if_(lt(V("d"), 200),
                 chv("fx", mul(mul(V("a"), div(V("dx"), V("d"))), -0.12)),
                 chv("fy", mul(mul(V("a"), div(V("dy"), V("d"))), -0.12))),
             setv("vx", mul(V("vx"), 0.975)), setv("vy", mul(V("vy"), 0.975)),
             setv("sp", sqrt(add(mul(V("vx"), V("vx")), mul(V("vy"), V("vy"))))),
             if_(gt(V("sp"), V("mx")),
                 setv("vx", mul(V("vx"), div(V("mx"), V("sp")))),
                 setv("vy", mul(V("vy"), div(V("mx"), V("sp"))))),
             chx(V("vx")), chy(V("vy")),
             *wall("x", 230), *wall("y", 170),
             ifelse(eq(V("kind"), 3),
                    [setv("h", mathop("atan", div(V("vx"), add(V("vy"), 0.0001)))),
                     if_(lt(V("vy"), 0), chv("h", 180)),
                     pointdir(V("h"))],
                    [turn(mul(V("pol"), 5))]),
             chv("age", 1),
             # prisms flicker then swap polarity
             if_(eq(V("kind"), 2),
                 setv("t", mod(V("age"), 150)),
                 if_(gt(V("t"), 120),
                     ifelse(lt(mod(V("age"), 6), 3), [costume("2w")], [call("skin")])),
                 if_(eq(V("t"), 0),
                     setv("pol", sub(0, V("pol"))), call("skin"),
                     addl("rqx", xpos()), addl("rqy", ypos()), addl("rqc", V("pol")), addl("rqs", 110))),
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
                     addl("pqx", xpos()), addl("pqy", add(ypos(), 22)), addl("pqc", "clutch"),
                     chv("energy", 10), addl("sqs", 3)],
                    [chv("score", mul(V("pts"), V("mult"))), addl("sqs", 1)]),
             addl("sqx", xpos()), addl("sqy", ypos()), addl("sqc", V("pol")),
             chv("mult", 1), if_(gt(V("mult"), 50), setv("mult", 50)), setv("combo", 75),
             chv("energy", 18), if_(gt(V("energy"), 100), setv("energy", 100)),
             addl("rqx", xpos()), addl("rqy", ypos()), addl("rqc", V("pol")), addl("rqs", 150),
             chv("enemies", -1), delclone())

# =====================================================================  SPARK (particles + hit sounds)
spark = Target("Spark", ["v", "k", "s", "big", "n2", "p"], glob=stage)


def color_costume(var):
    return ifelse(eq(V(var), 1), [costume("c")],
                  [ifelse(eq(V(var), -1), [costume("m")], [costume("w")])])


spark.script(whenflag(), hide(), forever(if_(gt(llen("sqx"), 0), call("burst"))))
spark.script(procdef("burst"),
             until(eq(llen("sqx"), 0),
                   gotoxy(item("sqx", 1), item("sqy", 1)),
                   setv("k", item("sqc", 1)), setv("s", item("sqs", 1)),
                   color_costume("k"),
                   if_(or_(eq(V("s"), 1), eq(V("s"), 3)),
                       setv("p", mul(sub(V("mult"), 1), 14)), if_(gt(V("p"), 280), setv("p", 280)),
                       sndeff("PITCH", V("p")), play("pop")),
                   if_(eq(V("s"), 3), play("clutch")),
                   setv("big", V("s")),
                   setv("n2", 9), if_(eq(V("s"), 2), setv("n2", 34)), if_(eq(V("s"), 0), setv("n2", 6)),
                   repeat(V("n2"), pointdir(rnd(0, 360)), clone()),
                   dell("sqx", 1), dell("sqy", 1), dell("sqc", 1), dell("sqs", 1)))
spark.script(whenclone(),
             setv("v", rnd(3.0, 8.0)), if_(eq(V("big"), 2), setv("v", rnd(4.0, 15.0))),
             setsize(rnd(60, 130)), show(),
             repeat(14, move(V("v")), setv("v", mul(V("v"), 0.86)), cheff("ghost", 7), chsize(-5)),
             delclone())

# =====================================================================  RING (shockwaves)
ringt = Target("Ring", ["g", "k"], glob=stage)
ringt.script(whenflag(), hide(), forever(if_(gt(llen("rqx"), 0), call("spawn"))))
ringt.script(procdef("spawn"),
             until(eq(llen("rqx"), 0),
                   gotoxy(item("rqx", 1), item("rqy", 1)),
                   setv("k", item("rqc", 1)), color_costume("k"),
                   setv("g", div(item("rqs", 1), 12)), setsize(8), clone(),
                   dell("rqx", 1), dell("rqy", 1), dell("rqc", 1), dell("rqs", 1)))
ringt.script(whenclone(), seteff("ghost", 0), show(),
             repeat(12, chsize(V("g")), cheff("ghost", 8.5)), delclone())

# =====================================================================  POPUP (floating text)
popup = Target("Popup", [], glob=stage)
popup.script(whenflag(), hide(), forever(if_(gt(llen("pqx"), 0), call("spawn"))))
popup.script(procdef("spawn"),
             until(eq(llen("pqx"), 0),
                   gotoxy(item("pqx", 1), item("pqy", 1)), costume(item("pqc", 1)), clone(),
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

# =====================================================================  FX (pen renderer)
fx = Target("FX", ["i", "ex", "ey", "mx", "my"], glob=stage)
fx.script(whenflag(), hide(), pen_clear())
fx.script(whenrecv("title"), pen_clear())
fx.script(whenrecv("go"), until(notplay(), call("render")), wait(0.15), pen_clear())


def by_pol(var, same):
    a, b = (A.CY, A.MG) if same else (A.MG, A.CY)
    return ifelse(eq(V(var), 1), [pen_color(a)], [pen_color(b)])


def seg(x0, y0, x1, y1):
    return [pen_up(), gotoxy(x0, y0), pen_down(), gotoxy(x1, y1), pen_up()]


fx.script(procdef("render"),
          pen_clear(),
          # crackling magnetic tethers toward incoming killers
          by_pol("ppol", False), setv("i", 1),
          repeat(llen("lx"),
                 setv("ex", item("lx", V("i"))), setv("ey", item("ly", V("i"))),
                 setv("mx", add(div(add(V("px"), V("ex")), 2), rnd(-9.0, 9.0))),
                 setv("my", add(div(add(V("py"), V("ey")), 2), rnd(-9.0, 9.0))),
                 pen_param("transparency", 70), pen_size(6),
                 pen_up(), gotoxy(V("px"), V("py")), pen_down(), gotoxy(V("mx"), V("my")),
                 gotoxy(V("ex"), V("ey")), pen_up(),
                 pen_param("transparency", 10), pen_size(1.5),
                 gotoxy(V("px"), V("py")), pen_down(), gotoxy(V("mx"), V("my")),
                 gotoxy(V("ex"), V("ey")), pen_up(),
                 chv("i", 1)),
          delall("lx"), delall("ly"),
          # comet trail
          by_pol("ppol", True), setv("i", 1), pen_up(),
          repeat(llen("tx"),
                 pen_size(mul(V("i"), 2.6)),
                 pen_param("transparency", add(35, mul(sub(llen("tx"), V("i")), 6))),
                 gotoxy(item("tx", V("i")), item("ty", V("i"))), pen_down(), chv("i", 1)),
          pen_up(),
          # energy bar (3 notches = 3 flips)
          pen_param("transparency", 0), pen_size(9), pen_color("#1b2238"), *seg(-100, -166, 100, -166),
          ifelse(lt(V("energy"), 30), [pen_color("#ff4d5e")], [by_pol("ppol", True)]),
          *seg(-100, -166, add(-100, mul(V("energy"), 2)), -166),
          pen_color("#070912"), pen_size(2),
          *seg(-40, -171, -40, -161), *seg(20, -171, 20, -161), *seg(80, -171, 80, -161),
          # combo timer
          if_(gt(V("mult"), 1),
              pen_color(A.YL), pen_size(3), *seg(sub(226, mul(V("combo"), 1.2)), 145, 226, 145)))

# =====================================================================  FLASH
flash = Target("Flash", [], glob=stage)
flash.script(whenflag(), hide())
flash.script(whenrecv("die"), gotoxy(0, 0), seteff("ghost", 15), show(), front(),
             repeat(17, cheff("ghost", 5)), hide())

# =====================================================================  assemble
def sprite_json(t, costumes, sounds, layer, visible=False, x=0, y=0, size=100, extra_vars=None):
    return {"isStage": False, "name": t.name,
            "variables": {vid: [n, 0] for n, vid in t.vars.items()},
            "lists": {}, "broadcasts": {}, "blocks": t.blocks, "comments": {},
            "currentCostume": 0, "costumes": costumes, "sounds": sounds, "volume": 100,
            "layerOrder": layer, "visible": visible, "x": x, "y": y, "size": size, "direction": 90,
            "draggable": False, "rotationStyle": "all around"}


def main():
    trio = lambda f: [add_costume(n, f(c)) for n, c in (("c", A.CY), ("m", A.MG), ("w", A.WH))]  # noqa: E731

    drone_cos = []
    for k in (1, 2, 3):
        drone_cos.append(add_costume("%dc" % k, A.drone(k, A.CY, True)))
        drone_cos.append(add_costume("%dm" % k, A.drone(k, A.MG, False)))
    drone_cos.append(add_costume("2w", A.drone(2, A.WH, True, white=True)))

    banner_cos = [add_costume("title", A.title_card()), add_costume("over", A.over_card())]
    banner_cos += [add_costume("wave%d" % n, A.wave_card(n)) for n in range(1, 31)]

    digit_cos = [add_costume("d" + c, A.digit(c)) for c in "0123456789x"]

    targets = [
        {"isStage": True, "name": "Stage",
         "variables": {vid: [n, 0] for n, vid in stage.vars.items()},
         "lists": {lid: [n, []] for n, lid in stage.lists.items()},
         "broadcasts": {bid: n for n, bid in stage.broadcasts.items()},
         "blocks": stage.blocks, "comments": {}, "currentCostume": 0,
         "costumes": [add_costume("grid", A.backdrop())],
         "sounds": [add_sound("music", A.snd_music()), add_sound("wave", A.snd_wave()),
                    add_sound("boom", A.snd_boom()), add_sound("clear", A.snd_clear())],
         "volume": 100, "layerOrder": 0, "tempo": 60, "videoTransparency": 50, "videoState": "on",
         "textToSpeechLanguage": None},
        sprite_json(fx, [add_costume("dot", A.blank())], [], 1),
        sprite_json(ringt, trio(A.ring), [], 2),
        sprite_json(drone, drone_cos, [], 3),
        sprite_json(spark, trio(A.spark), [add_sound("pop", A.snd_pop()), add_sound("clutch", A.snd_clutch())], 4),
        sprite_json(core, [add_costume("cyan", A.core(A.CY, "+")), add_costume("magenta", A.core(A.MG, "-"))],
                    [add_sound("flipup", A.snd_flip(True)), add_sound("flipdown", A.snd_flip(False)),
                     add_sound("denied", A.snd_denied())], 5),
        sprite_json(popup, [add_costume("clutch", A.popup("CLUTCH! x2", A.YL)),
                            add_costume("clear", A.popup("WAVE CLEAR", A.GR))], [], 6),
        sprite_json(banner, banner_cos, [], 7, visible=True),
        sprite_json(digits, digit_cos, [], 8),
        sprite_json(flash, [add_costume("white", A.flash())], [], 9),
    ]
    # stage variable "best" survives; everything else starts at 0
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
