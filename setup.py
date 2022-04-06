from setuptools import setup, find_packages

setup(
    name='AutoMod',
    version='0.1.0',
    packages=find_packages(include=['automod', 'automod.*']),
    install_requires=[
        "boto3",
        "agora_python_sdk",
        "requests",
        "pytz",
        "rich",
        "secrets",
    ],
    entry_points={
        "console_scripts": ["run_automod=automod.automod:run_automod_client"]
    }
)
