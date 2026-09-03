#pragma once
#include <string>
#include <vector>
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

// Function to get a single elevation or pixel value from a raster at specific coordinates
double sample_raster_at_point(const std::string& filepath, double lon, double lat);

// Function to read an entire raster band into a numpy array (for flow accum, dem, watershed mask)
py::array_t<float> read_raster_to_array(const std::string& filepath);

// Function to get the geotransform of a raster
std::vector<double> get_geotransform(const std::string& filepath);

// Function to read a vector file (like a Shapefile) and output GeoJSON string
std::string vector_to_geojson(const std::string& filepath);

// Function to write a GeoJSON string to a vector file (e.g. Shapefile)
void write_vector_file(const std::string& geojson_str, const std::string& output_path, const std::string& driver_name);
