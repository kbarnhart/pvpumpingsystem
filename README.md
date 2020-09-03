[![CI general checks](https://github.com/tylunel/pvpumpingsystem/workflows/CI%20general%20checks/badge.svg)](https://github.com/tylunel/pvpumpingsystem/actions)
[![Coverage](https://codecov.io/gh/tylunel/pvpumpingsystem/branch/master/graph/badge.svg)](https://codecov.io/gh/tylunel/pvpumpingsystem)
[![Documentation Status](https://readthedocs.org/projects/pvpumpingsystem/badge/?version=latest)](https://pvpumpingsystem.readthedocs.io/en/latest/?badge=latest)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/tylunel/pvpumpingsystem/master)

# pvpumpingsystem
*pvpumpingsystem* is a package providing tools for modeling and sizing
photovoltaic water pumping systems.

It can model the whole functioning of such pumping system on an hourly basis
and eventually provide key financial and technical findings on a year.
Conversely it can help choose some elements of the pumping station
depending on output values wanted (like daily water consumption and
acceptable risk of water shortage).


# Documentation
The package documentation is available on readthedocs:

[pvpumpingsystem docs](https://pvpumpingsystem.readthedocs.io/en/latest/?badge=latest)


# Installation
*pvpumpingsystem* works with Python 3.5 and superior only.

## With Anaconda and Git already installed

In *Anaconda prompt*, change directory to the one you want to install
pvpumpingsystem in, and type:
```
pip install -e git+https://github.com/tylunel/pvpumpingsystem#egg=pvpumpingsystem
```

To ensure *pvpumpingsystem* and its dependencies are properly installed,
run the tests by going to the directory of pvpumpingsystem and
by running pytest:
```
cd src/pvpumpingsystem
pytest
```

## Other installations
Consult the docs for more information:
https://pvpumpingsystem.readthedocs.io/en/latest/installation.html


# Hands-on start

Three examples of how the software can be used are in the folder
'docs/examples'.

For a given system, the first two show how to obtain the outflows,
probability of water shortage, life cycle cost and many other results:

[basic usage example](https://nbviewer.jupyter.org/github/tylunel/pvpumpingsystem/blob/master/docs/examples/simulation_tunis_basic.ipynb)

[more advanced usage example](https://nbviewer.jupyter.org/github/tylunel/pvpumpingsystem/blob/master/docs/examples/simulation_tunis_advanced.ipynb)

The third shows how to optimize the selection of one or more component
on the pumping station based on user requirements:

[sizing example](https://nbviewer.jupyter.org/github/tylunel/pvpumpingsystem/blob/master/docs/examples/sizing_example.ipynb)


# Contributions

All kind of contributions (documentation, testing, bug reports,
new features, suggestions...) are highly appreciated.
They can be reported as issues, pull requests, or simple message via
Github (prefered) or via mail of the maintainer.
