UNITS {
    (mV) = (millivolt)
    (mA) = (milliamp)
    (uS) = (microsiemens)
    (um) = (micrometer)
    (mM) = (milli/liter)
}

NEURON {
    SUFFIX ca
    RANGE numbtaus, numataus, A, B, Ainfonly, Binfonly, tmxAonly, tmxBonly, i, g, e, p, k1, k2, region, opt1, opt2, b, p1, p2, AnA, hA, sA, pA, tmxA, tminA, th1A, ts1A, tp1A, th2A, ts2A, tp2A, BnB, hB, sB, pB, tmxB, tminB, th1B, ts1B, tp1B, th2B, ts2B, tp2B

}

PARAMETER {
    g (uS) e (mV) p ()
    AnA () BnB ()
    numataus () numbtaus () tmxAonly = 0 () tmxBonly = 0 () Ainfonly = 0 () Binfonly = 0 ()
    region = -1
    k1 (1/s) k2 (nM/nA)
    opt1 () opt2 () p1 () p2 () b ()
    hA (mV) sA (mV) pA tmxA (s) tminA (s) th1A (mV) ts1A (mV) tp1A th2A (mV) ts2A (mV) tp2A
    hB (mV) sB (mV) pB tmxB (s) tminB (s) th1B (mV) ts1B (mV) tp1B th2B (mV) ts2B (mV) tp2B
    unit_conv = 1e-6 (mM)
}

ASSIGNED {
    C (mM) ica (mA/cm2) i (mA/cm2) v (mV) area (um2) nai (mM) ki (mM) cli (mM) cai (mM) dBR (/ms) A () B ()
}

STATE {
    Astate () Bstate () BR ()
}

INITIAL {
    Astate = 0.0
    Bstate = 0.0
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
    if (Ainfonly == 1) {
        A = Ainf(v)
    } else {
        A = Astate
    }
    if (Binfonly == 1) {
        B = Binf(v)
    } else {
        B = Bstate
    }
    if (numataus == 0) {
        i = (100)*(g/area)*(v-e)*fbr(br(C))
    } else if (numbtaus == 0) {
        i = (100)*(g/area)*pow(A,p)*(v-e)*fbr(br(C))
    } else {
        i = (100)*(g/area)*pow(A,p)*B*(v-e)*fbr(br(C))
    }
    ica = i
}

DERIVATIVE states {
    Astate' = dA()
    Bstate' = dB()
    BR' = dBR
}

FUNCTION current() (mA/cm2) { 
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

FUNCTION dA () (/ms) {
    if (Ainfonly == 1) {
        dA = 0
    } else if (numataus == 1) {
        if (tmxAonly == 1) {
            dA = (Ainf(v)-A)/((1000)*tmxA)
        } else {
            dA = (Ainf(v)-A)/t_1tau((1000)*tminA,(1000)*tmxA,th1A,ts1A,tp1A)
        }
    } else if (numataus == 2) {
        dA = (Ainf(v)-A)/t_2taus((1000)*tminA,(1000)*tmxA,th1A,ts1A,tp1A,th2A,ts2A,tp2A)
    } else {
        dA = 0
    }
}

FUNCTION dB () (/ms) {
    if (Binfonly == 1) {
        dB = 0
    } else if (numbtaus == 1) {
        if (tmxBonly == 1) {
            dB = (Binf(v)-B)/((1000)*tmxB)
        } else {
            dB = (Binf(v)-B)/t_1tau((1000)*tminB,(1000)*tmxB,th1B,ts1B,tp1B)
        }
    } else if (numbtaus == 2) {
        dB = (Binf(v)-B)/t_2taus((1000)*tminB,(1000)*tmxB,th1B,ts1B,tp1B,th2B,ts2B,tp2B)
    } else {
        dB = 0
    }
}

FUNCTION Ainf(v) () {
    Ainf = (1-AnA)/pow((1+exp((hA-v)/sA)), pA) + AnA
}

FUNCTION Binf(v) () {
    Binf = (1-BnB)/pow((1+exp((v-hB)/sB)), pB) + BnB
}

FUNCTION t_1tau(tmin,tmax,th1,ts1,tp1) (ms) {
  t_1tau = tmin+(tmax-tmin)/pow((1+exp((v-th1)/ts1)),tp1)
}

FUNCTION t_2taus(tmin,tmax,th1,ts1,tp1,th2,ts2,tp2) (ms) {
  t_2taus = tmin+(tmax-tmin)/pow((1+exp((v-th1)/ts1)),tp1)/pow((1+exp((v-th2)/ts2)),tp2)
}

UNITSON
