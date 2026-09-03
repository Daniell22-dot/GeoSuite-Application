#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "gdal_utils.h"

namespace py = pybind11;

PYBIND11_MODULE(geospatial_cpp, m) {
    m.doc() = "C++ Geospatial tools replacing rasterio and geopandas";

    m.def("sample_raster_at_point", &sample_raster_at_point, 
          "Read a single cell value from a raster given lat/lon context",
          py::arg("filepath"), py::arg("lon"), py::arg("lat"));

    m.def("read_raster_to_array", &read_raster_to_array,
          "Read an entire raster band into a 2D numpy float32 array",
          py::arg("filepath"));
          
    m.def("get_geotransform", &get_geotransform,
          "Return the 6 parameters of the affine geotransform",
          py::arg("filepath"));

    m.def("vector_to_geojson", &vector_to_geojson,
          "Convert a vector layer (e.g. Shapefile) to a GeoJSON string",
          py::arg("filepath"));

    m.def("write_vector_file", &write_vector_file,
          "Write a GeoJSON string to a vector file (e.g. ESRI Shapefile)",
          py::arg("geojson_str"), py::arg("output_path"), py::arg("driver_name"));
}
