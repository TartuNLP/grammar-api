from estnltk import Text
import numpy as np


def lev(xs, ys):
    mem = np.full((len(xs) + 1, len(ys) + 1), -1)

    def _lev(s1, s2):
        i = len(s1)
        j = len(s2)
        if mem[i][j] != -1:
            return mem[i][j]
        if i == 0:
            mem[i][j] = j
            return mem[i][j]
        if j == 0:
            mem[i][j] = i
            return mem[i][j]
        else:
            cost = 1
            if s1[-1] == s2[-1]:
                cost = 0
            mem[i][j] = min(_lev(s1[:-1], s2) + 1, _lev(s1, s2[:-1]) + 1, _lev(s1[:-1], s2[:-1]) + cost)
            return mem[i][j]

    result = _lev(xs, ys)
    return (result)


def lause_kaugus(lause1, lause2):
    # Saa ette kaks stringikujul lauset
    # Tagasta nende omavaheline kaugus järgmise valemi järgi:
    # sorteeritud sõnade kaugus + tähestiku järgi sorteeritud lause tähtede kaugus
    # mõlemad lause pikkuse järgi normaliseeritud
    kaugus = -1
    l1 = sorted(lause1.split())
    l2 = sorted(lause2.split())
    norm_alus = len(l1)
    if norm_alus == 0:
        if len(l2) == 0:
            # Mõlemad võrreldavad on tühisõned
            return 0
        norm_alus = len(l2)
    kaugus = lev(l1, l2) / norm_alus

    tähe_kaugus = lev("".join(sorted([a for a in lause1])), "".join(sorted([a for a in lause2])))
    norm_alus = len(lause1)
    if norm_alus == 0:
        norm_alus = len(lause2)
    kaugus += tähe_kaugus / norm_alus

    # Aga proovime lihtsalt tähepõhise levensteiniga
    kaugus = lev(lause1, lause2)

    return kaugus


def lev_lause(xs, ys):
    # Sisse originaallausejärjend ja hüpoteeslausejärjend
    # Leia lausejärjendite omavaheline lev. kaugus
    # tagasta võimalikud asendused kujul (orig_lause, hüpo_lause, asenduse_liik)
    # - kus asenduse liik on U: kustutatud e. unnecessary, M: lisatud e. missing, R: asendatud e. replace

    # Mälustruktuur - tabel, täidetud väärtustega -1
    mem = np.full((len(xs) + 1, len(ys) + 1, 4), -1.0)

    # print(mem) #DEBUG
    def _lev(s1, s2):
        i = len(s1)
        j = len(s2)
        if mem[i][j][0] != -1:
            # On juba välja arvutatud ja tabelis
            return mem[i][j]
        if i == 0:
            # Võrdlus tühisõnega
            # [kaugus, kust_i, kust_j, asenduse_liik]
            mem[i][j] = [lause_kaugus("", " ".join(s2[:j])), 0, -j, 0]
            return mem[i][j]
        if j == 0:
            # Võrdlus tühisõnega
            mem[i][j] = [lause_kaugus(" ".join(s1[:i]), ""), -i, 0, 1]
            return mem[i][j]
        else:
            # Asenduse maksumus
            asendused = []
            variandid = [(-1, 0), (0, -1), (-1, -1)]
            muutused = ["U", "M", "R"]  # kustutatud e. unnecessary, lisatud e. missing, asendatud e. replace
            # originaallause kustutatud
            asendused.append(_lev(s1[:-1], s2)[0] + lause_kaugus(s1[i - 1], ""))
            # uus lause hallutsineeritud
            asendused.append(_lev(s1, s2[:-1])[0] + lause_kaugus("", s2[j - 1]))
            # sama lause, aga muudetud
            asendused.append(_lev(s1[:-1], s2[:-1])[0] + lause_kaugus(s1[i - 1], s2[j - 1]))
            vastus = np.argmin(asendused)
            if np.nan in asendused:
                print("NAN sees", asendused)  # DEBUG
            # mis väärtus, kust lahtrist
            mem[i][j] = [asendused[vastus], variandid[vastus][0], variandid[vastus][1], vastus]

            return mem[i][j]

    result = _lev(xs, ys)

    # print(mem) #DEBUG
    # print()

    backtracked = []
    i = len(xs)
    # print(type(i)) #DEBUG
    j = len(ys)
    while i > 0 and j > 0:
        # mem: [kaugus,(i_delta,j_delta),asenduse_liik]
        vastus = mem[i][j]
        # print(vastus) #DEBUG
        # print(i,j,vastus)
        muutused = ["U", "M", "R"]
        backtracked.append([xs[i - 1], ys[j - 1], muutused[int(vastus[3])], vastus[0]])
        # print(backtracked) #DEBUG
        # Mine õigesse lahtrisse tagasi
        i += int(vastus[1])
        j += int(vastus[2])
    # print("Muudatused:",backtracked)
    if i > 0:
        backtracked.append([xs[:i], "", "#U", mem[i][j][0]])
    if j > 0:
        backtracked.append(["", ys[:j], "#M", mem[i][j][0]])
    # M ja U teine paariline tühisõneks
    for i, nelik in enumerate(backtracked):
        if nelik[-2] == "M":
            backtracked[i][0] = ""
        elif nelik[-2] == "U":
            backtracked[i][1] = ""

    return list(reversed(backtracked))
    return (result)


def laused_paralleeli_lev(kuldlaused, hypolaused):
    # Vii lausejärjendid omavahel vastavusse

    # kuldlaused võivad sisaldada alternatiivparandusi

    # (lause1, lause2, asenduse_liik,kaugus)
    # asenduse_liik: #M, #U, M, U, R
    nelikud = lev_lause(kuldlaused, hypolaused)
    # print(nelikud) #DEBUG
    paarid = []
    paar = [0, "", ""]
    # liik = "R"
    loendur = 0
    for i, nelik in enumerate(nelikud):
        # print(i) #DEBUG
        l1 = nelik[0]
        l2 = nelik[1]
        liik = nelik[2]
        # print("\t%",loendur) #DEBUG
        if i == 0:
            # esimene nelik - siin võib olla ka lausete list
            if liik == "R":
                paar[1] = nelik[0]
                paar[2] = nelik[1]
            elif liik == "#M":
                paar[1] = nelik[0]
                for lause in nelik[1]:
                    paar[2] += " " + lause
                loendur = -1
            elif liik == "#U":
                for lause in nelik[0]:
                    paar[1] += " " + lause
                loendur += len(nelik[0]) - 1  # sest et eeldame, et on 1 väiksem kui järgmisel lausel
                paar[2] = nelik[1]
            # print("#", paar) #DEBUG
            continue
        # print(i) #DEBUG

        # Viimane element: pane lihtsalt kõigele varasemale otsa ja ole õnnelik
        elif i == len(nelikud) - 1:
            # print("Viimane!",paar) #DEBUG
            if liik == "R" and nelikud[i - 1][2] == "R":
                # pane enne eelmine ära
                paar[1] = paar[1].strip().replace("  ", " ")
                paar[2] = paar[2].strip().replace("  ", " ")
                paarid.append(paar)
                loendur += 1
                paar = [loendur, "", ""]
            # Eelmine oli M/U või siis just saadud tühi paar
            paar[1] += " " + l1
            paar[2] += " " + l2
            # Suvalised tühikud ära igaks juhuks
            paar[1] = paar[1].strip().replace("  ", " ")
            paar[2] = paar[2].strip().replace("  ", " ")
            paarid.append(paar)
            # paar = [loendur,"",""]
            # continue

        # R, eelmine oli ka R -> kõik on kena ja valmis, saada ära
        elif liik == "R":
            loendur += 1
            if nelikud[i - 1][2] == "R":
                # print("##",i, "2 R järjest",paar) #DEBUG
                # varasemast teada paar lisa listi, sinna enam midagi juurde ei tule:
                # Suvalised tühikud ära igaks juhuks
                paar[1] = paar[1].strip().replace("  ", " ")
                paar[2] = paar[2].strip().replace("  ", " ")
                paarid.append(paar)
                # uus paar algab nüüd sellest lausest
                paar = [loendur, "", ""]
                paar[1] += l1
                paar[2] += l2
                # print("#", paar) #DEBUG

            else:
                # Enne on olnud kas U või M
                # Tehniliselt lisa lihtsalt juurde,
                # loodetavasti on siin muutujas 'paar' alles vaid need jupid, mis selle lausega liituvad.
                if nelikud[i - 1][2] == "M":
                    # sisend algab tegelikult nüüd sellest lausest siin. Kui oleks U/M järjest, siis oleks too pigem kokku R olnud.
                    paar[0] = loendur
                paar[1] += " " + l1
                paar[2] += " " + l2
                # print("#", paar) #DEBUG


        # M/U: Tuleks liita kas eelmise või järgmisega
        elif liik == "M":
            # lause on parandustes (l2) juurde hallutsineeritud, l1==""
            # -> vaata, kas lisada see eelmise lõppu või järgmise algusse
            # print(paar[1][-len(l2):],l2) #DEBUG
            kaugus_eelmisega = lev(paar[1][-len(l2):], l2)
            # print(nelikud[i+1][1][:len(l2)],l2) #DEBUG
            kaugus_järgmisega = lev(nelikud[i + 1][0][:len(l2)], l2)
            # print("M",kaugus_eelmisega,kaugus_järgmisega,l2,i) #DEBUG
            if kaugus_eelmisega <= kaugus_järgmisega:
                # Lisa eelmise lõppu
                paar[2] += " " + l2

            else:
                # Sobib paremini järgmise algusse -> alusta uut paari
                # varasemast teada paar lisa listi, sinna enam midagi juurde ei tule:
                # Suvalised tühikud ära igaks juhuks
                paar[1] = paar[1].strip().replace("  ", " ")
                paar[2] = paar[2].strip().replace("  ", " ")
                paarid.append(paar)
                # uus paar algab nüüd sellest lausest
                paar = [loendur, "", ""]
                paar[2] += l2

        elif liik == "U":
            loendur += 1
            # lause (l1) on parandustes kustunud, l2==""
            # -> vaata, kas lisada see eelmise lõppu või järgmise algusse
            # print(l1,paar[2][-len(l1):]) #DEBUG
            kaugus_eelmisega = lev(l1, paar[2][-len(l1):])
            # print(l1,paar[2][-len(l1):]) #DEBUG
            kaugus_järgmisega = lev(l1, nelikud[i + 1][1][:len(l1)])
            # print("U",kaugus_eelmisega,kaugus_järgmisega,l1,i) #DEBUG
            if kaugus_eelmisega <= kaugus_järgmisega:
                # Lisa eelmise lõppu
                paar[1] += " " + l1

            else:
                # Sobib paremini järgmise algusse -> alusta uut paari
                # varasemast teada paar lisa listi, sinna enam midagi juurde ei tule:
                # Suvalised tühikud ära igaks juhuks
                paar[1] = paar[1].strip().replace("  ", " ")
                paar[2] = paar[2].strip().replace("  ", " ")
                paarid.append(paar)
                # uus paar algab nüüd sellest lausest
                paar = [loendur, "", ""]
                paar[1] += l1


    # (kuldlause_indeks,kuldlaused stringina, hüpolaused_stringina)
    return paarid


def cut_hallucination(originaal, parandatud):
    # Kontrollib, kas paranduse lõpp sisaldab kohutavat hallutsineerimist
    # Tüüpiliselt rakendatav viimasele lausepaarile
    # Tagastab paari, kus parandatud osast on vajadusel lõpp maha lõigatud
    sents = Text(parandatud).tag_layer().sentences
    hüpolaused = [parandatud[s.start:s.end] for s in sents]
    eelmine_kaugus = 1000
    cutoff = 5  # how much of slack is allowed
    for i, sent in enumerate(hüpolaused):
        hüpotees = " ".join(hüpolaused[0:i + 1])
        kaugus = lause_kaugus(originaal, " ".join(hüpolaused[0:i + 1]))
        # print(originaal, " ".join(hüpolaused[0:i+1]),kaugus)
        if kaugus > eelmine_kaugus + cutoff:
            # Järgmise paranduslause lisamisel läheks erinevus märgatavalt suuremaks kui seda lisamata
            return (originaal, " ".join(hüpolaused[0:i]))
        eelmine_kaugus = kaugus
    # Läheb täispikkuses
    return (originaal, parandatud)


def vii_kokku_kirjandid(originaal, parandatud):
    #####
    # Saab sisse kaks pikka stringi: lõik (või kogu essee).
    # originaal - potentsiaalselt vigadega
    # parandatud - automaatsete parandustega mudeli väljund
    # Tagastab listi, kus on liikmeteks lausepaaride tuple'id [("l1_orig", "l1_par. l2 par."),("l2_orig","l3_par")] jne
    ######
    # rida
    sents = Text(originaal).tag_layer().sentences
    kuldlaused = [originaal[s.start:s.end] for s in sents]
    sents = Text(parandatud).tag_layer().sentences
    hüpolaused = [parandatud[s.start:s.end] for s in sents]
    lausepaarid = laused_paralleeli_lev(kuldlaused, hüpolaused)
    #print(lausepaarid)
    lausepaarid = [(l1,l2) for _,l1,l2 in lausepaarid]

    # Kontrolli, kas lõppu on midagi kõvasti juurde hallutsineeritud
    if lausepaarid:
        lausepaarid[-1] = cut_hallucination(lausepaarid[-1][0],lausepaarid[-1][1])

    return lausepaarid