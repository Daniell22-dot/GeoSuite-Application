cmake_minimum_required(VERSION 3.15)
project(geospatial_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)

# Find pybind11
find_package(pybind11 CONFIG REQUIRED)

# Find GDAL
find_package(GDAL REQUIRED)

# Add our Python extension module
pybind11_add_module(geospatial_cpp src/bindings.cpp src/gdal_utils.cpp)

# Link against GDAL
target_link_libraries(geospatial_cpp PRIVATE GDAL::GDAL)

# For numpy support in pybind11
# Numpy headers are usually included automatically by pybind11 if python has numpy installed,
# but we may need to make sure. We'll simply include pybind11/numpy.h in our code.
