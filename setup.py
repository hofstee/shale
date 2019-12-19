from setuptools import setup

setup(
    name="shale",
    author='Teguh Hofstee',
    url='https://github.com/hofstee/shale',

    python_requires='>=3.7',
    install_requires = [
        "astor",
        "cocotb @ git+http://github.com/cocotb/cocotb.git#egg=cocotb",
        "genesis2",
        "numpy",
        "pandas",
#         "pycoreir",
        "tabulate",
    ],
)
