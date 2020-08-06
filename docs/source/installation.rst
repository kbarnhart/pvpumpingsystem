.. _installation: pvpumpingsystem

Installation
============

Installing pvpumpingsystem can be done through different processes. Two of 
them are detailled here, mainly thought for newcomers. Experienced users 
can modify it to their liking.

**Do you plan on contributing or editing the code but you are new to Python?**

    If the answer to this is *Yes*, follow the :ref:`anacondagit` instructions
    to install pvpumpingsystem along with Anaconda and Git.

    If the answer to this is *No*, follow the :ref:`simple` instructions
    to install pvpumpingsystem alone in not editable mode.


Installing pvpumpingsystem is similar to installing most scientific python
packages, so in case of trouble see the :ref:`references` section 
for further help.

Please see the :ref:`compatibility` section for information on the
optional packages that are needed for some pvpumpingsystem features.

.. _anacondagit:

Install pvpumpingsystem with Anaconda and Git
---------------------------------------------

- Anaconda

The Anaconda distribution is an open source distribution providing Python 
and others softwares and libraries useful for data science. Anaconda includes 
many of the libraries needed for pvpumpingsystem (Pandas, NumPy, SciPy, etc).

#. **Install** the Anaconda Python distribution available at
   `<https://www.anaconda.com/download/>`_.

See `What is Anaconda? <https://www.anaconda.com/what-is-anaconda/>`_
and the `Anaconda Documentation <https://docs.anaconda.com/anaconda/>`_
for more information.


- Git

Git is a version control system that widely help contribution and development 
for open source softwares. Git should be native on most of Linux distribution,
but must be installed on Windows.

#. **Install** Git for Windows is available at
   `<https://gitforwindows.org/>`_.


Once you have Anaconda and git installed, open the command line interface 
'Anaconda prompt', change directory to the one you want to install 
pvpumpingsystem in, and type in:
```
pip install -e git+https://github.com/tylunel/pvpumpingsystem#egg=pvpumpingsystem
```
*N.B.: *pvpumpingsystem* is not available yet with conda-forge or with PyPI,
therefore it must be installed through a VCS or from the local source code.

To ensure 'pvpumpingsystem' and its dependencies are properly installed, 
run the tests by going to the directory of pvpumpingsystem and by running pytest:
```
cd src/pvpumpingsystem
pytest
```


.. _simple:

Install pvpumpingsystem alone
-----------------------------

.. note::

    This is a note.


The second option implies to download the Python source code manually.
Either clone the `git repository <https://github.com/tylunel/pvpumpingsystem>`_ 
or go to the `Releases page 
<https://github.com/tylunel/pvpumpingsystem/releases>`_ to
download the zip file of the most recent release.


Installing pvpumpingsystem as an editable library involves 3 steps:

1. :ref:`step1`
2. :ref:`setupenvironment`
3. :ref:`installsource`

None of these steps are particularly challenging, but they become
more difficult when combined.
With a little bit of practice the process will be fast and easy.
Experienced users can easily execute these steps in less than a minute.
You'll get there.

.. _step1:

Obtain the source code
~~~~~~~~~~~~~~~~~~~~~~

blablabla

Follow these steps ...:

#. **Download** 
#. **Fork** 
#. **Clone** your


.. _setupenvironment:

Set up a virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

blabla

.. _installsource:

Install the source code
~~~~~~~~~~~~~~~~~~~~~~~

blabla

#. **Install** 
#. **Test** your installation by running ``python -c 'import pvlib'``.
   You're good to go if it returns without an exception.


.. _compatibility:

Compatibility
-------------

*pvpumpingsystem* is compatible with Python 3.5 and above.

Besides the libraries contained in Anaconda, *pvpumpingsystem* also requires: 
* pvlib-python:
* fluids:
* numpy-financial:

The full list of dependencies is detailled in 
`setup.py <https://github.com/tylunel/pvpumpingsystem/docs/environment.rst>`_.


.. _references:

References
----------

.. note::

    This section was adapted from the pvlib-python documentation. 
    Thanks to them for this useful listing!

Here are a few recommended references for installing Python packages:

* `Python Packaging Authority tutorial
  <https://packaging.python.org/tutorials/installing-packages/>`_
* `Conda User Guide
  <http://conda.pydata.org/docs/index.html>`_

Here are a few recommended references for git and GitHub:

* `The git documentation <https://git-scm.com/doc>`_:
  detailed explanations, videos, more links, and cheat sheets. Go here first!
* `Forking Projects <https://guides.github.com/activities/forking/>`_
* `Fork A Repo <https://help.github.com/articles/fork-a-repo/>`_
* `Cloning a repository
  <https://help.github.com/articles/cloning-a-repository/>`_


