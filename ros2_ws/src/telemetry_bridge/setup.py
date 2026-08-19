from setuptools import setup

package_name = "telemetry_bridge"
setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", ["launch/telemetry_bridge.launch.py"]),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest"],
    entry_points={"console_scripts": ["telemetry_bridge = telemetry_bridge.node:main"]},
)
