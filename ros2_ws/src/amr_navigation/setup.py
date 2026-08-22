from glob import glob

from setuptools import find_packages, setup

package_name = "amr_navigation"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/config", glob("config/*.json")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="EV Factory Twin",
    maintainer_email="dev@example.com",
    description="Deterministic station navigation and AMR state simulator.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={"console_scripts": ["navigation_simulator = amr_navigation.node:main"]},
)
