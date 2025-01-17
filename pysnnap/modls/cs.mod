UNITS {
	(mV) = (millivolt)
	(nA) = (nanoamp)
	(uS) = (microsiemens)
    (um) = (micrometer)
    (mM) = (milli/liter)
}

NEURON {
    POINT_PROCESS pysnnap_CS
    RANGE g, e, i, u1, u2, ud, ur, h, s, p, tx, u, ion, depress, voltage_dependence, dur
    NONSPECIFIC_CURRENT i
	POINTER mod
}

PARAMETER {
    g (uS) e (mV)
    u1 (ms) u2 (ms) ud (ms) ur (ms) h (mV) s (mV) p () u (ms)
    tx = -1 (ms)
    ion = 0 () depress = 0 () voltage_dependence = 0 ()
    unit_conv = 1e-6 (/mM)
    dur = 3.0 (ms)
}

ASSIGNED {
    i (nA) v (mV) on () dPSM (/ms) dAv (/ms) Y () dBR (/ms) Xt ()mod (mM)
}

STATE {
    At () Av () dAt (/ms) PSM () BR ()
}

INITIAL {
    At = 0.0
    Av = 0.0
    dAt = 0.0
    PSM = 1.0
    BR = 0.0
}

BREAKPOINT {
    if (tx <= 0) {
        dAv = 0
    } else {
        dAv = (Ainf(v) - Av)/tx
    }
    if (depress == 0) {
        dPSM = 0
    } else {
        if (on == 1) {
            dPSM = -PSM/ud
        } else {
            dPSM = (1-PSM)/ur
        }
    }
    if (ion == 0) {
        dBR = 0
    } else {
        dBR = (mod/unit_conv - BR)/u
    }
    if (on == 0) {
        Xt = 0.0
    } else {
        if (depress != 0) {
            Xt = fBR(BR)*PSM
        } else {
            Xt = fBR(BR)
        }
    }
    SOLVE states METHOD derivimplicit
    if (voltage_dependence == 0) {
        Y = At
    } else {
        if (tx <= 0) {
            Y = Ainf(v)*At
        } else {
            Y = Av*At
        }
    }
    i = g*(v-e)*Y
}

DERIVATIVE states {
    BR' = dBR
    PSM' = dPSM
    Av' = dAv
    dAt' = (Xt - (u1+u2)*dAt - At) / (u1*u2)
    At' = dAt
}

FUNCTION fBR(br) {
    if (ion == 0) {
        fBR = 1
    } else {
        fBR = 1 + br
    }
}

FUNCTION Ainf(V) () {
    Ainf = 1/pow(1+exp((h-V)/s), p)
}

NET_RECEIVE (weight) {
    if (flag == 0) {
        if (!on) {
            on = 1
            net_send(dur, 1)
        } else {
            net_move(t + dur)
        }
    }
    if (flag == 1) {
        on = 0
    }
}