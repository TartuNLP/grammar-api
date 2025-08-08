# -*- coding: utf-8 -*-
from typing import List
import re
from collections import defaultdict
import difflib

from estnltk import Text

try:
    from Levenshtein import distance as _lev_distance, opcodes as _lev_opcodes  # type: ignore
    def ed_distance(a: str, b: str) -> int:
        return _lev_distance(a, b)
    def token_opcodes(a_tokens: List[str], b_tokens: List[str]):
        # The C ext expects sequences; emulate signature
        # We'll adapt by using a tiny wrapper that mimics difflib opcodes on tokens
        # But if available, use it directly on strings joined with spaces
        # However, the raw script uses Levenshtein.opcodes on Text.words.text (list of tokens)
        return _lev_opcodes(a_tokens, b_tokens)
except Exception:
    def ed_distance(a: str, b: str) -> int:
        # Pure Python Levenshtein distance (DP)
        if a == b:
            return 0
        if len(a) == 0:
            return len(b)
        if len(b) == 0:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, start=1):
            cur = [i]
            for j, cb in enumerate(b, start=1):
                ins = cur[j-1] + 1
                delete = prev[j] + 1
                sub = prev[j-1] + (0 if ca == cb else 1)
                cur.append(min(ins, delete, sub))
            prev = cur
        return prev[-1]
    def token_opcodes(a_tokens: List[str], b_tokens: List[str]):
        sm = difflib.SequenceMatcher(a=a_tokens, b=b_tokens)
        return sm.get_opcodes()

# Map raw error tags
veadloetavaks = {
    'R:LEX': 'sõnavalik',
    'R:NOM:FORM': 'käändevorm',
    'M:PUNCT': 'puuduv kirjavahemärk',
    'R:VERB:FORM': 'tegusõna vorm',
    'U:LEX': 'liigne sõna',
    'R:VERB:ROOT:FORM': 'tegusõna vorm',
    'R:PUNCT': 'vale kirjavahemärk',
    'R:WO': 'sõnajärg',
    'R:SPELL': 'õigekiri',
    'r:Sp': 'õigekiri',
    'M:LEX': 'puuduv sõna',
    'R:WS': 'kokku-lahkukirjutus',
    'U:PUNCT': 'liigne kirjavahemärk',
    'R:VERB:FORM:SPELL': 'tegusõna vorm ja õigekiri',
    'R:WS:NOM:FORM': 'kokku-lahkukirjutus ja käändevorm',
    'R:CASE': 'algustäht',
    'R:SPELL:CASE': 'õigekiri ja algustäht',
    'R:NOM:FORM:SPELL': 'käändevorm ja õigekiri',
    'R:NOM:ROOT:FORM': 'käändevorm',
    'R:LEX:VERB:FORM': 'sõnavalik ja tegusõna vorm',
    'R:WO:VERB:FORM': 'sõnajärg ja tegusõna vorm',
    'R:LEX:NOM:FORM': 'sõnavalik ja käändevorm',
    'R:LEX:SPELL': 'sõnavalik ja õigekiri',
    'R:LEX:WO': 'sõnavalik ja sõnajärg',
    'R:VERB:FORM:CASE': 'tegusõna vorm ja algustäht',
    'R:WO:NOM:FORM': 'sõnajärg ja käändevorm',
    'R:WS:NOM:FORM:CASE': 'kokku-lahkukirjutus, käändevorm ja algustäht',
    'R:WS:SPELL': 'kokku-lahkukirjutus ja õigekiri',
    'R:NOM:FORM:CASE': 'käändevorm ja algustäht',
    'R:LEX:WS': 'sõnavalik ja kokku-lahkukirjutus',
    'R:LEX:CASE': 'sõnavalik ja algustäht',
    'R:WS:NOM:FORM:SPELL': 'kokku-lahkukirjutus, käändevorm ja õigekiri',
    'R:WS:CASE': 'kokku-lahkukirjutus ja algustäht',
    'R:WS:NOM:ROOT:FORM': 'kokku-lahkukirjutus ja käändevorm',
    'R:WO-': 'sõnajärg',
    'R:WS:VERB:FORM': 'kokku-lahkukirjutus ja tegusõna vorm',
    'R:NOM:FORM:SPELL:CASE': 'käändevorm, õigekiri ja algustäht',
    'M:PUNCT:PREV': 'puuduv kirjavahemärk',
    '*': 'sõnavalik',
    'R:WS:VERB:ROOT:FORM': 'kokku-lahkukirjutus ja tegusõna vorm',
    'noop': 'kõik on õige',
    'R:WO:NOM: FORM': 'sõnajärg ja käändevorm',
    'R:WO:VERB: FORM': 'sõnajärg ja tegusõna vorm',
    'R:': 'asendus',
    'U:': 'liigne',
    'M:': 'puuduv'
}


def _sõnakraam(sõna: str) -> bool:
    for sümbol in sõna:
        if sümbol != "-" and not sümbol.isalnum():
            return False
    return True


def _veatyyp(liik: str, a, b) -> str:
    liigid = {'replace': "R:", 'delete': "U:", 'insert': "M:"}
    vealiik = liigid[liik]

    a_text = "".join(a.text)
    b_text = "".join(b.text)

    if len(a) == 0:
        vealiik = "M:"
    elif len(b) == 0:
        vealiik = "U:"

    if vealiik in ["M:", "U:"]:
        if _sõnakraam(a_text) and _sõnakraam(b_text):
            vealiik += "LEX"
        else:
            vealiik += "PUNCT"
        return vealiik

    if not _sõnakraam(a_text) and not _sõnakraam(b_text):
        return vealiik + "PUNCT"
    if a_text == b_text or a_text == "-".join(b.text) or "-".join(a.text) == b_text:
        return vealiik + "WS"
    if a_text.lower() == b_text.lower():
        return vealiik + "CASE"
    if sorted(a.text) == sorted(b.text):
        return vealiik + "WO"

    if len(a) > 1 or len(b) > 1:
        return vealiik

    try:
        if a.lemma[0][0] == b.lemma[0][0]:
            if a.partofspeech[0][0] == "V":
                return vealiik + "VERB:FORM"
            else:
                return vealiik + "NOM:FORM"
    except Exception:
        pass

    try:
        if ed_distance(a.text[0], b.text[0]) <= 2:
            return vealiik + "SPELL"
    except Exception:
        pass

    return vealiik + "LEX"


def _pane_paaridesse(seqa, seqb):
    allesa = seqa.copy()
    allesb = seqb.copy()
    valmis = []
    kvma = [i for (sona, i) in seqa if not _sõnakraam(sona)]
    kvmb = [i for (sona, i) in seqb if not _sõnakraam(sona)]
    if len(kvma) == len(kvmb):
        for j, i in enumerate(kvma):
            if abs(kvma[j] - kvmb[j]) < 2:
                valmis.append((seqa[j], seqb[j]))
                allesa.remove(seqa[kvma[j]])
                allesb.remove(seqb[kvmb[j]])
    if len(kvma) == 0:
        for i in kvmb:
            valmis.append(((None, i), seqb[i]))
            allesb.remove(seqb[i])
    elif len(kvmb) == 0:
        for i in kvma:
            valmis.append((seqa[i], (None, i)))
            allesa.remove(seqa[i])

    kaugused = []
    for a in allesa:
        for b in allesb:
            # normalized distance for sorting
            d = ed_distance(a[0], b[0])
            denom = max(len(a[0]), len(b[0])) or 1
            kaugused.append([(a[1], b[1]), d / denom])
    kaugused = sorted(kaugused, key=lambda x: x[1])

    while len(allesa) > 0 and len(allesb) > 0 and len(kaugused) > 0:
        parim = kaugused[0]
        valmis.append((seqa[parim[0][0]], seqb[parim[0][1]]))
        allesa.remove(seqa[parim[0][0]])
        allesb.remove(seqb[parim[0][1]])
        kaugused = [k for k in kaugused if k[0][0] != parim[0][0] and k[0][1] != parim[0][1]]

    if len(allesa) > 0:
        for i in list(allesa):
            valmis.append((i, (None, i[1])))
            allesa.remove(i)
    if len(allesb) > 0:
        for i in list(allesb):
            valmis.append(((None, i[1]), i))
            allesb.remove(i)

    valmis = sorted(valmis, key=lambda x: x[0][1])
    return valmis


def _jaga_vead(op, a_text, b_text):
    if op[0] != "replace":
        return [op]

    a_words = [(a, i) for i, a in enumerate(a_text)]
    b_words = [(b, i) for i, b in enumerate(b_text)]

    if len(a_words) == 1 or len(b_words) == 1:
        a = re.sub(" ", "", "".join([c.lower() for c in a_text]))
        b = re.sub(" ", "", "".join([c.lower() for c in b_text]))
        if a == b:
            return [op]
        tmp = []
        if len(a_words) == 1:
            kaugused = [(i, ed_distance(a_text[0], b_text[i])) for i in range(len(b_words))]
            kaugused = sorted(kaugused, key=lambda x: x[1])
            bi = kaugused[0][0]
            if bi > 0:
                for i in range(bi):
                    tmp.append(('insert', op[1], op[1], op[3] + i, op[3] + i + 1))
            tmp.append(('replace', op[1], op[2], op[3] + bi, op[3] + bi + 1))
            if op[3] + bi + 1 < op[4]:
                for i in range(op[3] + bi + 1, op[4]):
                    tmp.append(('insert', op[2], op[2], i, i + 1))
        if len(b_words) == 1:
            kaugused = [(i, ed_distance(b_text[0], a_text[i])) for i in range(len(a_words))]
            kaugused = sorted(kaugused, key=lambda x: x[1])
            ai = kaugused[0][0]
            if ai > 0:
                for i in range(ai):
                    tmp.append(('delete', op[1] + i, op[1] + 1 + 1, op[3], op[3]))
            tmp.append(('replace', op[1] + ai, op[1] + ai + 1, op[3], op[3] + 1))
            if op[1] + ai + 1 < op[2]:
                for i in range(op[1] + ai + 1, op[2]):
                    tmp.append(('insert', i, i + 1, op[4], op[4]))
        return tmp

    if sorted(a_text) == sorted(b_text):
        return [op]

    paarid = _pane_paaridesse(a_words, b_words)
    paaridops = []
    lastai = 0
    lastbi = 0
    algusa = op[1]
    algusb = op[3]
    for p in paarid:
        if p[0] and p[1]:
            ai = algusa + p[0][1]
            bi = algusb + p[1][1]
            lastai = ai + 1
            lastbi = bi + 1
            if p[0][0] == p[1][0]:
                paaridops.append(('equal', ai, lastai, bi, lastbi))
            else:
                paaridops.append(('replace', ai, lastai, bi, lastbi))
        elif p[0]:
            ai = algusa + p[0][1]
            lastai = ai + 1
            paaridops.append(('delete', ai, lastai, lastbi, lastbi))
        elif p[1]:
            bi = algusb + p[1][1]
            lastbi = bi + 1
            paaridops.append(('insert', lastai, lastai, bi, lastbi))
    return paaridops


def _sammud(a, b):
    ops = token_opcodes(a.text, b.text)
    ops_new = []
    tmp = None
    for op in ops:
        if op[0] == "equal":
            if tmp:
                ops_new.append(tuple(tmp))
            ops_new.append(op)
            tmp = None
        else:
            if tmp:
                if op[0] == "replace":
                    tmp[0] = "replace"
                tmp[2] = op[2]
                tmp[4] = op[4]
            else:
                tmp = list(op)
    if tmp:
        ops_new.append(tuple(tmp))
    ops = ops_new

    ops_new = []
    for op in ops:
        ops_new.extend(_jaga_vead(op, a.text[op[1]:op[2]], b.text[op[3]:op[4]]))

    tagastatav = []
    for op in ops_new:
        if op[0] == "equal":
            continue
        asendaja = ""
        if op[0] != "delete":
            asendaja = b[op[-2]:op[-1]].text
        asendatav = a[op[1]:op[2]].text
        tyyp = _veatyyp(op[0], a[op[1]:op[2]], b[op[-2]:op[-1]])
        tagastatav.append((op[1], op[2], tyyp, " ".join(asendatav), " ".join(asendaja)))
    return tagastatav


def build_differences(original: str, corrected: str) -> str:
    """Produce 'Erinevused:' block like in raw/sent2GEDinstruction using Levenshtein-based ops and mapping.
    Lines look like: '<vealiik>: #start #end orig -> corr' with human-readable vealiik.
    """
    a = Text(original).tag_layer().words
    b = Text(corrected).tag_layer().words
    s = _sammud(a, b)
    mapped = []
    for start, end, tag, orig, corr in s:
        label = veadloetavaks.get(tag, tag)
        mapped.append(f"{label}: #{start} #{end} {orig} -> {corr}")
    return "Erinevused:\n" + "\n".join(mapped)
