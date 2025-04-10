UNITS {
	(mV) = (millivolt)
	(nA) = (nanoamp)
	(uS) = (microsiemens)
}

NEURON {
    POINT_PROCESS pysnnap_ES
    RANGE g, i
    NONSPECIFIC_CURRENT i
    POINTER vpre
}

PARAMETER {
    g (uS)
}

ASSIGNED {
    i (nA) v (mV)
    vpre (mV)
}

BREAKPOINT {
    i = g*(v-vpre)
}