UNITS {
	(mV) = (millivolt)
	(mA) = (milliamp)
	(uS) = (microsiemens)
    (um) = (micrometer)
    (mM) = (milli/liter)
}

NEURON {
    SUFFIX cl
    RANGE numbtaus, numataus, tmxAonly, tmxBonly, i, g, e, p, k1, k2, region, opt1, opt2, b, p1, p2, AnA, hA, sA, pA, tmxA, tminA, th1A, ts1A, tp1A, th2A, ts2A, tp2A, BnB, hB, sB, pB, tmxB, tminB, th1B, ts1B, tp1B, th2B, ts2B, tp2B

}

PARAMETER {
    g (uS) e (mV) p ()
    AnA () BnB ()
    numataus () numbtaus () tmxAonly = 0 () tmxBonly = 0 ()
    region = -1
    k1 (1/s) k2 (nM/nA)
    opt1 () opt2 () p1 () p2 () b ()
    hA (mV) sA (mV) pA tmxA (s) tminA (s) th1A (mV) ts1A (mV) tp1A th2A (mV) ts2A (mV) tp2A
    hB (mV) sB (mV) pB tmxB (s) tminB (s) th1B (mV) ts1B (mV) tp1B th2B (mV) ts2B (mV) tp2B
    unit_conv = 1e-6 (mM)
}

ASSIGNED {
    C (mM) icl (mA/cm2) i (mA/cm2) v (mV) area (um2) nai (mM) ki (mM) cai (mM) cli (mM) dcli (mM/ms) dBR (/ms)
}

STATE {
    A () B () BR ()
}

INITIAL {
    A = AnA
    B = BnB
    BR = 0.0
}

BREAKPOINT {
    if (region == 1) {
        C = cai
    } else if (region == 2) {
        C = nai
    } else if (region == 3) {
        C = ki
    } else if (region == 4) {
        C = cli
    } else {
        C = 0.0
    }
    if (opt2 == 1) {
        dBR = (C/unit_conv-BR)/p1
    } else {
        dBR = 0
    }
    SOLVE states METHOD derivimplicit
    i = current(numataus, numbtaus)*fbr(br(C))
    icl = i
}

DERIVATIVE states {
    A' = dA(numataus)
    B' = dB(numbtaus)
    BR' = dBR
}

FUNCTION current(numataus, numbtaus) (mA/cm2) { 
    if (numataus == 0) {
        current = (100)*(g/area)*(v-e)
    } else if (numbtaus == 0) {
        current = (100)*(g/area)*pow(A,p)*(v-e)
    } else {
        current = (100)*(g/area)*pow(A,p)*B*(v-e)
    }
}

UNITSOFF

FUNCTION fbr(br) {
    if (region < 0) {
        fbr = 1
    } else {
        if (opt1 == 1) {
            fbr = br
        } else if (opt1 == 2) {
            fbr = 1 + br
        } else if (opt1 == 3) {
            fbr = 1/(1+b*br)
        } 
    }
}

FUNCTION br(c) {
    if (opt2 == 1) {
        br = BR
    } else if (opt2 == 2) {
        br = c/(p1+c)
    } else if (opt2 == 3) {
        br = c/(p1+c)+1
    } else if (opt2 == 4) {
        br = 1/(1+p1*c)
    } else if (opt2 == 5) {
        br = exp((p1+c)/p2)
    }
}

FUNCTION dA (numtaus) (/ms) {
    if (numtaus == 1) {
        if (tmxAonly == 1) {
            dA = (Ainf()-A)/((1000)*tmxA)
        } else {
            dA = (Ainf()-A)/tA_1tau((1000)*tminA, (1000)*tmxA)
        }
    } else if (numtaus == 2) {
        dA = (Ainf()-A)/tA_2taus((1000)*tminA, (1000)*tmxA)
    } else {
        dA = 0
    }
}

FUNCTION dB (numtaus) (/ms) {
    if (numtaus == 1) {
        if (tmxBonly == 1) {
            dB = (Binf()-B)/((1000)*tmxB)
        } else {
            dB = (Binf()-B)/tB_1tau((1000)*tminB, (1000)*tmxB)
        }
    } else if (numtaus == 2) {
        dB = (Binf()-B)/tB_2taus((1000)*tminB, (1000)*tmxB)
    } else {
        dB = 0
    }
}

FUNCTION Ainf() () {
    Ainf = 1/pow((1+exp((hA-v)/sA)), pA)
}

FUNCTION Binf() () {
    Binf = 1/pow((1+exp((v-hB)/sB)), pB)
}

FUNCTION tA_1tau(tmin, tmax) (ms) {
    tA_1tau = tmin+(tmax-tmin)/pow((1+exp((v-th1A)/ts1A)), tp1A)
}
FUNCTION tA_2taus(tmin, tmax) (ms) {
    tA_2taus = tmin+(tmax-tmin)/pow((1+exp((v-th1A)/ts1A)), tp1A)/pow((1+exp((v-th2A)/ts2A)), tp2A)
}

FUNCTION tB_1tau(tmin, tmax) (ms) {
    tB_1tau = tmin+(tmax-tmin)/pow((1+exp((v-th1B)/ts1B)), tp1B)
}

FUNCTION tB_2taus(tmin, tmax) (ms) {
    tB_2taus = tmin+(tmax-tmin)/pow((1+exp((v-th1B)/ts1B)), tp1B)/pow((1+exp((v-th2B)/ts2B)), tp2B)
}

UNITSON