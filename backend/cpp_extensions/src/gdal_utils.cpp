#include "gdal_utils.h"
#include <gdal_priv.h>
#include <ogrsf_frmts.h>
#include <iostream>
#include <stdexcept>
#include <memory>
#include <cmath>

// Helper to ensure GDAL is initialized
struct GDALInitializer {
    GDALInitializer() {
        GDALAllRegister();
        OGRRegisterAll();
    }
};
static GDALInitializer gdal_init;

double sample_raster_at_point(const std::string& filepath, double lon, double lat) {
    GDALDataset* poDataset = (GDALDataset*)GDALOpen(filepath.c_str(), GA_ReadOnly);
    if (!poDataset) {
        throw std::runtime_error("Failed to open raster file: " + filepath);
    }

    double adfGeoTransform[6];
    if (poDataset->GetGeoTransform(adfGeoTransform) != CE_None) {
        GDALClose(poDataset);
        throw std::runtime_error("Failed to get geotransform from: " + filepath);
    }

    // Inverse transform to find pixel location
    double invGeoTransform[6];
    if (!GDALInvGeoTransform(adfGeoTransform, invGeoTransform)) {
        GDALClose(poDataset);
        throw std::runtime_error("Failed to invert geotransform");
    }

    double pfPixel = 0, pfLine = 0;
    GDALApplyGeoTransform(invGeoTransform, lon, lat, &pfPixel, &pfLine);

    int dX = static_cast<int>(std::floor(pfPixel));
    int dY = static_cast<int>(std::floor(pfLine));

    GDALRasterBand* poBand = poDataset->GetRasterBand(1);
    if (!poBand) {
        GDALClose(poDataset);
        throw std::runtime_error("Could not get raster band 1");
    }

    int nXSize = poBand->GetXSize();
    int nYSize = poBand->GetYSize();

    if (dX < 0 || dY < 0 || dX >= nXSize || dY >= nYSize) {
        GDALClose(poDataset);
        return NAN; // Out of bounds
    }

    float value = 0.0f;
    if (poBand->RasterIO(GF_Read, dX, dY, 1, 1, &value, 1, 1, GDT_Float32, 0, 0) != CE_None) {
        GDALClose(poDataset);
        throw std::runtime_error("Error reading pixel from raster");
    }

    // Handle no-data
    int pbSuccess = 0;
    double dfNoData = poBand->GetNoDataValue(&pbSuccess);
    if (pbSuccess && std::abs(value - dfNoData) < 1e-6) {
        GDALClose(poDataset);
        return NAN;
    }

    GDALClose(poDataset);
    return static_cast<double>(value);
}

py::array_t<float> read_raster_to_array(const std::string& filepath) {
    GDALDataset* poDataset = (GDALDataset*)GDALOpen(filepath.c_str(), GA_ReadOnly);
    if (!poDataset) {
        throw std::runtime_error("Failed to open raster file: " + filepath);
    }

    GDALRasterBand* poBand = poDataset->GetRasterBand(1);
    int nXSize = poBand->GetXSize();
    int nYSize = poBand->GetYSize();

    // Allocate numpy array
    auto result = py::array_t<float>({nYSize, nXSize});
    py::buffer_info buf = result.request();
    float* ptr = static_cast<float*>(buf.ptr);

    if (poBand->RasterIO(GF_Read, 0, 0, nXSize, nYSize, ptr, nXSize, nYSize, GDT_Float32, 0, 0) != CE_None) {
        GDALClose(poDataset);
        throw std::runtime_error("Failed to read raster into buffer.");
    }

    GDALClose(poDataset);
    return result;
}

std::vector<double> get_geotransform(const std::string& filepath) {
    GDALDataset* poDataset = (GDALDataset*)GDALOpen(filepath.c_str(), GA_ReadOnly);
    if (!poDataset) {
        throw std::runtime_error("Failed to open raster file: " + filepath);
    }

    double adfGeoTransform[6];
    if (poDataset->GetGeoTransform(adfGeoTransform) != CE_None) {
        GDALClose(poDataset);
        throw std::runtime_error("Failed to get geotransform from: " + filepath);
    }
    GDALClose(poDataset);

    std::vector<double> gt(6);
    for (int i = 0; i < 6; ++i) {
        gt[i] = adfGeoTransform[i];
    }
    return gt;
}

std::string vector_to_geojson(const std::string& filepath) {
    GDALDataset* poDS = (GDALDataset*)GDALOpenEx(filepath.c_str(), GDAL_OF_VECTOR, NULL, NULL, NULL);
    if (!poDS) {
        throw std::runtime_error("Opening vector file failed: " + filepath);
    }

    // We can export the layer to GeoJSON by converting features
    // A simpler approach natively using GDAL is to create an in-memory geojson file
    GDALDriver* poGeoJsonDriver = GetGDALDriverManager()->GetDriverByName("GeoJSON");
    if (!poGeoJsonDriver) {
        GDALClose(poDS);
        throw std::runtime_error("GeoJSON driver not available.");
    }

    std::string outPath = "/vsimem/temp_" + std::to_string(rand()) + ".geojson";
    GDALDataset* poOutDS = poGeoJsonDriver->CreateCopy(outPath.c_str(), poDS, FALSE, NULL, NULL, NULL);
    if (!poOutDS) {
        GDALClose(poDS);
        throw std::runtime_error("Failed to create GeoJSON copy.");
    }

    GDALClose(poDS);
    GDALClose(poOutDS);

    // Read the in-memory file
    vsi_l_offset nLength;
    GByte* pabyData = VSIGetMemFileBuffer(outPath.c_str(), &nLength, FALSE);
    std::string geojson_str(reinterpret_cast<char*>(pabyData), nLength);

    VSIUnlink(outPath.c_str()); // delete from memory

    return geojson_str;
}

void write_vector_file(const std::string& geojson_str, const std::string& output_path, const std::string& driver_name) {
    GDALDriver* poDriver = GetGDALDriverManager()->GetDriverByName(driver_name.c_str());
    if (!poDriver) {
        throw std::runtime_error("GDAL Driver not found: " + driver_name);
    }

    // Use /vsimem so we can write the GeoJSON string to a file-like object OGR can open
    std::string vsiGeoJson = "/vsimem/input_" + std::to_string(rand()) + ".geojson";
    VSIFCloseL(VSIFileFromMemBuffer(vsiGeoJson.c_str(), (GByte*)geojson_str.c_str(), geojson_str.size(), FALSE));

    GDALDataset* poInputDS = (GDALDataset*)GDALOpenEx(vsiGeoJson.c_str(), GDAL_OF_VECTOR, NULL, NULL, NULL);
    if (!poInputDS) {
        VSIUnlink(vsiGeoJson.c_str());
        throw std::runtime_error("Failed to parse GeoJSON string for writing.");
    }

    // Create the output dataset
    GDALDataset* poOutputDS = poDriver->CreateCopy(output_path.c_str(), poInputDS, FALSE, NULL, NULL, NULL);

    GDALClose(poInputDS);
    VSIUnlink(vsiGeoJson.c_str());

    if (!poOutputDS) {
        throw std::runtime_error("Failed to write output vector file to: " + output_path);
    }

    GDALClose(poOutputDS);
}
