from setuptools import find_packages, setup

package_name = "fleet_manager"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="EV Factory Twin",
    maintainer_email="dev@example.com",
    description="Robot registry and transport execution for the simulated AMR fleet.",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={"console_scripts": ["fleet_manager = fleet_manager.node:main"]},
)
