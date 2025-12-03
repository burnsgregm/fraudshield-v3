import setuptools

setuptools.setup(
    name='fraudshield-streaming',
    version='0.0.1',
    install_requires=[
        'google-cloud-aiplatform==1.35.0',
        'apache-beam[gcp]==2.50.0'
    ],
    packages=setuptools.find_packages(),
)
