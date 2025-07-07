UNITS {
    (mM) = (milli/liter)
    (mA) = (milliamp)
    (um) = (micrometer)
}

NEURON {


    RANGE k1, k2

    THREADSAFE
}

PARAMETER {
    k1 (1/s) k2 (mM/mA)
}

ASSIGNED {

}

STATE {

}

INITIAL {

}

BREAKPOINT {
	SOLVE states METHOD derivimplicit
}

DERIVATIVE states {

}
