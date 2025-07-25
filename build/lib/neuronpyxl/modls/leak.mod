UNITS {
    (mV) = (millivolt)
    (mA) = (milliamp)
    (uS) = (microsiemens)
    (um) = (micrometer)
}

NEURON {
    SUFFIX neuronpyxl_leak
    RANGE g, e, i
    NONSPECIFIC_CURRENT i
}

PARAMETER {
    g (uS) e (mV)
}

ASSIGNED {
    i (mA/cm2) v (mV) area (um2)
}

BREAKPOINT {
    i = (100)*g/area*(v-e)
}
