"""Tiny DSL that compiles Python-described scripts into Scratch 3 project.json blocks."""
import itertools

_ids = itertools.count()


def nid():
    return "b%d" % next(_ids)


# ---------------------------------------------------------------- core types
class Blk:
    def __init__(self, op, inputs=None, fields=None, mutation=None):
        self.op = op
        self.inputs = inputs or {}
        self.fields = fields or {}
        self.mutation = mutation


class Var:
    def __init__(self, name):
        self.name = name


V = Var
PRIM = {"num": 4, "pos": 5, "whole": 6, "int": 7, "angle": 8, "color": 9, "text": 10}


def lit(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v.is_integer() and False:
        return str(int(v))
    return str(v)


class Target:
    """Collects blocks for one sprite / the stage."""

    def __init__(self, name, local_vars=(), is_stage=False, glob=None):
        self.name = name
        self.is_stage = is_stage
        self.glob = glob  # stage Target holding globals (None for stage itself)
        self.vars = {}
        self.lists = {}
        self.broadcasts = {}
        for v in local_vars:
            self.vars[v] = "v_%s_%s" % (name, v)
        self.blocks = {}
        self.script_y = 0
        self.default_costume = None
        self.default_sound = None

    # --- lookups
    def var_id(self, n):
        if n in self.vars:
            return self.vars[n]
        if self.glob and n in self.glob.vars:
            return self.glob.vars[n]
        raise KeyError("unknown variable %s in %s" % (n, self.name))

    def list_id(self, n):
        if n in self.lists:
            return self.lists[n]
        if self.glob and n in self.glob.lists:
            return self.glob.lists[n]
        raise KeyError("unknown list %s in %s" % (n, self.name))

    def bcast_id(self, n):
        st = self.glob or self
        if n not in st.broadcasts:
            st.broadcasts[n] = "m_" + n
        return st.broadcasts[n]

    # --- compile
    def emit(self, blk, parent, top=False):
        bid = nid()
        d = {"opcode": blk.op, "next": None, "parent": parent, "inputs": {}, "fields": {},
             "shadow": False, "topLevel": top}
        if top:
            d["x"] = 0
            d["y"] = self.script_y
            self.script_y += 900
        if blk.mutation is not None:
            d["mutation"] = blk.mutation
        self.blocks[bid] = d
        for fname, fval in blk.fields.items():
            if isinstance(fval, tuple):
                kind, n = fval
                if kind == "var":
                    d["fields"][fname] = [n, self.var_id(n)]
                elif kind == "list":
                    d["fields"][fname] = [n, self.list_id(n)]
                elif kind == "bcast":
                    d["fields"][fname] = [n, self.bcast_id(n)]
            else:
                d["fields"][fname] = [fval, None]
        for iname, (kind, val) in blk.inputs.items():
            inp = self.input(kind, val, bid)
            if inp is not None:
                d["inputs"][iname] = inp
        return bid

    def input(self, kind, val, parent):
        if kind == "bool":
            if val is None:
                return None
            return [2, self.emit(val, parent)]
        if kind == "stack":
            if not val:
                return None
            return [2, self.chain(val, parent)]
        if kind == "bcast":
            return [1, [11, val, self.bcast_id(val)]]
        if kind == "custom":  # procedure prototype
            return [1, val]
        if kind == "menu":
            mop, mfield, mval, default = val
            sid = nid()
            dv = mval if isinstance(mval, str) else default
            self.blocks[sid] = {"opcode": mop, "next": None, "parent": parent, "inputs": {},
                                "fields": {mfield: [dv, None]}, "shadow": True, "topLevel": False}
            if isinstance(mval, str):
                return [1, sid]
            if isinstance(mval, Var):
                return [3, [12, mval.name, self.var_id(mval.name)], sid]
            return [3, self.emit(mval, parent), sid]
        code = PRIM[kind]
        if isinstance(val, Var):
            return [3, [12, val.name, self.var_id(val.name)], [code, "" if kind != "color" else "#ffffff"]]
        if isinstance(val, Blk):
            return [3, self.emit(val, parent), [code, "" if kind != "color" else "#ffffff"]]
        return [1, [code, lit(val)]]

    def chain(self, stmts, parent):
        first = None
        prev = None
        for s in stmts:
            if s is None:
                continue
            sid = self.emit(s, prev if prev else parent)
            if prev is None:
                first = sid
            else:
                self.blocks[prev]["next"] = sid
            prev = sid
        return first

    def script(self, hat, *stmts):
        if hat.op == "procedures_definition":
            return self._procdef(hat, stmts)
        hid = self.emit(hat, None, top=True)
        body = [s for s in stmts if s is not None]
        if body:
            first = self.chain(body, hid)
            self.blocks[hid]["next"] = first

    def _procdef(self, hat, stmts):
        name, warp = hat.mutation
        hid = nid()
        pid = nid()
        self.blocks[hid] = {"opcode": "procedures_definition", "next": None, "parent": None,
                            "inputs": {"custom_block": [1, pid]}, "fields": {}, "shadow": False,
                            "topLevel": True, "x": 600, "y": self.script_y}
        self.script_y += 900
        self.blocks[pid] = {"opcode": "procedures_prototype", "next": None, "parent": hid,
                            "inputs": {}, "fields": {}, "shadow": True, "topLevel": False,
                            "mutation": {"tagName": "mutation", "children": [], "proccode": name,
                                         "argumentids": "[]", "argumentnames": "[]",
                                         "argumentdefaults": "[]", "warp": "true" if warp else "false"}}
        body = [s for s in stmts if s is not None]
        if body:
            self.blocks[hid]["next"] = self.chain(body, hid)


# ---------------------------------------------------------------- hats
def whenflag(): return Blk("event_whenflagclicked")
def whenrecv(m): return Blk("event_whenbroadcastreceived", fields={"BROADCAST_OPTION": ("bcast", m)})
def whenclone(): return Blk("control_start_as_clone")
def procdef(name, warp=True): return Blk("procedures_definition", mutation=(name, warp))


def call(name, warp=True):
    return Blk("procedures_call", mutation={"tagName": "mutation", "children": [], "proccode": name,
                                            "argumentids": "[]", "warp": "true" if warp else "false"})


# ---------------------------------------------------------------- operators
def _bin(op, a, b, kind="num", n1="NUM1", n2="NUM2"):
    return Blk(op, inputs={n1: (kind, a), n2: (kind, b)})


def add(a, b): return _bin("operator_add", a, b)
def sub(a, b): return _bin("operator_subtract", a, b)
def mul(a, b): return _bin("operator_multiply", a, b)
def div(a, b): return _bin("operator_divide", a, b)
def mod(a, b): return _bin("operator_mod", a, b)
def rnd(a, b): return Blk("operator_random", inputs={"FROM": ("num", a), "TO": ("num", b)})
def gt(a, b): return _bin("operator_gt", a, b, "text", "OPERAND1", "OPERAND2")
def lt(a, b): return _bin("operator_lt", a, b, "text", "OPERAND1", "OPERAND2")
def eq(a, b): return _bin("operator_equals", a, b, "text", "OPERAND1", "OPERAND2")
def and_(a, b): return Blk("operator_and", inputs={"OPERAND1": ("bool", a), "OPERAND2": ("bool", b)})
def or_(a, b): return Blk("operator_or", inputs={"OPERAND1": ("bool", a), "OPERAND2": ("bool", b)})
def not_(a): return Blk("operator_not", inputs={"OPERAND": ("bool", a)})
def join(a, b): return _bin("operator_join", a, b, "text", "STRING1", "STRING2")
def letter(i, s): return Blk("operator_letter_of", inputs={"LETTER": ("whole", i), "STRING": ("text", s)})
def length(s): return Blk("operator_length", inputs={"STRING": ("text", s)})
def mathop(op, x): return Blk("operator_mathop", inputs={"NUM": ("num", x)}, fields={"OPERATOR": op})
def sqrt(x): return mathop("sqrt", x)


def any_(*cs):
    r = cs[0]
    for c in cs[1:]:
        r = or_(r, c)
    return r


# ---------------------------------------------------------------- data
def setv(n, v): return Blk("data_setvariableto", inputs={"VALUE": ("text", v)}, fields={"VARIABLE": ("var", n)})
def chv(n, v): return Blk("data_changevariableby", inputs={"VALUE": ("num", v)}, fields={"VARIABLE": ("var", n)})
def addl(l, v): return Blk("data_addtolist", inputs={"ITEM": ("text", v)}, fields={"LIST": ("list", l)})
def dell(l, i): return Blk("data_deleteoflist", inputs={"INDEX": ("int", i)}, fields={"LIST": ("list", l)})
def delall(l): return Blk("data_deletealloflist", fields={"LIST": ("list", l)})
def item(l, i): return Blk("data_itemoflist", inputs={"INDEX": ("int", i)}, fields={"LIST": ("list", l)})
def llen(l): return Blk("data_lengthoflist", fields={"LIST": ("list", l)})


# ---------------------------------------------------------------- motion
def gotoxy(x, y): return Blk("motion_gotoxy", inputs={"X": ("num", x), "Y": ("num", y)})
def setx(x): return Blk("motion_setx", inputs={"X": ("num", x)})
def sety(y): return Blk("motion_sety", inputs={"Y": ("num", y)})
def chx(d): return Blk("motion_changexby", inputs={"DX": ("num", d)})
def chy(d): return Blk("motion_changeyby", inputs={"DY": ("num", d)})
def pointdir(d): return Blk("motion_pointindirection", inputs={"DIRECTION": ("angle", d)})
def turn(d): return Blk("motion_turnright", inputs={"DEGREES": ("num", d)})
def move(s): return Blk("motion_movesteps", inputs={"STEPS": ("num", s)})
def rotstyle(s): return Blk("motion_setrotationstyle", fields={"STYLE": s})
def xpos(): return Blk("motion_xposition")
def ypos(): return Blk("motion_yposition")


# ---------------------------------------------------------------- looks
def costume(c, default="x"):
    return Blk("looks_switchcostumeto", inputs={"COSTUME": ("menu", ("looks_costume", "COSTUME", c, default))})


def backdrop(b):
    return Blk("looks_switchbackdropto",
               inputs={"BACKDROP": ("menu", ("looks_backdrops", "BACKDROP", b, b))})


def show(): return Blk("looks_show")
def hide(): return Blk("looks_hide")
def setsize(v): return Blk("looks_setsizeto", inputs={"SIZE": ("num", v)})
def chsize(v): return Blk("looks_changesizeby", inputs={"CHANGE": ("num", v)})
def seteff(e, v): return Blk("looks_seteffectto", inputs={"VALUE": ("num", v)}, fields={"EFFECT": e.upper()})
def cheff(e, v): return Blk("looks_changeeffectby", inputs={"CHANGE": ("num", v)}, fields={"EFFECT": e.upper()})
def cleareff(): return Blk("looks_cleargraphiceffects")
def front(): return Blk("looks_gotofrontback", fields={"FRONT_BACK": "front"})


# ---------------------------------------------------------------- control
def wait(s): return Blk("control_wait", inputs={"DURATION": ("pos", s)})
def waituntil(c): return Blk("control_wait_until", inputs={"CONDITION": ("bool", c)})
def forever(*b): return Blk("control_forever", inputs={"SUBSTACK": ("stack", list(b))})
def repeat(n, *b): return Blk("control_repeat", inputs={"TIMES": ("whole", n), "SUBSTACK": ("stack", list(b))})
def until(c, *b): return Blk("control_repeat_until", inputs={"CONDITION": ("bool", c), "SUBSTACK": ("stack", list(b))})
def if_(c, *b): return Blk("control_if", inputs={"CONDITION": ("bool", c), "SUBSTACK": ("stack", list(b))})


def ifelse(c, a, b):
    return Blk("control_if_else", inputs={"CONDITION": ("bool", c), "SUBSTACK": ("stack", list(a)),
                                          "SUBSTACK2": ("stack", list(b))})


def stop(opt):
    return Blk("control_stop", fields={"STOP_OPTION": opt},
               mutation={"tagName": "mutation", "children": [],
                         "hasnext": "true" if opt == "other scripts in sprite" else "false"})


def clone(t="_myself_"):
    return Blk("control_create_clone_of",
               inputs={"CLONE_OPTION": ("menu", ("control_create_clone_of_menu", "CLONE_OPTION", t, t))})


def delclone(): return Blk("control_delete_this_clone")
def bcast(m): return Blk("event_broadcast", inputs={"BROADCAST_INPUT": ("bcast", m)})


# ---------------------------------------------------------------- sensing
def key(k):
    return Blk("sensing_keypressed", inputs={"KEY_OPTION": ("menu", ("sensing_keyoptions", "KEY_OPTION", k, k))})


def mousedown(): return Blk("sensing_mousedown")
def timer(): return Blk("sensing_timer")


# ---------------------------------------------------------------- sound
def play(s): return Blk("sound_play", inputs={"SOUND_MENU": ("menu", ("sound_sounds_menu", "SOUND_MENU", s, s))})
def playwait(s): return Blk("sound_playuntildone", inputs={"SOUND_MENU": ("menu", ("sound_sounds_menu", "SOUND_MENU", s, s))})
def sndeff(e, v): return Blk("sound_seteffectto", inputs={"VALUE": ("num", v)}, fields={"EFFECT": e.upper()})
def setvol(v): return Blk("sound_setvolumeto", inputs={"VOLUME": ("num", v)})


# ---------------------------------------------------------------- pen
def pen_clear(): return Blk("pen_clear")
def pen_down(): return Blk("pen_penDown")
def pen_up(): return Blk("pen_penUp")
def pen_color(c): return Blk("pen_setPenColorToColor", inputs={"COLOR": ("color", c)})
def pen_size(v): return Blk("pen_setPenSizeTo", inputs={"SIZE": ("num", v)})


def pen_param(p, v):
    return Blk("pen_setPenColorParamTo",
               inputs={"COLOR_PARAM": ("menu", ("pen_menu_colorParam", "colorParam", p, p)),
                       "VALUE": ("num", v)})


# ---------------------------------------------------------------- added for 3D
def back(): return Blk("looks_gotofrontback", fields={"FRONT_BACK": "back"})
def fwd(n): return Blk("looks_goforwardbackwardlayers", inputs={"NUM": ("int", n)}, fields={"FORWARD_BACKWARD": "forward"})
def round_(x): return Blk("operator_round", inputs={"NUM": ("num", x)})
def mousex(): return Blk("sensing_mousex")
def mousey(): return Blk("sensing_mousey")
